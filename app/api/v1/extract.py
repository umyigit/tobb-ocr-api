from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_extractor
from app.schemas.requests import ExtractRequest
from app.schemas.responses import ExtractResult
from app.services.extractor import Extractor

router = APIRouter()


@router.post("/extract", response_model=ExtractResult)
async def extract(
    body: ExtractRequest,
    extractor: Extractor = Depends(get_extractor),
) -> ExtractResult:
    return await extractor.extract_from_url(pdf_url=body.pdf_url)
