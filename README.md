# ReviewInsight

ReviewInsight is now a small MVP for analyzing one customer review at a time.

The app has a FastAPI backend, a Streamlit frontend, and local SQLite history. The backend uses simple rule-based sentiment, topic, and urgency logic. It also tries the existing Hugging Face summary path and falls back to a rule-based summary if the model is unavailable or fails.

## Included Features

- Analysis page for one pasted review.
- One `Analyze Review` button.
- Results shown in tabs:
  - Sentiment
  - Topics / Categories
  - Urgency
  - Summary
  - Raw Result / Debug Info
- History page showing saved SQLite review analyses.
- FastAPI routes for health, single-review analysis, and history.

## Intentionally Removed

- CSV upload.
- Batch analysis.
- Multi-page dashboards.
- Trends, charts, metrics dashboards, and advanced analytics.
- Advanced filtering and saved-run exploration.
- Test files, pytest-style setup, smoke scripts, and test helper scripts.
- Unused helper modules for batch insights and keyword dashboards.

## Install

From the project folder:

```powershell
cd C:\Users\adith\Desktop\Work\reviewproject
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Optional import check:

```powershell
python -c "import fastapi, streamlit, requests, transformers, torch; print('imports ok')"
```

## Run Backend

```powershell
uvicorn backend.app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Analyze one review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/single -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow."}'
```

Fetch history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/history
```

## Run Frontend

In a second terminal:

```powershell
streamlit run dashboard\streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## SQLite

The default SQLite database is `data/reviewinsight.db`. Set `REVIEWINSIGHT_DB_PATH` to use a different file.
