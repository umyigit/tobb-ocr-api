from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pdfplumber

from app.config import Settings
from app.core.exceptions import OCRError
from app.core.logging import get_logger

logger = get_logger(__name__)

MIN_TEXT_LENGTH = 50  # Minimum chars to consider text layer sufficient


class OCRPipeline:
    """Two-tier OCR: pdfplumber (text layer) then OCRmyPDF fallback (image PDFs)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract_text(self, pdf_data: bytes) -> str:
        """Extract text from PDF bytes. Tries text layer first, then OCR."""
        text = self._try_text_layer(pdf_data)
        if text and len(text.strip()) >= MIN_TEXT_LENGTH:
            logger.info("ocr_tier1_success", text_length=len(text))
            return text

        logger.info("ocr_tier1_insufficient, falling back to OCRmyPDF")
        return self._try_ocrmypdf(pdf_data)

    def _try_text_layer(self, pdf_data: bytes) -> str:
        """Tier 1: Extract embedded text layer with pdfplumber."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name

            pages_text: list[str] = []
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)

            return "\n".join(pages_text)
        except Exception:
            logger.warning("pdfplumber_failed", exc_info=True)
            return ""
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    def _try_ocrmypdf(self, pdf_data: bytes) -> str:
        """Tier 2: OCRmyPDF subprocess for image-based PDFs."""
        input_path = None
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as inp:
                inp.write(pdf_data)
                input_path = inp.name

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as out:
                output_path = out.name

            cmd = [
                "ocrmypdf",
                "--language",
                self._settings.OCR_LANG,
                "--force-ocr",
                "--deskew",
                "--clean",
                input_path,
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.warning("ocrmypdf_failed", stderr=result.stderr[:500])
                raise OCRError(
                    message="OCRmyPDF islem hatasi",
                    detail=result.stderr[:500],
                )

            # Extract text from the OCR'd PDF
            text = self._try_text_layer_from_path(output_path)
            if not text.strip():
                raise OCRError(message="OCR sonrasi metin cikarilmadi")

            logger.info("ocr_tier2_success", text_length=len(text))
            return text

        except OCRError:
            raise
        except subprocess.TimeoutExpired as exc:
            raise OCRError(message="OCR zaman asimi", detail="timeout=120s") from exc
        except Exception as exc:
            raise OCRError(message="OCR hatasi", detail=str(exc)) from exc
        finally:
            if input_path:
                Path(input_path).unlink(missing_ok=True)
            if output_path:
                Path(output_path).unlink(missing_ok=True)

    @staticmethod
    def _try_text_layer_from_path(pdf_path: str) -> str:
        pages_text: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
        return "\n".join(pages_text)
