# ReviewInsight Project Status

## 1. Project Overview

ReviewInsight is a Python customer review intelligence dashboard. The implemented app accepts customer review text, runs rule-based analysis, stores saved runs in SQLite, and displays results through a Streamlit dashboard backed by FastAPI.

The current app is an MVP. It can clean review text, classify simple sentiment, detect keywords and topics, estimate urgency, generate deterministic summaries, save analysis runs to SQLite, list saved runs, load saved runs, and render dashboard views for a selected or latest run.

No real machine learning, transformer, GenAI, LangChain, Ollama, Hugging Face pipeline, or external API model is currently connected to the analysis flow.

## 2. Current Architecture

### Backend

- `backend/app/main.py` creates the FastAPI app and includes routers.
- `backend/app/routers/health.py` defines `GET /health`.
- `backend/app/routers/reviews.py` defines analysis workflow routes plus utility analysis routes.
- `backend/app/schemas/reviews.py` defines Pydantic request and response models.
- `backend/app/services/processing.py` cleans and deduplicates review text.
- `backend/app/services/sentiment.py` contains rule-based sentiment scoring.
- `backend/app/services/keywords.py` contains keyword, theme, and complaint extraction.
- `backend/app/services/summarization.py` contains deterministic summaries.
- `backend/app/services/insights.py` combines rule-based business insights.
- `backend/app/services/analysis.py` orchestrates review analysis, CSV parsing, urgency, topics, and metrics.
- `backend/app/services/db.py` creates SQLite connections and initializes the database table.
- `backend/app/services/history.py` saves and loads analysis runs from SQLite.

### Frontend

- `dashboard/streamlit_app.py` is the Home/Add Reviews page.
- `dashboard/api_client.py` contains FastAPI HTTP helpers.
- `dashboard/ui.py` contains shared Streamlit rendering and state helpers.
- `dashboard/pages/1_Overview.py` through `dashboard/pages/6_Summaries.py` render the selected or latest analysis run.
- `dashboard/pages/7_History.py` lists SQLite saved runs and can load one into the dashboard workspace.

### FastAPI And Streamlit Connection

Streamlit calls FastAPI through `dashboard/api_client.py`. The default backend URL is `http://127.0.0.1:8000`.

The main workflow is:

```text
Typed review -> /analysis/single -> optional SQLite history
JSON batch -> /analysis/batch -> saved SQLite run
CSV upload -> /analysis/csv -> saved SQLite run
Dashboard -> selected/latest analysis run
History -> /analysis/runs -> SQLite saved runs
```

## 3. Implemented Features

### Main Workflow Routes

- `POST /analysis/single`
- `POST /analysis/batch`
- `POST /analysis/csv`
- `GET /analysis/runs`
- `GET /analysis/runs/{run_id}`
- `GET /analysis/runs/{run_id}/reviews/{review_index}`
- `GET /analysis/latest`

### Utility Routes

- `GET /health`
- `POST /sentiment`
- `POST /keywords`
- `POST /summarize`
- `POST /insights`

### Removed Duplicate Workflow Routes

These old overlapping routes are no longer registered:

- `POST /api/analyze/single`
- `POST /analysis/review`
- `POST /analysis/reviews`
- `POST /analyze`
- `POST /reviews`
- `POST /reviews/batch`
- `GET /history`
- `GET /dashboard/metrics`

### Analysis Features

- Sentiment is rule-based and uses fixed positive/negative word sets.
- Topic and theme detection is rule-based.
- Urgency is rule-based.
- Summaries are deterministic placeholder-style summaries.
- Batch metrics include sentiment breakdown, urgency breakdown, top topics, average urgency, and high-priority review count.
- CSV parsing reads UTF-8 CSV files and uses a known review column name or the first column.
- SQLite stores saved run metadata plus the full analysis JSON payload.

## 4. Data Flow

### Typed Review

1. User enters one review in Streamlit.
2. User optionally checks "Save this analysis to history".
3. Streamlit sends `POST /analysis/single` with `text` and `save_to_history`.
4. FastAPI cleans and analyzes the review.
5. If not saved, FastAPI returns the single-review result.
6. If saved, FastAPI stores a SQLite analysis run and returns the single-review result with `run_id` and `run`.
7. Streamlit renders the single-review card and, when saved, loads the run into the dashboard workspace.

### JSON Batch

1. User pastes API-style JSON in Streamlit.
2. Streamlit parses review text and sends `POST /analysis/batch`.
3. FastAPI analyzes the batch, saves it to SQLite, and returns the full run.
4. Streamlit stores the returned run in session state for dashboard pages.

### CSV Upload

1. User uploads a CSV in Streamlit.
2. Streamlit sends `POST /analysis/csv`.
3. FastAPI extracts review text, analyzes the reviews, saves the run to SQLite, and returns the full run.
4. Streamlit stores the returned run in session state for dashboard pages.

### History And Dashboard

1. History calls `GET /analysis/runs`.
2. User can select a run.
3. Streamlit loads it through `GET /analysis/runs/{run_id}`.
4. Dashboard pages use the selected run from session state or fall back to `GET /analysis/latest`.

## 5. Models / Services

- `SingleReviewAnalysisRequest` accepts `text` and `save_to_history`.
- `SingleReviewAnalysisResponse` returns single-review fields plus `saved_to_history`, optional `run_id`, and optional saved `run`.
- `ReviewBatchAnalysisRequest` accepts a list of reviews for `/analysis/batch`.
- `AnalysisRunResponse` is the saved run payload for batch, CSV, and saved single-review analysis.
- `HistoryResponse` lists saved SQLite run metadata.
- `ReviewDetailResponse` returns one review result from a saved run.

The service layer remains rule-based. The SQLite layer uses only Python standard library `sqlite3`.

## 6. What Is Working

- Standardized main workflow routes.
- Optional save behavior for typed single-review analysis.
- Saved batch and CSV analysis runs.
- SQLite table creation when the database is missing.
- SQLite save, list, load, latest-run, and review-detail behavior.
- Streamlit Home page calling the new routes.
- Streamlit History page listing and loading saved runs.
- Dashboard pages reading selected/latest runs.
- Tests for new route names, SQLite history behavior, frontend client route calls, single review with and without saving, batch saves, CSV saves, scripts, UI helpers, and Streamlit import context.

## 7. What Is Incomplete Or Missing

- No real ML or GenAI model is connected.
- No database migrations exist yet.
- Saved runs cannot be deleted, renamed, searched, filtered, or exported.
- CSV upload has no preview or column-mapping UI.
- Review metadata such as rating, date, product, and customer segment is not stored separately.
- No browser-level tests verify the rendered Streamlit UI.
- Error handling is still basic.
- The older dated Superpowers plan/spec files still document the prior `/api/analyze/single` implementation as historical project artifacts.

## 8. Recommended Next Steps

1. Add CSV preview and column mapping.
2. Add saved-run delete/export actions.
3. Add run filtering and search on the History page.
4. Add browser-level Streamlit checks for the main workflows.
5. Add SQLite migration handling before the schema grows.
6. Improve deterministic summaries before replacing them with ML or GenAI.
7. Decide whether review metadata should become first-class database columns.

## 9. Questions / Decisions Needed

- Should saved runs support deletion and export in the next iteration?
- Which CSV metadata fields should be supported first?
- Should the app keep utility routes such as `/sentiment`, `/keywords`, `/summarize`, and `/insights`, or eventually fold them behind the main analysis workflow only?
- Should the SQLite schema remain JSON-payload-first, or should individual reviews become normalized rows?
