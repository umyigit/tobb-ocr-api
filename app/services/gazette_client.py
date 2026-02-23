"""Client for the TOBB ilan goruntuleme (gazette announcement viewer) page.

This page requires an authenticated session. It searches by SicilMudurluguId
and either TicSicNo (registry number) or TicaretUnvani (trade name).
Results contain gazette announcements with PDF download links.
"""

from __future__ import annotations

import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from app.config import Settings
from app.core.logging import get_logger
from app.schemas.responses import GazetteRecord
from app.services import selectors

logger = get_logger(__name__)

# Base URL fragment for resolving relative PDF links
_PDF_BASE = "view/hizlierisim/"


class GazetteClient:
    """Searches the ilan goruntuleme page for gazette announcements (requires login)."""

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def search(
        self,
        sicil_mudurlugu_id: str,
        tic_sic_no: str = "",
        ticaret_unvani: str = "",
    ) -> list[GazetteRecord]:
        """Search ilan goruntuleme and return gazette records.

        At least one of tic_sic_no or ticaret_unvani must be provided.
        ticaret_unvani requires minimum 5 characters on the TOBB side.
        """
        base = self._settings.TOBB_BASE_URL

        await asyncio.sleep(self._settings.RATE_LIMIT_DELAY)

        resp = await self._client.post(
            f"{base}/{_PDF_BASE}ilangoruntuleme_ok.php",
            data={
                "SicilMudurluguId": sicil_mudurlugu_id,
                "TicSicNo": tic_sic_no,
                "TicaretUnvani": ticaret_unvani,
                "BagliIlan": "",
                "Tarih": "",
                "Tarih1": "",
                "Tarih2": "",
            },
        )
        resp.raise_for_status()

        records = self._parse_results(resp.text)
        logger.info(
            "gazette_search_completed",
            sicil_mudurlugu_id=sicil_mudurlugu_id,
            tic_sic_no=tic_sic_no,
            ticaret_unvani=ticaret_unvani,
            result_count=len(records),
        )
        return records

    def _parse_results(self, html: str) -> list[GazetteRecord]:
        """Parse the ilan goruntuleme results HTML table.

        Table columns (10 total):
        0: Mudurluk, 1: Sicil No, 2: Unvan, 3: Yayin Tarihi,
        4: Sayi, 5: Sayfa, 6: Ilan Turu, 7: Gazete (PDF link),
        8: Sepete Ekle, 9: Geri Bildirim
        """
        base = self._settings.TOBB_BASE_URL
        soup = BeautifulSoup(html, "lxml")
        records: list[GazetteRecord] = []

        table = soup.select_one(selectors.ILAN_RESULT_TABLE)
        if not table:
            return records

        # Log total count from the span if present
        total_span = soup.find("span", string=re.compile(r"Adet\)", re.IGNORECASE))
        if total_span:
            match = re.search(r"\((\d+)\s*Adet\)", total_span.get_text())
            if match:
                logger.info("gazette_total_results", total=int(match.group(1)))

        rows = table.select(selectors.ILAN_RESULT_ROW)
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            mudurluk = cells[0].get_text(strip=True)
            sicil_no = cells[1].get_text(strip=True)
            unvan = cells[2].get_text(strip=True)
            yayin_tarihi = cells[3].get_text(strip=True) or None
            sayi = cells[4].get_text(strip=True) or None
            sayfa = cells[5].get_text(strip=True) or None
            ilan_turu = cells[6].get_text(strip=True) or None

            # Extract PDF link from column 7
            pdf_url: str | None = None
            pdf_link = cells[7].select_one(selectors.ILAN_PDF_LINK)
            if pdf_link:
                href = pdf_link.get("href", "")
                if href:
                    # href is like "pdf_goster.php?Guid=..."
                    # Build full URL
                    if href.startswith("http"):
                        pdf_url = href
                    else:
                        pdf_url = f"{base}/{_PDF_BASE}{href}"

            records.append(
                GazetteRecord(
                    mudurluk=mudurluk,
                    sicil_no=sicil_no,
                    unvan=unvan,
                    yayin_tarihi=yayin_tarihi,
                    sayi=sayi,
                    sayfa=sayfa,
                    ilan_turu=ilan_turu,
                    pdf_url=pdf_url,
                )
            )

        return records
