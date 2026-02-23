from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    trade_name: str = Field(..., min_length=2, max_length=500, description="Ticaret unvani")


class ExtractRequest(BaseModel):
    trade_name: str = Field(..., min_length=2, max_length=500, description="Ticaret unvani")
    max_results: int = Field(default=5, ge=1, le=20, description="Maksimum sonuc sayisi")
