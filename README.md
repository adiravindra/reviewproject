# ReviewInsight

ReviewInsight is a small customer-review analysis app. It lets a user paste one review, sends it to a FastAPI backend, analyzes it with Hugging Face models, saves the result to SQLite, and displays a polished Streamlit dashboard with summary and sentiment insights.

## What It Does

- Analyzes one pasted customer review at a time.
- Generates a model-based review summary.
- Classifies sentiment with a model and shows confidence when available.
- Highlights positive, neutral, and negative keywords in the review text.
- Saves each analysis to local SQLite history.
- Provides a History page for previously analyzed reviews.

The app is model-first. Rule-based logic is used only as a fallback when a model cannot load, cannot run inference, or returns an invalid result.

## Models

- Summary model: `google/flan-t5-small`
  - Loaded with `AutoTokenizer` and `AutoModelForSeq2SeqLM`.
  - Prompted to generate a short business-owner-friendly customer review analysis.
  - Override with `REVIEWINSIGHT_SUMMARY_MODEL` if you want another compatible seq2seq model.

- Sentiment model: `distilbert/distilbert-base-uncased-finetuned-sst-2-english`
  - Loaded through the Transformers `sentiment-analysis` pipeline.
  - Produces positive/negative sentiment with a confidence score.

Transformers downloads model files automatically if they are not already cached. Set `REVIEWINSIGHT_MODEL_LOCAL_ONLY=1` only when you want Transformers to use locally cached model files without downloading.

## Project Structure

```text
backend/
  app/
    main.py                 FastAPI app setup
    routers/reviews.py      API routes
    services/analysis.py    Review analysis orchestration
    services/model_*.py     Hugging Face model wrappers
    services/history.py     SQLite history persistence
dashboard/
  streamlit_app.py          Main Analysis page
  pages/1_History.py        History page
  ui.py                     Shared Streamlit UI and styling
scripts/
  run_app.py                Starts backend and frontend together
```

For detailed system diagrams, see [docs/architecture.md](docs/architecture.md).

## API Routes

### `POST /analysis/single`

Analyzes one review and saves the result to history.

Request body:

```json
{
  "text": "The product is easy to use, but shipping was slow."
}
```

Response includes the cleaned review text, sentiment, sentiment score, summary, model source metadata, fallback reason if one was needed, and saved history status.

### `GET /analysis/history`

Returns saved review analyses from SQLite.

Optional query parameter:

- `limit`: number of history items to return, from `1` to `200`. Default is `50`.

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

## Run The App

Start FastAPI and Streamlit together:

```powershell
python scripts\run_app.py
```

Then open:

```text
http://127.0.0.1:8501
```

The runner warms the summary and sentiment models before starting the app. If warmup fails, the app still starts; each API request tries the models again and falls back only if the model path fails.

Press `Ctrl+C` in the terminal to stop both services.

## Run Manually

Start the backend:

```powershell
uvicorn backend.app.main:app --reload
```

In a second terminal, start the frontend:

```powershell
streamlit run dashboard\streamlit_app.py
```

Open:

```text
http://localhost:8501
```

Manual API examples:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/single -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow."}'
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/history
```

## Configuration

Optional environment variables:

```powershell
$env:REVIEWINSIGHT_SUMMARY_MODEL = "google/flan-t5-base"
$env:REVIEWINSIGHT_MODEL_LOCAL_ONLY = "1"
$env:REVIEWINSIGHT_DB_PATH = "data/reviewinsight.db"
```

The default SQLite database is `data/reviewinsight.db`.
