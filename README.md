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
- FastAPI routes for single-review analysis and history.
- One helper script for starting the app.

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

The Hugging Face summary path is enabled by default. To use only the fast rule-based fallback summary, set this before starting the app:

```powershell
$env:REVIEWINSIGHT_ENABLE_MODEL_SUMMARY = "0"
```

The default model is `sshleifer/distilbart-cnn-12-6`, a distilled BART summarizer. The app will download it through Transformers if it is not already cached. To force offline-only model loading, set:

```powershell
$env:REVIEWINSIGHT_MODEL_LOCAL_ONLY = "1"
```

## Run App

This is the easiest way to start both FastAPI and Streamlit:

```powershell
python scripts\run_app.py
```

Then open:

```text
http://127.0.0.1:8501
```

Press `Ctrl+C` in the terminal to stop both services.

## Run Backend Manually

```powershell
uvicorn backend.app.main:app --reload
```

Analyze one review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/single -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow."}'
```

Fetch history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/history
```

## Run Frontend Manually

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
