from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_client, get_gazette_client, get_search_client
from app.schemas.requests import SearchRequest
from app.schemas.responses import SearchResponse
from app.services.auth_client import AuthClient
from app.services.gazette_client import GazetteClient
from app.services.search_client import SearchClient
from app.services.tsm_mapping import resolve_tsm_id

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    search_client: SearchClient = Depends(get_search_client),
    auth_client: AuthClient = Depends(get_auth_client),
    gazette_client: GazetteClient = Depends(get_gazette_client),
) -> SearchResponse:
    results, total_records = await search_client.search(body.trade_name)

    # Enrich with PDF URLs from ilan goruntuleme
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
