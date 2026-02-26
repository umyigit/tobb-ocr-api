from __future__ import annotations

from app.core.exceptions import AuthError, PDFFetchError
from app.core.logging import get_logger
from app.schemas.responses import ExtractResult
from app.services.auth_client import AuthClient
from app.services.ocr_pipeline import OCRPipeline
from app.services.pdf_fetcher import PDFFetcher

logger = get_logger(__name__)


class Extractor:
    """Orchestrator: auth -> pdf fetch -> ocr -> raw text."""

    def __init__(
        self,
        auth_client: AuthClient,
        pdf_fetcher: PDFFetcher,
        ocr_pipeline: OCRPipeline,
    ) -> None:
        self._auth = auth_client
        self._pdf = pdf_fetcher
        self._ocr = ocr_pipeline

    async def extract_from_url(self, pdf_url: str) -> ExtractResult:
        """Extract raw OCR text from a single gazette PDF by its direct URL."""
        await self._ensure_auth_with_retry()

        try:
            pdf_data = await self._fetch_pdf_with_reauth(pdf_url)
            raw_text = self._ocr.extract_text(pdf_data)

            return ExtractResult(
                source_pdf_url=pdf_url,
                raw_text=raw_text,
            )
        except Exception as exc:
            logger.warning(
                "pdf_processing_failed",
                url=pdf_url,
                error=str(exc),
                exc_info=True,
            )
            return ExtractResult(
                source_pdf_url=pdf_url,
                error=str(exc),
            )
        finally:
            await self._auth.logout()

    async def _ensure_auth_with_retry(self) -> None:
        """Authenticate, and on failure clear session state and retry once."""
        try:
            await self._auth.ensure_authenticated()
        except AuthError:
            logger.warning("auth_failed_clearing_session_and_retrying")
            await self._auth.logout()
            await self._auth.ensure_authenticated()

    async def _fetch_pdf_with_reauth(self, url: str) -> bytes:
        """Fetch PDF, re-authenticate and retry once if session seems expired."""
        try:
            return await self._pdf.fetch(url)
        except PDFFetchError as exc:
            if "HTML sayfasinda bulunamadi" not in exc.message:
                raise
            logger.warning("pdf_fetch_session_expired_suspected", url=url)
            await self._auth.logout()
            await self._auth.ensure_authenticated()
            return await self._pdf.fetch(url)
