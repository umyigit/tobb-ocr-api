from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.core.exceptions import OCRError
from app.services.ocr_pipeline import OCRPipeline


@pytest.fixture
def pipeline():
    settings = Settings(OCR_LANG="tur+eng")
    return OCRPipeline(settings=settings)


class TestOCRPipeline:
    def test_tier1_success(self, pipeline):
        """When pdfplumber extracts enough text, no OCRmyPDF fallback."""
        long_text = "A" * 100
        with patch.object(pipeline, "_try_text_layer", return_value=long_text):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == long_text

    def test_tier1_insufficient_triggers_tier2(self, pipeline):
        """Short text triggers OCRmyPDF fallback."""
        with (
            patch.object(pipeline, "_try_text_layer", return_value="short"),
            patch.object(pipeline, "_try_ocrmypdf", return_value="OCR result text here"),
        ):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == "OCR result text here"

    def test_tier2_failure_raises(self, pipeline):
        """OCRmyPDF failure raises OCRError."""
        with (
            patch.object(pipeline, "_try_text_layer", return_value=""),
            patch.object(pipeline, "_try_ocrmypdf", side_effect=OCRError(message="fail")),
        ):
            with pytest.raises(OCRError):
                pipeline.extract_text(b"fake-pdf")

    def test_try_text_layer_bad_pdf(self, pipeline):
        """Corrupt PDF returns empty string, doesn't raise."""
        result = pipeline._try_text_layer(b"not a pdf")
        assert result == ""
