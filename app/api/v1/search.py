from __future__ import annotations

import asyncio
import unicodedata
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends
from unicode_tr import unicode_tr as tr

from app.api.deps import get_auth_client, get_gazette_client, get_search_client
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.schemas.requests import SearchRequest
from app.schemas.responses import GazetteRecord, SearchRecord, SearchResponse
from app.services.auth_client import AuthClient
from app.services.gazette_client import GazetteClient
from app.services.search_client import SearchClient
from app.services.tsm_mapping import resolve_tsm_id

logger = get_logger(__name__)
router = APIRouter()

_RETRY_DELAY = 2.0


def _date_sort_key(record: GazetteRecord) -> datetime:
    """Parse yayin_tarihi (DD/MM/YYYY or DD.MM.YYYY) for sorting. Unknown dates go last."""
    if not record.yayin_tarihi:
        return datetime.min
    try:
        cleaned = record.yayin_tarihi.replace(".", "/")
        return datetime.strptime(cleaned, "%d/%m/%Y")
    except (ValueError, TypeError):
        return datetime.min


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    search_client: SearchClient = Depends(get_search_client),
    auth_client: AuthClient = Depends(get_auth_client),
    gazette_client: GazetteClient = Depends(get_gazette_client),
) -> SearchResponse:
    trade_name = unicodedata.normalize("NFC", body.trade_name)

    results, total_records = await _search_with_retry(search_client, trade_name)

    if not results:
        return SearchResponse(
            query=body.trade_name,
            total_results=0,
            total_records=total_records,
            results=[],
        )

    # Enrich with PDF URLs from ilan goruntuleme
    try:
        await auth_client.ensure_authenticated()
    except AuthError:
        logger.warning("search_enrich_auth_failed_retrying")
        await auth_client.logout()
        await auth_client.ensure_authenticated()

    for record in results:
        if not record.tsm or not record.registry_no:
            continue
        tsm_id = resolve_tsm_id(record.tsm)
        if not tsm_id:
            continue
        try:
            gazette_records = await gazette_client.search(
                sicil_mudurlugu_id=tsm_id,
                tic_sic_no=record.registry_no,
            )
            gazette_records = sorted(gazette_records, key=_date_sort_key, reverse=True)
            record.pdf_urls = [gr.pdf_url for gr in gazette_records if gr.pdf_url]
        except Exception:
            logger.warning(
                "gazette_enrich_failed",
                title=record.title,
                registry_no=record.registry_no,
                exc_info=True,
            )

    return SearchResponse(
        query=body.trade_name,
        total_results=len(results),
        total_records=total_records,
        results=results,
    )


async def _search_with_retry(
    client: SearchClient,
    trade_name: str,
) -> tuple[list[SearchRecord], int]:
    """Search with retries: try original text twice, then I→İ fallback twice.

    Returns empty list if no results found.
    """
    for attempt in range(1, 3):
        try:
            results, total = await client.search(trade_name)
            if results:
                return results, total
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
        if attempt < 2:
            logger.info("search_failed_retrying", attempt=attempt, query=trade_name)
            await asyncio.sleep(_RETRY_DELAY)

    # Fallback: aggressive I→İ conversion
    turkish = _ascii_to_turkish_upper(trade_name)
    if turkish == trade_name:
        logger.info("search_not_found", query=trade_name)
        return [], 0

    logger.info("retrying_search_with_turkish_upper", original=trade_name, turkish=turkish)
    for attempt in range(1, 3):
        try:
            results, total = await client.search(turkish)
            if results:
                return results, total
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
        if attempt < 2:
            logger.info("search_fallback_retrying", attempt=attempt, query=turkish)
            await asyncio.sleep(_RETRY_DELAY)

    logger.info("search_not_found", query=trade_name)
    return [], 0


def _ascii_to_turkish_upper(text: str) -> str:
    """Convert text to Turkish uppercase, mapping ASCII I to Turkish İ."""
    lowered = text.lower().replace("\u0307", "")
    return str(tr(lowered).upper())
