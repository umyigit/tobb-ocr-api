from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.config import Settings
from app.core.exceptions import OCRError
from app.services.ocr_pipeline import OCRPipeline


@pytest.fixture
def pipeline():
    settings = Settings(OCR_LANG="tur")
    return OCRPipeline(settings=settings)


class TestOCRPipeline:
    def test_tier1_success(self, pipeline):
        """When pdfplumber extracts enough text, no further tiers are called."""
        long_text = "A" * 100
        with patch.object(pipeline, "_try_text_layer", return_value=long_text):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == long_text

    def test_tier1_insufficient_triggers_tier1_5_then_tier2(self, pipeline):
        """Short text from Tier 1, empty from Tier 1.5, triggers OCRmyPDF."""
        with (
            patch.object(pipeline, "_try_text_layer", return_value="short"),
            patch.object(pipeline, "_try_column_aware_ocr", return_value=""),
            patch.object(pipeline, "_try_ocrmypdf", return_value="OCR result text here"),
        ):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == "OCR result text here"

    def test_tier1_5_success_skips_tier2(self, pipeline):
        """When column-aware OCR produces enough text, OCRmyPDF is not called."""
        long_text = "B" * 100
        with (
            patch.object(pipeline, "_try_text_layer", return_value=""),
            patch.object(pipeline, "_try_column_aware_ocr", return_value=long_text),
            patch.object(pipeline, "_try_ocrmypdf") as mock_ocrmypdf,
        ):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == long_text
        mock_ocrmypdf.assert_not_called()

    def test_tier1_5_failure_falls_to_tier2(self, pipeline):
        """When column-aware OCR returns empty, falls through to OCRmyPDF."""
        fallback_text = "fallback text " * 10
        with (
            patch.object(pipeline, "_try_text_layer", return_value=""),
            patch.object(pipeline, "_try_column_aware_ocr", return_value=""),
            patch.object(pipeline, "_try_ocrmypdf", return_value=fallback_text),
        ):
            result = pipeline.extract_text(b"fake-pdf")
        assert result == fallback_text

    def test_tier2_failure_raises(self, pipeline):
        """OCRmyPDF failure raises OCRError."""
        with (
            patch.object(pipeline, "_try_text_layer", return_value=""),
            patch.object(pipeline, "_try_column_aware_ocr", return_value=""),
            patch.object(pipeline, "_try_ocrmypdf", side_effect=OCRError(message="fail")),
        ):
            with pytest.raises(OCRError):
                pipeline.extract_text(b"fake-pdf")

    def test_try_text_layer_bad_pdf(self, pipeline):
        """Corrupt PDF returns empty string, doesn't raise."""
        result = pipeline._try_text_layer(b"not a pdf")
        assert result == ""

    def test_column_detection_disabled(self, pipeline):
        """When OCR_COLUMN_DETECTION is False, treats page as single column."""
        pipeline._settings.OCR_COLUMN_DETECTION = False

        mock_page = MagicMock()
        mock_page_image = MagicMock()
        mock_page_image.original = Image.new("RGB", (200, 300), "white")
        mock_page.to_image.return_value = mock_page_image

        with patch("app.services.ocr_pipeline.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "single column text"
            result = pipeline._ocr_single_page(mock_page, 0)

        assert mock_tess.image_to_string.call_count == 1
        assert "single column text" in result
