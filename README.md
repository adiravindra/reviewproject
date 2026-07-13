# ReviewInsight

ReviewInsight is a lightweight proof of concept that turns reviews from one public HTML page into a structured product readout. FastAPI collects and analyzes reviews; a separate Streamlit dashboard presents deterministic metrics and AI-generated insights.

## Architecture

```text
Streamlit :8501
  -> POST FastAPI :8000/api/analyze
       -> bounded static HTTP collection
       -> JSON-LD first, conservative HTML review cards second
       -> one structured LangChain agent call (Gemini or Groq)
       -> deterministic Python metrics
       -> validated report
```

The API exposes only `GET /health` and `POST /api/analyze`. The dashboard communicates with it over HTTP and never imports backend application services.

## Supported sources and limitations

- The URL must be public `http` or `https` without embedded credentials.
- Collection uses ordinary HTTP requests only; it does not render JavaScript.
- JSON-LD/Schema.org reviews are preferred. Conservative static review-card selectors are the fallback.
- One page, at most three redirects, and at most 40 unique reviews are processed.
- At least two reviews are required.
- Pagination, authenticated pages, anti-bot bypasses, browser automation, databases, history, accounts, and background jobs are deliberately excluded.

The demonstration page is `https://web-scraping.dev/product/1`. External markup can change, so deterministic tests use a committed HTML fixture.

## Installation

Python 3.12 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The application reads configuration from environment variables. Load `.env` with your preferred local environment workflow or set the values in each terminal session.

## Provider configuration

Set at least one provider credential:

```powershell
$env:GOOGLE_API_KEY = "your-key"
# or
$env:GROQ_API_KEY = "your-key"
```

Default models are `gemini-2.5-flash-lite` and `llama-3.3-70b-versatile`. Override them with `REVIEWINSIGHT_GOOGLE_MODEL` and `REVIEWINSIGHT_GROQ_MODEL`. Free-tier eligibility, quotas, and model access are controlled by the Google or Groq account, not by ReviewInsight.

Never commit API keys or paste them into logs.

## Two-terminal startup

Start FastAPI in the first terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start Streamlit independently in the second terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Open `http://127.0.0.1:8501` and use `https://web-scraping.dev/product/1` as the sample URL.

## API example

```powershell
$body = @{ url = "https://web-scraping.dev/product/1"; provider = "google" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/analyze -ContentType application/json -Body $body
```

Public errors use a small envelope such as:

```json
{"detail":{"code":"no_reviews","message":"At least two public reviews are required."}}
```

## Tests

Tests do not call live websites or providers.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall backend dashboard tests
```

## Connection-error resolution

If the dashboard says the backend is unreachable, run the FastAPI command above in a separate terminal and verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The expected response contains `status: ok`. ReviewInsight intentionally has no launcher that spawns both processes; starting them explicitly keeps Windows process ownership and localhost failures visible.
