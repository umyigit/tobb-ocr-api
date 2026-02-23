from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import TOBBBaseError
from app.core.logging import get_logger
from app.schemas.responses import ErrorResponse

logger = get_logger(__name__)


async def tobb_exception_handler(request: Request, exc: TOBBBaseError) -> JSONResponse:
    logger.error(
        "tobb_error",
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        path=request.url.path,
    )
    body = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())
