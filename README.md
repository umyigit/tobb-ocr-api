# TOBB Trade Registry Gazette OCR REST API

A REST API that searches companies on the TOBB Trade Registry Gazette, downloads the relevant gazette PDFs, processes them with a three-tier OCR pipeline, and returns structured JSON.

## Features

- **Trade Name Search**: Search the TOBB Trade Registry Gazette by trade name, enriched with gazette PDF URLs
- **PDF OCR**: Three-tier OCR pipeline (pdfplumber text layer → column-aware pytesseract → OCRmyPDF fallback)
- **Column Detection**: Automatic multi-column layout detection and per-column OCR with OpenCV preprocessing
- **CAPTCHA Solving**: Local Tesseract OCR captcha solving (no third-party services)
- **Automatic Session Management**: PHP session tracking, 30min TTL, automatic re-authentication
- **Resilient Auth**: Login retries with cookie cleanup between attempts; session-level re-auth on failure
- **Turkish Character Normalization**: Unicode NFC normalization for external systems (n8n, etc.) and automatic I→İ fallback via `unicode_tr`
- **Search Retry**: Search retries with delay; if not found, retried with Turkish uppercase conversion (ASCII I→İ)
- **PDF Re-auth**: If a PDF fetch returns HTML instead of PDF (expired session), the system re-authenticates and retries
- **Partial Failure Tolerance**: A single PDF failure does not stop the entire batch
- **Easy Docker Deployment**: Up and running with a single command

## Requirements

- Python 3.11+
- Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-tur`)
- OCRmyPDF, Ghostscript, Unpaper
- TOBB Trade Registry Gazette membership credentials (email + password)

## Installation

### From GitHub Container Registry (Quickest)

```bash
# 1. Create .env with your TOBB credentials
cat <<EOF > .env
TOBB_LOGIN_EMAIL=your@email.com
TOBB_LOGIN_PASSWORD=yourpassword
EOF

# 2. Pull and run
docker pull ghcr.io/umyigittr/tobb-ocr-rest-api:latest
docker run -p 8000:8000 --env-file .env ghcr.io/umyigittr/tobb-ocr-rest-api:latest
```

### Build Locally with Docker

```bash
# 1. Create the .env file and set your TOBB login credentials
cp .env.example .env
# Update TOBB_LOGIN_EMAIL and TOBB_LOGIN_PASSWORD in .env

# 2. Build and run the Docker image
docker build -t tobb-ocr-api -f docker/Dockerfile .
docker run -p 8000:8000 tobb-ocr-api
```

> **Switching Users:** To use a different TOBB account, update `TOBB_LOGIN_EMAIL` and
> `TOBB_LOGIN_PASSWORD` in the `.env` file and re-run `docker build`.

### Manual Installation

```bash
# System dependencies (Ubuntu/Debian)
sudo apt install tesseract-ocr tesseract-ocr-tur ocrmypdf ghostscript unpaper

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Create the .env file
cp .env.example .env
# Set your TOBB login credentials in .env

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

All settings are managed via the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `TOBB_BASE_URL` | `https://www.ticaretsicil.gov.tr` | Site URL |
| `TOBB_LOGIN_EMAIL` | _(required)_ | Login email |
| `TOBB_LOGIN_PASSWORD` | _(required)_ | Login password |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout (seconds) |
| `MAX_RETRIES` | `3` | Max HTTP retries |
| `BACKOFF_FACTOR` | `0.5` | Exponential backoff factor |
| `VERIFY_SSL` | `false` | SSL verification |
| `RATE_LIMIT_DELAY` | `1.0` | Delay between requests (seconds) |
| `OCR_LANG` | `tur` | Tesseract language |
| `OCR_DPI` | `300` | Image render resolution for OCR |
| `OCR_COLUMN_DETECTION` | `true` | Enable multi-column layout detection |
| `OCR_MIN_COLUMN_GAP_PX` | `4` | Minimum pixel gap to detect column boundary |
| `OCR_BINARIZE_BLOCK_SIZE` | `31` | Adaptive threshold block size |
| `OCR_DENOISE_STRENGTH` | `10` | OpenCV denoising strength |
| `MAX_PDF_MB` | `20` | Max PDF size (MB) |
| `CAPTCHA_MAX_ATTEMPTS` | `5` | Max captcha attempts |
| `LOG_LEVEL` | `INFO` | Log level |
| `DEBUG` | `false` | Debug mode |
| `PDF_DOWNLOAD_DIR` | `/tmp/tobb_pdfs` | Temporary PDF directory |

## API Usage

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "service": "tobb-ocr-rest-api"}
```

### Trade Name Search

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"trade_name": "ALTINKAYA ELEKTRONİK"}'
```

```json
{
  "query": "ALTINKAYA ELEKTRONİK",
  "total_results": 1,
  "total_records": 5,
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

### PDF Text Extraction (OCR)

Provide a `pdf_url` from the search results and the system handles the rest (login → PDF download → OCR → raw text).

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc-123"}'
```

```json
{
  "source_pdf_url": "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc-123",
  "raw_text": "Ticaret Sicil Mudurlugu: Ankara ...",
  "error": null
}
```

## OCR Pipeline

The OCR pipeline uses a three-tier fallback strategy:

```
PDF bytes
  │
  ▼
Tier 1: pdfplumber (text layer extraction, layout-aware)
  │  ≥50 chars? → Done
  ▼
Tier 2: Column-aware pytesseract
  │  1. Render page to image (300 DPI)
  │  2. Detect columns via vertical density analysis (OpenCV)
  │  3. Split into column images
  │  4. Preprocess each column:
  │     - Grayscale → Denoise → Adaptive binarization → Morphological closing
  │  5. Tesseract OCR per column (--psm 6 --oem 1, lang=tur)
  │  ≥50 chars? → Done
  ▼
Tier 3: OCRmyPDF subprocess fallback
  │  --force-ocr --deskew --clean --language tur
  │  timeout=120s
  ▼
Raw text result
```

## Error Codes

All errors are returned as deterministic JSON:

| Code | HTTP | Description |
|---|---|---|
| `NOT_FOUND` | 404 | No search results found |
| `PDF_FETCH_FAILED` | 502 | PDF could not be downloaded |
| `OCR_FAILED` | 500 | Text could not be extracted |
| `PARSING_FAILED` | 422 | Structured fields could not be extracted |
| `CAPTCHA_FAILED` | 503 | CAPTCHA could not be solved |
| `AUTH_FAILED` | 401 | TOBB login failed |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

Example error response:

```json
{"error_code": "NOT_FOUND", "message": "'XYZ' icin sonuc bulunamadi", "detail": "query=XYZ"}
```

## Architecture

```
Client
  │
  ├─ POST /search ──► search_client ─► captcha_handler ──► Tesseract OCR
  │                     └── gazette_client (enriches results with PDF URLs)
  │
  └─ POST /extract ─► extractor (orchestrator)
                        ├── auth_client ──► captcha_handler ──► Tesseract OCR
                        │     └── login retry with cookie cleanup + session-level re-auth
                        ├── pdf_fetcher
                        │     └── re-auth on expired session (HTML instead of PDF)
                        └── ocr_pipeline
                              ├── Tier 1: pdfplumber (text layer)
                              ├── Tier 2: Pillow + OpenCV + pytesseract (column-aware image OCR)
                              └── Tier 3: OCRmyPDF subprocess (fallback)
```

| Layer | File | Responsibility |
|---|---|---|
| api | `app/api/` | Endpoint definitions, validation, dependency injection |
| auth_client | `app/services/auth_client.py` | TOBB login flow, session management |
| captcha_handler | `app/services/captcha_handler.py` | Captcha fetch, preprocess, OCR |
| search_client | `app/services/search_client.py` | Public trade name search, HTML parsing |
| gazette_client | `app/services/gazette_client.py` | Authenticated gazette search, PDF URL enrichment |
| pdf_fetcher | `app/services/pdf_fetcher.py` | Authenticated PDF download (7 fallback strategies) |
| ocr_pipeline | `app/services/ocr_pipeline.py` | Three-tier OCR pipeline |
| parser | `app/services/parser.py` | Raw text → structured fields (regex-based) |
| extractor | `app/services/extractor.py` | Orchestrator: auth → PDF fetch → OCR |
| tsm_mapping | `app/services/tsm_mapping.py` | City name to SicilMudurluguId mapping (250+ cities) |
| session_manager | `app/clients/session_manager.py` | PHP session lifecycle (30min TTL) |
| image_processing | `app/utils/image_processing.py` | Column detection, denoising, binarization |

## Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest -m integration

# Coverage report
pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
tobb-ocr-rest-api/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan
│   ├── config.py                # Pydantic Settings (env-based)
│   ├── api/
│   │   ├── router.py            # Top-level router
│   │   ├── deps.py              # FastAPI dependency injection
│   │   └── v1/                  # health, search, extract endpoints
│   ├── schemas/
│   │   ├── requests.py          # SearchRequest, ExtractRequest
│   │   ├── responses.py         # SearchResponse, ExtractResult, etc.
│   │   └── enums.py             # ErrorCode, NoticeType
│   ├── services/
│   │   ├── auth_client.py       # TOBB login flow
│   │   ├── search_client.py     # Public company search
│   │   ├── gazette_client.py    # Authenticated gazette search
│   │   ├── pdf_fetcher.py       # PDF download
│   │   ├── ocr_pipeline.py      # Three-tier OCR
│   │   ├── captcha_handler.py   # Captcha solving
│   │   ├── parser.py            # Structured field extraction
│   │   ├── extractor.py         # Main orchestrator
│   │   ├── tsm_mapping.py       # City ID mapping
│   │   └── selectors.py         # CSS selectors
│   ├── clients/
│   │   ├── http_client.py       # httpx AsyncClient factory
│   │   └── session_manager.py   # PHP session lifecycle
│   ├── core/
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   ├── logging.py           # structlog setup
│   │   └── middleware.py        # Global exception handler
│   └── utils/
│       ├── image_processing.py  # OCR image preprocessing
│       ├── ua_rotation.py       # User-Agent rotation
│       └── retry.py             # Retry utilities
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── contract/                # API contract tests
│   ├── fixtures/                # Test fixtures
│   └── conftest.py
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml
├── .env.example
├── .gitignore
└── pyproject.toml
```

## License

This project is developed for internal use.
