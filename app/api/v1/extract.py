from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_extractor
from app.schemas.requests import ExtractRequest
from app.schemas.responses import ExtractResponse
from app.services.extractor import Extractor

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    body: ExtractRequest,
    extractor: Extractor = Depends(get_extractor),
) -> ExtractResponse:
    results = await extractor.extract(
        trade_name=body.trade_name,
        max_results=body.max_results,
    )
    successful = sum(1 for r in results if r.error is None)
    return ExtractResponse(
        query=body.trade_name,
        total_processed=len(results),
        successful=successful,
        results=results,
    )
