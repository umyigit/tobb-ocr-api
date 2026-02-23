from __future__ import annotations

from app.schemas.enums import NoticeType
from app.services.parser import GazetteParser


class TestGazetteParser:
    def setup_method(self):
        self.parser = GazetteParser()

    def test_extract_registry_city(self):
        text = "Istanbul Ticaret Sicil Müdürlüğü: Istanbul"
        result = self.parser.parse(text)
        assert result.registry_city == "Istanbul"

    def test_extract_registry_no(self):
        text = "Sicil No: 123456"
        result = self.parser.parse(text)
        assert result.registry_no == "123456"

    def test_extract_publication_date_dot(self):
        text = "Tarih: 15.03.2024 ilan"
        result = self.parser.parse(text)
        assert result.publication_date == "15/03/2024"

    def test_extract_publication_date_slash(self):
        text = "Tarih: 15/03/2024 ilan"
        result = self.parser.parse(text)
        assert result.publication_date == "15/03/2024"

    def test_extract_issue_no(self):
        text = "Sayı: 10987"
        result = self.parser.parse(text)
        assert result.issue_no == "10987"

    def test_classify_kurulus(self):
        text = "Bu ilan kuruluş tescil ilanıdır"
        result = self.parser.parse(text)
        assert result.notice_type == NoticeType.KURULUS

    def test_classify_degisiklik(self):
        text = "Şirket değişiklik tadil ilanı"
        result = self.parser.parse(text)
        assert result.notice_type == NoticeType.DEGISIKLIK

    def test_classify_kapanis(self):
        text = "Tasfiye ve terkin ilanı"
        result = self.parser.parse(text)
        assert result.notice_type == NoticeType.KAPANIS

    def test_classify_diger(self):
        text = "Genel bilgilendirme metni"
        result = self.parser.parse(text)
        assert result.notice_type == NoticeType.DIGER

    def test_confidence_all_fields(self):
        text = (
            "Istanbul Ticaret Sicil Müdürlüğü: Istanbul\n"
            "Sicil No: 123456\n"
            "Tarih: 15/03/2024\n"
            "Sayı: 10987\n"
            "Kuruluş tescil ilanı"
        )
        result = self.parser.parse(text)
        assert result.parse_confidence == 1.0

    def test_confidence_no_fields(self):
        text = "random text without any fields"
        result = self.parser.parse(text)
        # notice_type still matches DIGER
        assert result.parse_confidence == pytest.approx(1 / 5)

    def test_empty_text(self):
        result = self.parser.parse("")
        assert result.raw_text == ""


import pytest  # noqa: E402
