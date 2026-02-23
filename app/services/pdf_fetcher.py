from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from app.config import Settings
from app.core.exceptions import PDFFetchError
from app.core.logging import get_logger

logger = get_logger(__name__)


class PDFFetcher:
    """Downloads PDF files from TOBB with streaming, size limits, and retry.

    Handles the pdf_goster.php endpoint which may return:
    - Direct PDF (Content-Type: application/pdf)
    - HTML page with embedded PDF (embed/iframe/object tag)
    """

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def fetch(self, url: str) -> bytes:
        max_bytes = self._settings.MAX_PDF_MB * 1024 * 1024

        try:
            # First, do a non-streaming GET to check content type
            resp = await self._client.get(url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")

            if "application/pdf" in content_type:
                # Direct PDF response
                pdf_data = resp.content
                if len(pdf_data) > max_bytes:
                    raise PDFFetchError(
                        message=f"PDF boyutu limiti asildi ({len(pdf_data)} bytes)",
                        detail=f"max={self._settings.MAX_PDF_MB}MB, url={url}",
                    )
                logger.info("pdf_fetched", url=url, size_bytes=len(pdf_data), mode="direct")
                return pdf_data

            if "text/html" in content_type:
                # HTML page - look for embedded PDF URL
                pdf_url = self._extract_pdf_url_from_html(resp.text, url)
                if pdf_url:
                    return await self._stream_pdf(pdf_url, max_bytes)

                raise PDFFetchError(
                    message="PDF linki HTML sayfasinda bulunamadi",
                    detail=f"url={url}",
                )

            # Unknown content type - try treating as PDF
            pdf_data = resp.content
            if pdf_data[:4] == b"%PDF":
                if len(pdf_data) > max_bytes:
                    raise PDFFetchError(
                        message=f"PDF boyutu limiti asildi ({len(pdf_data)} bytes)",
                        detail=f"max={self._settings.MAX_PDF_MB}MB, url={url}",
                    )
                logger.info("pdf_fetched", url=url, size_bytes=len(pdf_data), mode="raw")
                return pdf_data

            raise PDFFetchError(
                message=f"Beklenmeyen icerik tipi: {content_type}",
                detail=f"url={url}",
            )

        except PDFFetchError:
            raise
        except httpx.HTTPStatusError as exc:
            raise PDFFetchError(
                message=f"PDF indirilemedi (HTTP {exc.response.status_code})",
                detail=f"url={url}",
            ) from exc
        except httpx.HTTPError as exc:
            raise PDFFetchError(
                message="PDF indirme hatasi",
                detail=f"url={url}, error={exc}",
            ) from exc

    @staticmethod
    def _extract_pdf_url_from_html(html: str, base_url: str) -> str | None:
        """Extract PDF URL from an HTML page that embeds/iframes a PDF."""
        soup = BeautifulSoup(html, "lxml")

        # Check embed tag
        embed = soup.select_one("embed[src]")
        if embed:
            src = embed.get("src", "")
            if src:
                return _resolve_url(src, base_url)

        # Check iframe tag
        iframe = soup.select_one("iframe[src]")
        if iframe:
            src = iframe.get("src", "")
            if src:
                return _resolve_url(src, base_url)

        # Check object tag
        obj = soup.select_one("object[data]")
        if obj:
            data = obj.get("data", "")
            if data:
                return _resolve_url(data, base_url)

        return None

    async def _stream_pdf(self, url: str, max_bytes: int) -> bytes:
        """Stream-download a PDF with size limit enforcement."""
        async with self._client.stream("GET", url) as resp:
            resp.raise_for_status()

            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                raise PDFFetchError(
                    message=f"PDF boyutu limiti asildi ({content_length} bytes)",
                    detail=f"max={self._settings.MAX_PDF_MB}MB, url={url}",
                )

            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise PDFFetchError(
                        message=f"PDF boyutu limiti asildi ({total} bytes)",
                        detail=f"max={self._settings.MAX_PDF_MB}MB, url={url}",
                    )
                chunks.append(chunk)

        pdf_data = b"".join(chunks)
        logger.info("pdf_fetched", url=url, size_bytes=len(pdf_data), mode="embedded")
        return pdf_data


def _resolve_url(src: str, base_url: str) -> str:
    """Resolve a potentially relative URL against a base URL."""
    from urllib.parse import urljoin

    if src.startswith("http"):
        return src
    # urljoin handles both absolute paths (/tmp_gazete/...) and relative paths correctly
    return urljoin(base_url, src)
