# TOBB Trade Registry Gazette OCR REST API

A REST API that searches companies on the TOBB Trade Registry Gazette, downloads the relevant gazette PDFs, processes them with OCR, and returns structured JSON.

## Features

- **Trade Name Search**: Search the TOBB Trade Registry Gazette by trade name
- **PDF OCR**: Two-tier OCR pipeline (pdfplumber text layer + OCRmyPDF fallback)
- **Structured Output**: Automatically extracts registry city, registry no, publication date, issue no, notice type
- **CAPTCHA Solving**: Ethical local Tesseract OCR captcha solving (no third-party services)
- **Automatic Session Management**: PHP session tracking, 30min TTL, automatic re-authentication
- **Partial Failure Tolerance**: A single PDF failure does not stop the entire batch
- **Easy Docker Deployment**: Up and running with a single command

## Requirements

- Python 3.11+
- Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-tur`, `tesseract-ocr-eng`)
- OCRmyPDF, Ghostscript, Unpaper
- TOBB Trade Registry Gazette membership credentials (email + password)

## Installation

### With Docker (Recommended)

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
sudo apt install tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng ocrmypdf ghostscript unpaper

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
| `OCR_LANG` | `tur+eng` | Tesseract language(s) |
| `MAX_PDF_MB` | `20` | Max PDF size (MB) |
| `RATE_LIMIT_DELAY` | `1.0` | Delay between requests (seconds) |
| `CAPTCHA_MAX_ATTEMPTS` | `5` | Max captcha attempts |
| `LOG_LEVEL` | `INFO` | Log level |
| `PDF_DOWNLOAD_DIR` | `/tmp/tobb_pdfs` | Temporary PDF directory |
| `DEBUG` | `false` | Debug mode |

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

### Full Extraction (Search + PDF + OCR + Parse)

Just provide the `trade_name` and the system handles the rest (login -> search -> PDF download -> OCR -> parse).

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

Example error response:

```json
{"error_code": "NOT_FOUND", "message": "'XYZ' icin sonuc bulunamadi", "detail": "query=XYZ"}
```

## Architecture

```
Client
  │
  ▼
api (FastAPI endpoints, validation, JSON response)
  │
  ▼
extractor (orchestrator)
  ├── auth_client ──► captcha_handler ──► Tesseract OCR
  ├── search_client ─► captcha_handler
  ├── pdf_fetcher
  └── ocr_pipeline ──► pdfplumber (Tier 1) / OCRmyPDF (Tier 2)
        │
        ▼
      parser (regex-based structured field extraction)
```

| Layer | File | Responsibility |
|---|---|---|
| api | `app/api/` | Endpoint definitions, validation, dependency injection |
| auth_client | `app/services/auth_client.py` | TOBB login flow |
| captcha_handler | `app/services/captcha_handler.py` | Captcha fetch, preprocess, OCR |
| search_client | `app/services/search_client.py` | Trade name search, HTML parsing |
| pdf_fetcher | `app/services/pdf_fetcher.py` | Authenticated PDF download |
| ocr_pipeline | `app/services/ocr_pipeline.py` | Two-tier OCR |
| parser | `app/services/parser.py` | Raw text -> structured fields |
| extractor | `app/services/extractor.py` | Main workflow orchestrating all services |

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
│   ├── schemas/                 # Pydantic request/response models
│   ├── services/                # Business logic layers
│   ├── clients/                 # HTTP client factory, session manager
│   ├── core/                    # Exceptions, logging, middleware
│   └── utils/                   # UA rotation, retry, image processing
├── tests/                       # unit, integration, contract tests
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml
├── .env.example
├── .gitignore
└── pyproject.toml
```

## License

This project is developed for internal use.
