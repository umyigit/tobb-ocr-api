from __future__ import annotations

from datetime import datetime

from app.core.exceptions import NotFoundError, OCRError, PDFFetchError
from app.core.logging import get_logger
from app.schemas.responses import ExtractResult, GazetteRecord
from app.services.auth_client import AuthClient
from app.services.gazette_client import GazetteClient
from app.services.ocr_pipeline import OCRPipeline
from app.services.parser import GazetteParser
from app.services.pdf_fetcher import PDFFetcher
from app.services.search_client import SearchClient
from app.services.tsm_mapping import resolve_tsm_id

logger = get_logger(__name__)


class Extractor:
    """Orchestrator: auth -> search (unvan sorgulama) -> gazette (ilan goruntuleme) -> pdf -> ocr -> parse -> JSON."""

    def __init__(
        self,
        auth_client: AuthClient,
        search_client: SearchClient,
        gazette_client: GazetteClient,
        pdf_fetcher: PDFFetcher,
        ocr_pipeline: OCRPipeline,
        parser: GazetteParser,
    ) -> None:
        self._auth = auth_client
        self._search = search_client
        self._gazette = gazette_client
        self._pdf = pdf_fetcher
        self._ocr = ocr_pipeline
        self._parser = parser

    async def extract(
        self,
        trade_name: str,
        max_results: int = 5,
    ) -> list[ExtractResult]:
        """Full extraction pipeline. User only provides trade_name."""
        # 1. Ensure authenticated session for gazette/PDF access
        await self._auth.ensure_authenticated()

        # 2. Unvan sorgulama -> ilan goruntuleme (always two-step)
        gazette_records = await self._search_gazette_via_unvan(trade_name)
        gazette_records = sorted(gazette_records, key=self._date_sort_key, reverse=True)
        gazette_records = gazette_records[:max_results]

        if not gazette_records:
            raise NotFoundError(
                message=f"'{trade_name}' icin gazete ilani bulunamadi",
                detail=f"query={trade_name}",
            )

        # 3. Process each gazette record: pdf fetch -> ocr -> parse
        results: list[ExtractResult] = []
        for record in gazette_records:
            result = await self._process_gazette_record(record)
            results.append(result)

        # If ALL failed, raise error
        successful = [r for r in results if r.error is None]
        if not successful and results:
            raise OCRError(
                message="Hicbir PDF'den metin cikarilmadi",
                detail=f"total_attempted={len(results)}",
            )

        # Logout after successful extraction; next request will re-login
        await self._auth.logout()

        return results

    async def _search_gazette_via_unvan(self, trade_name: str) -> list[GazetteRecord]:
        """Search unvan sorgulama first, then use results to search ilan goruntuleme."""
        search_records, _total = await self._search.search(trade_name)

        all_gazette_records: list[GazetteRecord] = []
        seen_keys: set[tuple[str, str]] = set()

        for record in search_records:
            if not record.tsm or not record.registry_no:
                logger.warning(
                    "search_record_missing_tsm_or_registry",
                    title=record.title,
                    tsm=record.tsm,
                    registry_no=record.registry_no,
                )
                continue

            tsm_id = resolve_tsm_id(record.tsm)
            if not tsm_id:
                logger.warning(
                    "tsm_id_not_found",
                    tsm=record.tsm,
                    title=record.title,
                )
                continue

            gazette_records = await self._gazette.search(
                sicil_mudurlugu_id=tsm_id,
                tic_sic_no=record.registry_no,
            )

            for gr in gazette_records:
                key = (gr.sicil_no, gr.yayin_tarihi or "")
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_gazette_records.append(gr)

        return all_gazette_records

    @staticmethod
    def _date_sort_key(record: GazetteRecord) -> datetime:
        """Parse yayin_tarihi (DD/MM/YYYY or DD.MM.YYYY) for sorting. Unknown dates go last."""
        if not record.yayin_tarihi:
            return datetime.min
        try:
            cleaned = record.yayin_tarihi.replace(".", "/")
            return datetime.strptime(cleaned, "%d/%m/%Y")
        except (ValueError, TypeError):
            return datetime.min

    async def _process_gazette_record(self, record: GazetteRecord) -> ExtractResult:
        """Fetch PDF, OCR, and parse a single gazette record."""
        if not record.pdf_url:
            return ExtractResult(
                trade_name=record.unvan,
                registry_city=record.mudurluk,
                registry_no=record.sicil_no,
                publication_date=record.yayin_tarihi,
                issue_no=record.sayi,
                notice_type=record.ilan_turu,
                source_pdf_url=None,
                error="PDF URL bulunamadi",
            )

        try:
            pdf_data = await self._fetch_pdf_with_reauth(record.pdf_url)
            raw_text = self._ocr.extract_text(pdf_data)
            parsed = self._parser.parse(raw_text)

            # Merge: gazette metadata as primary, OCR parse as fallback/enrichment
            return ExtractResult(
                trade_name=record.unvan,
                registry_city=parsed.registry_city or record.mudurluk,
                registry_no=parsed.registry_no or record.sicil_no,
                publication_date=parsed.publication_date or record.yayin_tarihi,
                issue_no=parsed.issue_no or record.sayi,
                notice_type=parsed.notice_type.value if parsed.notice_type else record.ilan_turu,
                source_pdf_url=record.pdf_url,
                raw_text=parsed.raw_text,
                parse_confidence=parsed.parse_confidence,
            )
        except Exception as exc:
            logger.warning(
                "gazette_record_processing_failed",
                url=record.pdf_url,
                error=str(exc),
                exc_info=True,
            )
            return ExtractResult(
                trade_name=record.unvan,
                registry_city=record.mudurluk,
                registry_no=record.sicil_no,
                publication_date=record.yayin_tarihi,
                issue_no=record.sayi,
                notice_type=record.ilan_turu,
                source_pdf_url=record.pdf_url,
                error=str(exc),
            )

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
