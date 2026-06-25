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

## How To Run Backend

```powershell
uvicorn backend.app.main:app --reload
```

## How To Run Frontend

```powershell
streamlit run dashboard\streamlit_app.py
```

## What Was Removed

- CSV upload.
- API payload and batch analysis flows.
- Overview, Review Details, Sentiment, Topics, Urgency, and Summaries dashboard pages.
- Charting and trend views.
- Advanced history filtering and run-detail exploration.
- Helper scripts.
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

The model summary path is intentionally simple. If Transformers or the local model cannot load, the backend returns the rule-based summary and includes fallback metadata in the raw result.
