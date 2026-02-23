from __future__ import annotations

import httpx

from app.config import Settings
from app.utils.ua_rotation import get_random_ua


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(
        retries=settings.MAX_RETRIES,
        verify=settings.VERIFY_SSL,
    )
    return httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(settings.REQUEST_TIMEOUT),
        verify=settings.VERIFY_SSL,
        headers={"User-Agent": get_random_ua()},
        follow_redirects=True,
    )


async def close_http_client(client: httpx.AsyncClient) -> None:
    await client.aclose()
