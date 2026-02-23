# TOBB Ticaret Sicil Gazetesi OCR REST API

TOBB Ticaret Sicil Gazetesi üzerinde şirket bazlı arama yapan, ilgili gazete PDF'lerini indirip OCR ile işleyerek yapılandırılmış JSON dönen bir REST API.

## Özellikler

- **Ünvan Sorgulama**: Ticaret ünvanı ile TOBB Ticaret Sicil Gazetesi'nde arama
- **PDF OCR**: İki katmanlı OCR pipeline (pdfplumber text layer + OCRmyPDF fallback)
- **Yapılandırılmış Çıktı**: Sicil ili, sicil no, yayın tarihi, sayı, ilan türü gibi alanları otomatik çıkarma
- **CAPTCHA Çözümü**: Lokal Tesseract OCR ile etik captcha çözümü (3. parti servis yok)
- **Otomatik Oturum Yönetimi**: PHP session takibi, 30dk TTL, otomatik yeniden giriş
- **Kısmi Hata Toleransı**: Tek bir PDF hatası tüm batch'i durdurmaz
- **Docker ile Kolay Deploy**: Tek komutla ayağa kalkar

## Gereksinimler

- Python 3.11+
- Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-tur`, `tesseract-ocr-eng`)
- OCRmyPDF, Ghostscript, Unpaper
- TOBB Ticaret Sicil Gazetesi üyelik bilgileri (email + şifre)

## Kurulum

### Docker ile (Önerilen)

```bash
# 1. .env dosyasını oluştur ve TOBB login bilgilerini yaz
cp .env.example .env
# .env içinde TOBB_LOGIN_EMAIL ve TOBB_LOGIN_PASSWORD değerlerini güncelle

# 2. Docker image'ı build et ve çalıştır
docker build -t tobb-ocr-api -f docker/Dockerfile .
docker run -p 8000:8000 tobb-ocr-api
```

> **Kullanıcı Değişikliği:** Farklı bir TOBB hesabı kullanmak için `.env` dosyasındaki
> `TOBB_LOGIN_EMAIL` ve `TOBB_LOGIN_PASSWORD` değerlerini güncelleyip
> `docker build` komutunu tekrar çalıştırmanız yeterlidir.

### Manuel Kurulum

```bash
# Sistem bağımlılıklar (Ubuntu/Debian)
sudo apt install tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng ocrmypdf ghostscript unpaper

# Python ortamı
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# .env dosyasını oluştur
cp .env.example .env
# .env içine TOBB login bilgilerini yaz

# Çalıştır
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Konfigürasyon

Tüm ayarlar `.env` dosyası üzerinden yönetilir:

| Değişken | Default | Açıklama |
|---|---|---|
| `TOBB_BASE_URL` | `https://www.ticaretsicil.gov.tr` | Site URL |
| `TOBB_LOGIN_EMAIL` | _(zorunlu)_ | Login email |
| `TOBB_LOGIN_PASSWORD` | _(zorunlu)_ | Login şifre |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout (sn) |
| `MAX_RETRIES` | `3` | Max HTTP retry |
| `BACKOFF_FACTOR` | `0.5` | Exponential backoff çarpanı |
| `VERIFY_SSL` | `false` | SSL doğrulama |
| `OCR_LANG` | `tur+eng` | Tesseract dil(ler) |
| `MAX_PDF_MB` | `20` | Max PDF boyutu (MB) |
| `RATE_LIMIT_DELAY` | `1.0` | İstekler arası bekleme (sn) |
| `CAPTCHA_MAX_ATTEMPTS` | `5` | Max captcha deneme |
| `LOG_LEVEL` | `INFO` | Log seviyesi |
| `PDF_DOWNLOAD_DIR` | `/tmp/tobb_pdfs` | Geçici PDF dizini |
| `DEBUG` | `false` | Debug modu |

## API Kullanımı

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "service": "tobb-ocr-rest-api"}
```

### Ünvan Arama

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"trade_name": "ALTINKAYA ELEKTRONİK"}'
```

```json
{
  "query": "ALTINKAYA ELEKTRONİK",
  "total_results": 1,
  "results": [
    {
      "title": "ALTINKAYA ELEKTRONİK CİHAZ KUTULARI SANAYİ TİCARET ANONİM ŞİRKETİ",
      "registry_no": "123456",
      "tsm": "ANKARA",
      "pdf_urls": [
        "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc-123",
        "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=def-456"
      ]
    }
  ]
}
```

### Tam Çıkarım (Arama + PDF + OCR + Parse)

Sadece `trade_name` girin, gerisini sistem halleder (login -> arama -> PDF indirme -> OCR -> parse).

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{"trade_name": "ALTINKAYA ELEKTRONİK"}'
```

```json
{
  "query": "ALTINKAYA ELEKTRONİK",
  "total_processed": 3,
  "successful": 2,
  "results": [
    {
      "trade_name": "ALTINKAYA ELEKTRONİK CİHAZ KUTULARI SANAYİ TİCARET ANONİM ŞİRKETİ",
      "registry_city": "Ankara",
      "registry_no": "123456",
      "publication_date": "15/03/2024",
      "issue_no": "10987",
      "notice_type": "KURULUS",
      "source_pdf_url": "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc-123",
      "raw_text": "Ticaret Sicil Mudurlugu: Ankara ...",
      "parse_confidence": 0.8,
      "error": null
    }
  ]
}
```

## Hata Kodları

Tüm hatalar deterministic JSON olarak döner:

| Kod | HTTP | Durum |
|---|---|---|
| `NOT_FOUND` | 404 | Arama sonucu boş |
| `PDF_FETCH_FAILED` | 502 | PDF indirilemedi |
| `OCR_FAILED` | 500 | Metin çıkarılmadı |
| `PARSING_FAILED` | 422 | Yapısal alan çıkarılmadı |
| `CAPTCHA_FAILED` | 503 | CAPTCHA çözülemedi |
| `AUTH_FAILED` | 401 | TOBB login başarısız |

Örnek hata yanıtı:

```json
{"error_code": "NOT_FOUND", "message": "'XYZ' icin sonuc bulunamadi", "detail": "query=XYZ"}
```

## Mimari

```
İstemci
  │
  ▼
api (FastAPI endpoint'ler, validation, JSON response)
  │
  ▼
extractor (orkestratör)
  ├── auth_client ──► captcha_handler ──► Tesseract OCR
  ├── search_client ─► captcha_handler
  ├── pdf_fetcher
  └── ocr_pipeline ──► pdfplumber (Tier 1) / OCRmyPDF (Tier 2)
        │
        ▼
      parser (regex-based structured field extraction)
```

| Katman | Dosya | Sorumluluk |
|---|---|---|
| api | `app/api/` | Endpoint tanımları, validation, dependency injection |
| auth_client | `app/services/auth_client.py` | TOBB login akışı |
| captcha_handler | `app/services/captcha_handler.py` | Captcha fetch, preprocess, OCR |
| search_client | `app/services/search_client.py` | Ünvan sorgulama, HTML parse |
| pdf_fetcher | `app/services/pdf_fetcher.py` | Authenticated PDF download |
| ocr_pipeline | `app/services/ocr_pipeline.py` | İki katmanlı OCR |
| parser | `app/services/parser.py` | Raw text -> structured fields |
| extractor | `app/services/extractor.py` | Tüm servisleri birleştiren ana iş akışı |

## Testler

```bash
# Tüm testler
pytest

# Sadece unit testler
pytest tests/unit/

# Sadece integration testler
pytest -m integration

# Coverage raporu
pytest --cov=app --cov-report=term-missing
```

## Proje Yapısı

```
tobb-ocr-rest-api/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan
│   ├── config.py                # Pydantic Settings (env-based)
│   ├── api/
│   │   ├── router.py            # Top-level router
│   │   ├── deps.py              # FastAPI dependency injection
│   │   └── v1/                  # health, search, extract endpoint'leri
│   ├── schemas/                 # Pydantic request/response modelleri
│   ├── services/                # İş mantığı katmanları
│   ├── clients/                 # HTTP client factory, session manager
│   ├── core/                    # Exceptions, logging, middleware
│   └── utils/                   # UA rotation, retry, image processing
├── tests/                       # unit, integration, contract testler
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml
├── .env.example
├── .gitignore
└── pyproject.toml
```

## Lisans

Bu proje dahili kullanım için geliştirilmiştir.
