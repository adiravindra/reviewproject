# ReviewInsight Project Status

## Simplified Scope

ReviewInsight is an MVP customer review analysis dashboard. It analyzes one pasted review at a time, saves the result to SQLite, and shows saved review history.

The goal is clarity over breadth. The project no longer supports CSV uploads, batch analysis, charts, trends, or multi-page dashboards.

## Current Features

- FastAPI backend with:
  - `POST /analysis/single`
  - `GET /analysis/history`
- Streamlit frontend with two pages:
  - Analysis
  - History
- Analysis output tabs:
  - Sentiment
  - Topics / Categories
  - Urgency
  - Summary
  - Raw Result / Debug Info
- SQLite history at `data/reviewinsight.db` by default.
- Rule-based sentiment, topics, and urgency.
- Hugging Face summary attempt with rule-based fallback.
- One app runner script at `scripts/run_app.py`.

## How To Run The App

```powershell
python scripts\run_app.py
```

Then open `http://127.0.0.1:8501`.

## How To Run Backend Manually

```powershell
uvicorn backend.app.main:app --reload
```

## How To Run Frontend Manually

```powershell
streamlit run dashboard\streamlit_app.py
```

## What Was Removed

- CSV upload.
- API payload and batch analysis flows.
- Overview, Review Details, Sentiment, Topics, Urgency, and Summaries dashboard pages.
- Charting and trend views.
- Advanced history filtering and run-detail exploration.
- Extra helper scripts.
- Batch insights and keyword-dashboard helper modules.
- Unneeded dependencies for pandas, Plotly, matplotlib, scikit-learn, and multipart uploads.

## Current Data Flow

1. User opens the Analysis page.
2. User pastes one review.
3. Streamlit sends `POST /analysis/single`.
4. FastAPI analyzes the review and saves it to SQLite.
5. Streamlit displays the result in tabs.
6. User opens the History page.
7. Streamlit calls `GET /analysis/history` and displays saved reviews.

## Notes

The model summary path is enabled by default with `sshleifer/distilbart-cnn-12-6`, a distilled BART summarizer. Set `REVIEWINSIGHT_ENABLE_MODEL_SUMMARY=0` before starting the app to use only the fast rule-based fallback summary, or `REVIEWINSIGHT_MODEL_LOCAL_ONLY=1` to prevent model downloads. If Transformers or the model cannot load, the backend returns the rule-based summary and includes fallback metadata in the raw result.
