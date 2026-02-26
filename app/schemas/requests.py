from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    trade_name: str = Field(..., min_length=2, max_length=500, description="Ticaret unvani")


class ExtractRequest(BaseModel):
    pdf_url: str = Field(..., min_length=10, max_length=2000, description="Gazete PDF URL")
