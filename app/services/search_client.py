from __future__ import annotations

import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from app.config import Settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.responses import SearchRecord
from app.services import selectors
from app.services.captcha_handler import CaptchaHandler

logger = get_logger(__name__)


class SearchClient:
    """Performs company name search on TOBB (public, no login required)."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        captcha_handler: CaptchaHandler,
    ) -> None:
        self._client = client
        self._settings = settings
        self._captcha = captcha_handler

    async def search(self, trade_name: str) -> tuple[list[SearchRecord], int]:
        """Search and return (results, total_records)."""
        base = self._settings.TOBB_BASE_URL

        # Init session by hitting the search page
        await self._client.get(f"{base}/view/hizlierisim/unvansorgulama.php")

        await asyncio.sleep(self._settings.RATE_LIMIT_DELAY)

        # Solve search captcha
        captcha_text = await self._captcha.solve(context="search")

        # POST search form
        resp = await self._client.post(
            f"{base}/view/hizlierisim/unvansorgulama_ok.php",
            data={
                "UnvanSorgu": trade_name,
                "Captcha": captcha_text,
                "YeniSorgu": "1",
            },
        )
        resp.raise_for_status()

        records, total = self._parse_results(resp.text)

        if not records:
            raise NotFoundError(
                message=f"'{trade_name}' icin sonuc bulunamadi",
                detail=f"query={trade_name}",
            )

        logger.info("search_completed", query=trade_name, result_count=len(records), total=total)
        return records, total

    @staticmethod
    def _parse_results(html: str) -> tuple[list[SearchRecord], int]:
        soup = BeautifulSoup(html, "lxml")
        records: list[SearchRecord] = []
        total = 0

        table = soup.select_one(selectors.SEARCH_RESULT_TABLE)
        if not table:
            return records, total

        # "Toplam Kayıt Sayısı: 384" header'dan toplam sayiyi cek
        header = table.select_one(selectors.SEARCH_TOTAL_HEADER)
        if header:
            match = re.search(r"(\d+)", header.get_text())
            if match:
                total = int(match.group(1))

        # Satirlari parse et: #, Unvan, Sicil No, Tsm
        rows = table.select(selectors.SEARCH_RESULT_ROW)
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            title = cells[1].get_text(strip=True)
            registry_no = cells[2].get_text(strip=True)
            tsm = cells[3].get_text(strip=True)

            records.append(
                SearchRecord(
                    title=title,
                    registry_no=registry_no or None,
                    tsm=tsm or None,
                )
            )

        return records, total
