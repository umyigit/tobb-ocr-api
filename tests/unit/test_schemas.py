from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.enums import ErrorCode
from app.schemas.requests import ExtractRequest, SearchRequest
from app.schemas.responses import (
    ErrorResponse,
    ExtractResponse,
    ExtractResult,
    GazetteRecord,
    HealthResponse,
    ParsedGazette,
    SearchRecord,
    SearchResponse,
)


class TestSearchRequest:
    def test_valid(self):
        req = SearchRequest(trade_name="ACME LTD")
        assert req.trade_name == "ACME LTD"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            SearchRequest(trade_name="A")

    def test_empty(self):
        with pytest.raises(ValidationError):
            SearchRequest(trade_name="")


class TestExtractRequest:
    def test_defaults(self):
        req = ExtractRequest(trade_name="ACME LTD")
        assert req.max_results == 5

    def test_custom_max(self):
        req = ExtractRequest(trade_name="ACME LTD", max_results=10)
        assert req.max_results == 10

    def test_only_trade_name_required(self):
        req = ExtractRequest(trade_name="ACME LTD")
        assert req.trade_name == "ACME LTD"
        assert req.max_results == 5

    def test_max_results_bounds(self):
        with pytest.raises(ValidationError):
            ExtractRequest(trade_name="ACME LTD", max_results=0)
        with pytest.raises(ValidationError):
            ExtractRequest(trade_name="ACME LTD", max_results=21)


class TestSearchRecord:
    def test_with_all_fields(self):
        rec = SearchRecord(
            title="ACME A.S.",
            registry_no="123456",
            tsm="ISTANBUL",
            pdf_urls=["https://example.com/pdf1", "https://example.com/pdf2"],
        )
        assert rec.title == "ACME A.S."
        assert rec.registry_no == "123456"
        assert rec.tsm == "ISTANBUL"
        assert len(rec.pdf_urls) == 2

    def test_optional_fields(self):
        rec = SearchRecord(title="ACME A.S.")
        assert rec.registry_no is None
        assert rec.tsm is None
        assert rec.pdf_urls == []


class TestSearchResponse:
    def test_structure(self):
        resp = SearchResponse(
            query="ACME",
            total_results=1,
            results=[SearchRecord(title="ACME A.S.", registry_no="123", tsm="ANKARA")],
        )
        assert resp.total_results == 1
        assert resp.results[0].title == "ACME A.S."


class TestGazetteRecord:
    def test_full_record(self):
        rec = GazetteRecord(
            mudurluk="ISTANBUL",
            sicil_no="123456",
            unvan="ACME A.S.",
            yayin_tarihi="01/01/2024",
            sayi="10987",
            sayfa="5",
            ilan_turu="KURULUS",
            pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc",
        )
        assert rec.mudurluk == "ISTANBUL"
        assert rec.pdf_url is not None

    def test_minimal_record(self):
        rec = GazetteRecord(
            mudurluk="ANKARA",
            sicil_no="789",
            unvan="TEST LTD",
        )
        assert rec.yayin_tarihi is None
        assert rec.pdf_url is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            GazetteRecord(mudurluk="ISTANBUL")  # missing sicil_no, unvan


class TestParsedGazette:
    def test_defaults(self):
        g = ParsedGazette()
        assert g.registry_city is None
        assert g.parse_confidence == 0.0

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ParsedGazette(parse_confidence=1.5)


class TestExtractResult:
    def test_with_error(self):
        r = ExtractResult(error="fail")
        assert r.error == "fail"

    def test_with_all_fields(self):
        r = ExtractResult(
            trade_name="ACME A.S.",
            registry_city="Istanbul",
            registry_no="123456",
            publication_date="01/01/2024",
            issue_no="10987",
            notice_type="KURULUS",
            source_pdf_url="https://example.com/pdf",
            raw_text="sample text",
            parse_confidence=0.8,
        )
        assert r.trade_name == "ACME A.S."
        assert r.registry_city == "Istanbul"
        assert r.registry_no == "123456"
        assert r.source_pdf_url == "https://example.com/pdf"
        assert r.raw_text == "sample text"

    def test_defaults(self):
        r = ExtractResult()
        assert r.trade_name is None
        assert r.raw_text == ""
        assert r.parse_confidence == 0.0
        assert r.error is None


class TestExtractResponse:
    def test_structure(self):
        resp = ExtractResponse(
            query="ACME",
            total_processed=1,
            successful=1,
            results=[
                ExtractResult(
                    trade_name="ACME A.S.",
                    notice_type="KURULUS",
                    source_pdf_url="http://x",
                    raw_text="text",
                )
            ],
        )
        assert resp.successful == 1


class TestHealthResponse:
    def test_defaults(self):
        h = HealthResponse()
        assert h.status == "ok"
        assert h.service == "tobb-ocr-rest-api"


class TestErrorResponse:
    def test_structure(self):
        e = ErrorResponse(error_code=ErrorCode.NOT_FOUND, message="not found")
        assert e.error_code == ErrorCode.NOT_FOUND
