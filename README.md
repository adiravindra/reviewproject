# ReviewInsight

ReviewInsight is now a small MVP for analyzing one customer review at a time.

The app has a FastAPI backend, a Streamlit frontend, and local SQLite history. The backend uses Hugging Face models for summary and sentiment with rule-based fallbacks, plus rule-based topic and urgency logic.

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

The Hugging Face summary path is enabled by default with `Falconsai/text_summarization`. This model is loaded directly with `AutoTokenizer` and `AutoModelForSeq2SeqLM` because Transformers v5 no longer supports the `summarization` pipeline task. To use only the rule-based summary fallback, set this before starting the app:

```powershell
$env:REVIEWINSIGHT_ENABLE_MODEL_SUMMARY = "0"
```

The Hugging Face sentiment path is also enabled by default. To use only the rule-based sentiment fallback, set:

```powershell
$env:REVIEWINSIGHT_ENABLE_MODEL_SENTIMENT = "0"
```

The default sentiment model is `distilbert-base-uncased-finetuned-sst-2-english`, loaded with the supported `sentiment-analysis` Transformers task. The app will download models through Transformers if they are not already cached. To force offline-only model loading, set:

```powershell
$env:REVIEWINSIGHT_MODEL_LOCAL_ONLY = "1"
```

## Run App

This is the easiest way to start both FastAPI and Streamlit:

```powershell
python scripts\run_app.py
```

The runner checks the summary and sentiment models before starting the backend and frontend. If a model is not cached yet, Transformers downloads it during this startup check so the first dashboard analysis request does not spend that time loading the model.

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
