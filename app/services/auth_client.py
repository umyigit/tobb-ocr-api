from __future__ import annotations

import asyncio

import httpx

from app.clients.session_manager import SessionManager
from app.config import Settings
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.services.captcha_handler import CaptchaHandler

logger = get_logger(__name__)


class AuthClient:
    """Handles TOBB login: session init, captcha solve, credential POST."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        captcha_handler: CaptchaHandler,
        session_manager: SessionManager,
    ) -> None:
        self._client = client
        self._settings = settings
        self._captcha = captcha_handler
        self._session = session_manager

    async def ensure_authenticated(self) -> None:
        """Login if session is expired or not yet established."""
        if self._session.is_authenticated:
            return
        await self._login_with_retry()

    async def logout(self) -> None:
        """Logout from TOBB and clear session state."""
        if not self._session.is_authenticated:
            return
        self._session.invalidate()
        self._client.cookies.clear()
        logger.info("logout_complete")

    async def _login_with_retry(self) -> None:
        """Try login up to MAX_RETRIES times. Captcha errors or unexpected responses trigger retry."""
        max_attempts = self._settings.MAX_RETRIES
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                await self._login()
                return
            except AuthError as exc:
                # Missing credentials → no point retrying
                if "bilgileri eksik" in exc.message:
                    raise
                last_error = exc
                logger.warning(
                    "login_attempt_failed",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(self._settings.RATE_LIMIT_DELAY * attempt)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "login_attempt_failed",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(self._settings.RATE_LIMIT_DELAY * attempt)

        raise AuthError(
            message=f"TOBB login {max_attempts} denemede basarisiz",
            detail=str(last_error) if last_error else None,
        )

    async def _login(self) -> None:
        base = self._settings.TOBB_BASE_URL
        email = self._settings.TOBB_LOGIN_EMAIL
        password = self._settings.TOBB_LOGIN_PASSWORD.get_secret_value()

        if not email or not password:
            raise AuthError(
                message="TOBB login bilgileri eksik",
                detail="TOBB_LOGIN_EMAIL ve TOBB_LOGIN_PASSWORD env degiskenleri gerekli",
            )

        # Init PHP session
        await self._client.get(base)

        await asyncio.sleep(self._settings.RATE_LIMIT_DELAY)

        # Solve login captcha
        captcha_text = await self._captcha.solve(context="login")

        # POST login
        resp = await self._client.post(
            f"{base}/view/modal/uyegirisi_ok.php",
            data={
                "LoginEmail": email,
                "LoginSifre": password,
                "Captcha": captcha_text,
            },
        )
        resp.raise_for_status()

        # Response body "1" means success
        if resp.text.strip() == "1":
            self._session.mark_authenticated()
            logger.info("login_success", email=email)
        else:
            self._session.invalidate()
            raise AuthError(
                message="TOBB login basarisiz",
                detail=f"response={resp.text.strip()[:100]}",
            )
