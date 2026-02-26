from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # TOBB Site
    TOBB_BASE_URL: str = "https://www.ticaretsicil.gov.tr"
    TOBB_LOGIN_EMAIL: str = ""
    TOBB_LOGIN_PASSWORD: SecretStr = SecretStr("")

    # HTTP
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.5
    VERIFY_SSL: bool = False
    RATE_LIMIT_DELAY: float = 1.0

    # OCR
    OCR_LANG: str = "tur+eng"
    MAX_PDF_MB: int = 20
    OCR_DPI: int = 300
    OCR_COLUMN_DETECTION: bool = True
    OCR_MIN_COLUMN_GAP_PX: int = 4
    OCR_BINARIZE_BLOCK_SIZE: int = 31
    OCR_DENOISE_STRENGTH: int = 10

    # CAPTCHA
    CAPTCHA_MAX_ATTEMPTS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Temp
    PDF_DOWNLOAD_DIR: str = "/tmp/tobb_pdfs"
