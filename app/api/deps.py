from __future__ import annotations

from functools import lru_cache

import httpx
from fastapi import Depends, Request

from app.clients.session_manager import SessionManager
from app.config import Settings
from app.services.auth_client import AuthClient
from app.services.captcha_handler import CaptchaHandler
from app.services.extractor import Extractor
from app.services.gazette_client import GazetteClient
from app.services.ocr_pipeline import OCRPipeline
from app.services.pdf_fetcher import PDFFetcher
from app.services.search_client import SearchClient

# Singletons
_session_manager = SessionManager()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_session_manager() -> SessionManager:
    return _session_manager


def get_captcha_handler(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> CaptchaHandler:
    return CaptchaHandler(client=client, settings=settings)


def get_search_client(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
    captcha: CaptchaHandler = Depends(get_captcha_handler),
) -> SearchClient:
    return SearchClient(client=client, settings=settings, captcha_handler=captcha)


def get_auth_client(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
    captcha: CaptchaHandler = Depends(get_captcha_handler),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> AuthClient:
    return AuthClient(
        client=client, settings=settings, captcha_handler=captcha, session_manager=session_mgr
    )


def get_gazette_client(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> GazetteClient:
    return GazetteClient(client=client, settings=settings)


def get_pdf_fetcher(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> PDFFetcher:
    return PDFFetcher(client=client, settings=settings)


def get_ocr_pipeline(settings: Settings = Depends(get_settings)) -> OCRPipeline:
    return OCRPipeline(settings=settings)


def get_extractor(
    auth: AuthClient = Depends(get_auth_client),
    pdf_fetcher: PDFFetcher = Depends(get_pdf_fetcher),
    ocr: OCRPipeline = Depends(get_ocr_pipeline),
) -> Extractor:
    return Extractor(
        auth_client=auth,
        pdf_fetcher=pdf_fetcher,
        ocr_pipeline=ocr,
    )
