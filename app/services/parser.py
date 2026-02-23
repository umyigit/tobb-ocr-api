from __future__ import annotations

import re

from app.core.logging import get_logger
from app.schemas.enums import NoticeType
from app.schemas.responses import ParsedGazette

logger = get_logger(__name__)

TOTAL_FIELDS = 5  # registry_city, registry_no, publication_date, issue_no, notice_type


class GazetteParser:
    """Parses raw OCR text into structured gazette fields using regex patterns."""

    REGISTRY_CITY = re.compile(r"Ticaret\s+Sicil.*?[Mm][uü]d[uü]rl[uü][gğ][uü]\s*[:\-]?\s*(.+?)(?:\n|$)", re.IGNORECASE)
    REGISTRY_NO = re.compile(r"Sicil\s+No\s*[:\-]?\s*(\d+)", re.IGNORECASE)
    PUBLICATION_DATE = re.compile(r"(\d{2}[./]\d{2}[./]\d{4})")
    ISSUE_NO = re.compile(r"[Ss]ay[iıİ]\s*[:\-]?\s*(\d+)")

    NOTICE_KEYWORDS: dict[NoticeType, list[str]] = {
        NoticeType.KURULUS: ["kuruluş", "kurulus", "tescil", "yeni kayıt", "yeni kayit"],
        NoticeType.DEGISIKLIK: ["değişiklik", "degisiklik", "tadil", "değişik", "degisik"],
        NoticeType.KAPANIS: ["kapanış", "kapanis", "tasfiye", "terkin", "fesih"],
    }

    def parse(self, raw_text: str) -> ParsedGazette:
        found = 0

        registry_city = self._extract(self.REGISTRY_CITY, raw_text)
        if registry_city:
            found += 1

        registry_no = self._extract(self.REGISTRY_NO, raw_text)
        if registry_no:
            found += 1

        publication_date = self._extract_date(raw_text)
        if publication_date:
            found += 1

        issue_no = self._extract(self.ISSUE_NO, raw_text)
        if issue_no:
            found += 1

        notice_type = self._classify_notice(raw_text)
        if notice_type:
            found += 1

        confidence = found / TOTAL_FIELDS

        logger.info(
            "gazette_parsed",
            found_fields=found,
            confidence=confidence,
            registry_city=registry_city,
            registry_no=registry_no,
        )

        return ParsedGazette(
            registry_city=registry_city,
            registry_no=registry_no,
            publication_date=publication_date,
            issue_no=issue_no,
            notice_type=notice_type,
            raw_text=raw_text,
            parse_confidence=confidence,
        )

    @staticmethod
    def _extract(pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    def _extract_date(self, text: str) -> str | None:
        match = self.PUBLICATION_DATE.search(text)
        if not match:
            return None
        raw = match.group(1)
        # Normalize to DD/MM/YYYY
        return raw.replace(".", "/")

    def _classify_notice(self, text: str) -> NoticeType | None:
        lower = text.lower()
        for notice_type, keywords in self.NOTICE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return notice_type
        return NoticeType.DIGER
