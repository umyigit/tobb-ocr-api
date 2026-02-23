from __future__ import annotations

import time

from app.core.logging import get_logger

logger = get_logger(__name__)

SESSION_TTL_SECONDS = 30 * 60  # 30 minutes


class SessionManager:
    """Manages PHP session lifecycle: tracks auth state and triggers re-auth when expired."""

    def __init__(self) -> None:
        self._authenticated_at: float | None = None

    @property
    def is_authenticated(self) -> bool:
        if self._authenticated_at is None:
            return False
        elapsed = time.monotonic() - self._authenticated_at
        if elapsed > SESSION_TTL_SECONDS:
            logger.info("session_expired", elapsed_seconds=elapsed)
            self._authenticated_at = None
            return False
        return True

    def mark_authenticated(self) -> None:
        self._authenticated_at = time.monotonic()
        logger.info("session_authenticated")

    def invalidate(self) -> None:
        self._authenticated_at = None
        logger.info("session_invalidated")
