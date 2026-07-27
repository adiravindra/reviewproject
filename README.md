# Review Intelligence

Review Intelligence is a local application that turns public customer reviews
into a clear, evidence-backed report. It imports reviews from an Amazon product
or Google Maps place, lets you inspect the source evidence, uses Groq to find
sentiment and recurring themes, and saves successful reports in local SQLite
history at `data/review_history.db`.

## How it works

1. Import 10, 20, 50, or 100 reviews with Apify, or load the bundled demo data.
2. Inspect the collected ratings, dates, text, and source details.
3. Analyze the first 40 reviews with Groq.
4. Explore the summary, sentiment, themes, strengths, concerns, and suggested
   actions.
5. Reopen saved reports from the local history sidebar.

Live imports are cached for 30 days. Repeating an import uses the cache;
**Refresh from source** is the only action that deliberately contacts Apify
again and may use provider quota.

## Tech stack

| Area | Technology |
|---|---|
| Dashboard | Streamlit |
| API | FastAPI and Uvicorn |
| AI analysis | Groq through LangChain |
| Review imports | Apify Actors |
| Local storage | SQLite |
| Parsing and HTTP | Beautiful Soup, Requests, and HTTPX |
| Tests | Python `unittest` |

## 1. Create the required accounts

### Groq

1. [Create a Groq account and open API Keys](https://console.groq.com/keys).
2. Create a key and copy it.
3. Save it as `GROQ_API_KEY` in the project `.env` file.

Groq is required only when you select **Analyze with Groq**.

### Apify

1. [Create an Apify account](https://console.apify.com/sign-up).
2. Open **Settings > API & Integrations** and create or copy an
   [Apify API token](https://docs.apify.com/integrations/api).
3. Save it as `APIFY_API_TOKEN` in the project `.env` file.

Apify is required for live Amazon and Google Maps imports. Provider usage may
consume free-plan or paid quota, so review your current Apify limits before
running live imports. No Apify account is needed to load the bundled demo data,
although analyzing that demo still requires a Groq key.

## 2. Set up the project

Python 3.12 or newer is recommended. Clone or download the repository, open a
terminal in its root directory, and follow the commands for your system.

### Windows / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

## 3. Configure the environment

Open the new `.env` file and add your keys:

```dotenv
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
GROQ_API_KEY=your-groq-api-key
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
APIFY_API_TOKEN=your-apify-api-token
```

`REVIEWINSIGHT_GROQ_MODEL` is optional. If it is not set, the application uses
`llama-3.3-70b-versatile`. Values already defined in your shell or system
environment take precedence over values in `.env`.

Keep `.env` local. Never commit API keys or place them in source code,
screenshots, browser fields, or logs.

## 4. Run the application

### Recommended: run everything together

Windows / PowerShell:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

macOS / Linux:

```bash
.venv/bin/python run_app.py
```

The launcher starts FastAPI, waits for it to become healthy, starts Streamlit,
and automatically opens the dashboard after both services are ready. Press
`Ctrl+C` in the launcher terminal to stop both services.

- Dashboard: <http://127.0.0.1:8501>
- FastAPI documentation: <http://127.0.0.1:8000/docs>

### Run the services individually

Start the backend first, then start the dashboard in a second terminal. The
underlying commands are `python -m uvicorn backend.app.main:app` and
`python -m streamlit run dashboard/streamlit_app.py`; use the interpreter for
your virtual environment as shown below.

Windows / PowerShell — terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Windows / PowerShell — terminal 2:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

macOS / Linux — terminal 1:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

macOS / Linux — terminal 2:

```bash
.venv/bin/python -m streamlit run dashboard/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

## Project structure

```text
backend/app/       FastAPI routes, imports, collection, analysis, and storage
dashboard/         Streamlit interface and backend API client
demo_data/         Bundled fictional reviews for a repeatable demo
tests/             Fixture-backed automated tests
docs/              Detailed architecture, source, and project-status notes
run_app.py         Recommended launcher for the complete local application
requirements.txt   Python dependencies
```

The backend owns provider credentials, Groq calls, and SQLite data. The
dashboard communicates with it through the local FastAPI API and never asks the
user to enter credentials in the interface.

## Future work

Possible next steps include:

- Docker packaging and cloud deployment.
- Authentication and multi-user workspaces.
- More review sources and replaceable import adapters.
- Background imports with progress and retry controls.
- History search, export, deletion, backup, and retention settings.
- Better provider quota visibility, observability, and automated live checks.

## Tests

Tests use fixtures and fakes, so they do not spend Apify or Groq quota.

Windows / PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

macOS / Linux:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q backend dashboard tests run_app.py
```

## More documentation

- [Architecture and data flow](docs/architecture.md)
- [Current status, limitations, and provider operations](docs/project_status.md)
- [Demo and evaluated review sources](docs/demo_sources.md)
