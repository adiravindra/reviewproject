# ReviewInsight High-Level Architecture

ReviewInsight is a customer review intelligence dashboard. It accepts customer review text from Streamlit or direct API calls, runs rule-based analysis in FastAPI, stores saved analysis runs in SQLite, and renders saved or selected runs in dashboard pages.

The current project is an MVP. Sentiment, topic, urgency, keyword, insight, and summary logic are deterministic and rule-based. No ML model, GenAI model, LangChain, Ollama, Hugging Face pipeline, or external API is active in the analysis flow.

## Architecture Diagram

```text
Review Input
  |-- typed review
  |-- JSON batch
  |-- CSV upload
        |
        v
Streamlit Dashboard
  |-- Home/Add Reviews
  |-- History
  |-- analysis pages
        |
        v
FastAPI Backend
  |-- /analysis/single
  |-- /analysis/batch
  |-- /analysis/csv
  |-- /analysis/runs
  |-- /analysis/latest
        |
        v
Rule-Based Services
  |-- processing
  |-- sentiment
  |-- keywords/topics
  |-- urgency
  |-- summaries
  |-- insights
        |
        v
SQLite History
  |-- analysis_runs metadata
  |-- full analysis JSON payload
        |
        v
Dashboard Views
  |-- overview
  |-- review details
  |-- sentiment
  |-- topics
  |-- urgency
  |-- summaries
```

## Main Components

### Review Input

Review text currently enters the system through:

- Typed single review input in Streamlit.
- API-style JSON payload input in Streamlit.
- CSV upload in Streamlit.
- Direct FastAPI requests.

Typed review input uses `/analysis/single`. JSON batches use `/analysis/batch`. CSV uploads use `/analysis/csv`.

### Streamlit UI

The Streamlit dashboard lives in `dashboard/`.

- `streamlit_app.py` is the Home/Add Reviews page.
- `api_client.py` is the only place that should call FastAPI routes.
- `ui.py` contains shared layout and rendering helpers.
- `pages/` contains Overview, Review Details, Sentiment, Topics, Urgency, Summaries, and History.

Home/Add Reviews can run a typed single-review analysis with or without saving. Batch and CSV workflows always save completed runs. History lists saved SQLite runs and can load a selected run into session state for the other dashboard pages.

### FastAPI Backend

The FastAPI app is created in `backend/app/main.py` and includes:

- `backend/app/routers/health.py`
- `backend/app/routers/reviews.py`

The main analysis workflow routes are:

- `POST /analysis/single`
- `POST /analysis/batch`
- `POST /analysis/csv`
- `GET /analysis/runs`
- `GET /analysis/runs/{run_id}`
- `GET /analysis/runs/{run_id}/reviews/{review_index}`
- `GET /analysis/latest`

Utility routes still exist for lower-level rule-based outputs:

- `POST /sentiment`
- `POST /keywords`
- `POST /summarize`
- `POST /insights`

The older duplicate workflow routes are no longer registered:

- `POST /api/analyze/single`
- `POST /analysis/review`
- `POST /analysis/reviews`
- `POST /analyze`
- `POST /reviews`
- `POST /reviews/batch`
- `GET /history`
- `GET /dashboard/metrics`

### Rule-Based Services

The backend service layer lives in `backend/app/services/`.

- `processing.py` normalizes whitespace, removes empty reviews, and deduplicates reviews case-insensitively.
- `sentiment.py` classifies sentiment with fixed positive and negative word sets.
- `keywords.py` extracts keywords, themes, and common complaints with token counts and fixed vocabularies.
- `summarization.py` returns deterministic summaries.
- `insights.py` combines sentiment, themes, complaints, summaries, and suggested action items.
- `analysis.py` orchestrates full analysis runs, single-review structured analysis, CSV parsing, topic detection, urgency scoring, metrics, and most-urgent review selection.
- `db.py` owns SQLite path resolution, connection creation, and table initialization.
- `history.py` persists and loads saved analysis runs through SQLite.

### SQLite Storage

Saved analysis runs are stored in SQLite at:

```text
data/reviewinsight.db
```

The path can be overridden with:

```text
REVIEWINSIGHT_DB_PATH
```

The database is created automatically when missing. The `analysis_runs` table stores:

- `id`
- `created_at`
- `input_type`
- `review_count`
- `sentiment_counts_json`
- `topic_counts_json`
- `urgency_counts_json`
- `average_urgency`
- `overall_summary`
- `payload_json`

For the MVP, the detailed `AnalysisRunResponse` is stored as JSON text in `payload_json`.

## Current Data Flow

```text
Typed review
  -> Streamlit checkbox chooses save_to_history
  -> POST /analysis/single
  -> FastAPI cleans and analyzes one review
  -> if save_to_history is false, returns single-review result only
  -> if save_to_history is true, saves a SQLite run and returns run_id plus run payload

JSON batch
  -> Streamlit parses review texts
  -> POST /analysis/batch
  -> FastAPI analyzes the batch
  -> SQLite stores the completed run
  -> Streamlit loads the returned run into dashboard session state

CSV upload
  -> Streamlit uploads file
  -> POST /analysis/csv
  -> FastAPI extracts review text from a review/text/comment/feedback column or first column
  -> SQLite stores the completed run
  -> Streamlit loads the returned run into dashboard session state

Dashboard
  -> pages read selected run from session state
  -> if no run is selected, pages try GET /analysis/latest

History
  -> GET /analysis/runs lists saved runs
  -> GET /analysis/runs/{run_id} loads the selected saved run
```

## Current Status

Completed:

- FastAPI app and routers.
- Standardized analysis workflow routes.
- SQLite-backed history storage.
- Rule-based single, batch, and CSV analysis.
- Streamlit Home/Add Reviews workflow.
- Streamlit dashboard pages for loaded or latest saved runs.
- History page with saved-run loading.
- Unit tests for routes, SQLite save/load/list behavior, dashboard client calls, UI helpers, scripts, and Streamlit import context.

Remaining:

- Real ML or GenAI models are not connected.
- CSV upload has no column preview or metadata mapping UI.
- Saved runs cannot be deleted, renamed, filtered, or exported.
- There are no browser-level Streamlit UI tests.
- There is no database migration system because the SQLite schema is still MVP-sized.
