from __future__ import annotations


class TOBBBaseError(Exception):
    """Base exception for all TOBB OCR API errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(TOBBBaseError):
    status_code = 404
    error_code = "NOT_FOUND"


class PDFFetchError(TOBBBaseError):
    status_code = 502
    error_code = "PDF_FETCH_FAILED"


class OCRError(TOBBBaseError):
    status_code = 500
    error_code = "OCR_FAILED"


class ParsingError(TOBBBaseError):
    status_code = 422
    error_code = "PARSING_FAILED"


class CaptchaError(TOBBBaseError):
    status_code = 503
    error_code = "CAPTCHA_FAILED"


class AuthError(TOBBBaseError):
    status_code = 401
    error_code = "AUTH_FAILED"
