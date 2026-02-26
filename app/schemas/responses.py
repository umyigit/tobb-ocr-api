from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import ErrorCode, NoticeType


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "tobb-ocr-rest-api"


class SearchRecord(BaseModel):
    title: str = Field(..., description="Ticaret unvani")
    registry_no: str | None = Field(default=None, description="Sicil numarasi")
    tsm: str | None = Field(default=None, description="Ticaret Sicil Mudurlugu (sehir)")
    pdf_urls: list[str] = Field(default_factory=list, description="Gazete PDF linkleri")


class SearchResponse(BaseModel):
    query: str
    total_results: int
    total_records: int = Field(default=0, description="TOBB toplam kayit sayisi")
    results: list[SearchRecord]


class GazetteRecord(BaseModel):
    """A single gazette announcement from ilan goruntuleme results."""

    mudurluk: str
    sicil_no: str
    unvan: str
    yayin_tarihi: str | None = None
    sayi: str | None = None
    sayfa: str | None = None
    ilan_turu: str | None = None
    pdf_url: str | None = None


class ParsedGazette(BaseModel):
    registry_city: str | None = None
    registry_no: str | None = None
    publication_date: str | None = None
    issue_no: str | None = None
    notice_type: NoticeType | None = None
    raw_text: str = ""
    parse_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExtractResult(BaseModel):
    """OCR result from a single gazette PDF."""

    source_pdf_url: str | None = None
    raw_text: str = ""
    error: str | None = None


class ErrorResponse(BaseModel):
    error_code: ErrorCode
    message: str
    detail: str | None = None
