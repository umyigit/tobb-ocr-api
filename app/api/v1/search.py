from __future__ import annotations

import asyncio
import unicodedata

import httpx
from fastapi import APIRouter, Depends
from unicode_tr import unicode_tr as tr

from app.api.deps import get_auth_client, get_gazette_client, get_search_client
from app.core.exceptions import AuthError, NotFoundError
from app.core.logging import get_logger
from app.schemas.requests import SearchRequest
from app.schemas.responses import SearchRecord, SearchResponse
from app.services.auth_client import AuthClient
from app.services.gazette_client import GazetteClient
from app.services.search_client import SearchClient
from app.services.tsm_mapping import resolve_tsm_id

logger = get_logger(__name__)
router = APIRouter()

_RETRY_DELAY = 2.0


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    search_client: SearchClient = Depends(get_search_client),
    auth_client: AuthClient = Depends(get_auth_client),
    gazette_client: GazetteClient = Depends(get_gazette_client),
) -> SearchResponse:
    trade_name = unicodedata.normalize("NFC", body.trade_name)

    results, total_records = await _search_with_retry(search_client, trade_name)

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
        gazette_records = await gazette_client.search(
            sicil_mudurlugu_id=tsm_id,
            tic_sic_no=record.registry_no,
        )
        record.pdf_urls = [gr.pdf_url for gr in gazette_records if gr.pdf_url]

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
    """Search with retries: try original text twice, then I→İ fallback twice."""
    original_exc: Exception | None = None
    for attempt in range(1, 3):
        try:
            return await client.search(trade_name)
        except (NotFoundError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code != 404:
                raise
            original_exc = exc
            if attempt < 2:
                logger.info("search_failed_retrying", attempt=attempt, query=trade_name)
                await asyncio.sleep(_RETRY_DELAY)

    # Fallback: aggressive I→İ conversion
    turkish = _ascii_to_turkish_upper(trade_name)
    if turkish == trade_name:
        raise original_exc  # type: ignore[misc]

    logger.info("retrying_search_with_turkish_upper", original=trade_name, turkish=turkish)
    for attempt in range(1, 3):
        try:
            return await client.search(turkish)
        except (NotFoundError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code != 404:
                raise
            if attempt < 2:
                logger.info("search_fallback_retrying", attempt=attempt, query=turkish)
                await asyncio.sleep(_RETRY_DELAY)

    raise original_exc  # type: ignore[misc]


def _ascii_to_turkish_upper(text: str) -> str:
    """Convert text to Turkish uppercase, mapping ASCII I to Turkish İ."""
    lowered = text.lower().replace("\u0307", "")
    return str(tr(lowered).upper())
