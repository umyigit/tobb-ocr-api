from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.clients.http_client import close_http_client, create_http_client
from app.config import Settings
from app.core.exceptions import TOBBBaseError
from app.core.logging import setup_logging
from app.core.middleware import tobb_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    setup_logging(log_level=settings.LOG_LEVEL, debug=settings.DEBUG)
    app.state.settings = settings
    app.state.http_client = create_http_client(settings)
    yield
    await close_http_client(app.state.http_client)


def create_app() -> FastAPI:
    app = FastAPI(
        title="TOBB Ticaret Sicil Gazetesi OCR API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_exception_handler(TOBBBaseError, tobb_exception_handler)
    app.include_router(api_router)
    return app


app = create_app()
