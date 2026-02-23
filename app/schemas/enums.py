from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    PDF_FETCH_FAILED = "PDF_FETCH_FAILED"
    OCR_FAILED = "OCR_FAILED"
    PARSING_FAILED = "PARSING_FAILED"
    CAPTCHA_FAILED = "CAPTCHA_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class NoticeType(str, Enum):
    KURULUS = "KURULUS"
    DEGISIKLIK = "DEGISIKLIK"
    KAPANIS = "KAPANIS"
    DIGER = "DIGER"
