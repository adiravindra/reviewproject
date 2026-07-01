# ReviewInsight

ReviewInsight is a customer-review analysis app. It lets a user paste one review, sends it to a FastAPI backend, analyzes it with Hugging Face models, saves the result to SQLite, and displays a polished Streamlit dashboard with summary and sentiment insights. The backend also has a batch endpoint for product-scale review reports.

## What It Does

- Analyzes one pasted customer review at a time.
- Analyzes many reviews in one batch for product-level reports.
- Generates a model-based review summary.
- Classifies sentiment with a model and shows confidence when available.
- Aggregates overall sentiment, common issues, praised features, recurring complaints, and main like/dislike reasons for batch workloads.
- Highlights positive, neutral, and negative keywords in the review text.
- Saves each analysis to local SQLite history.
- Provides a History page for previously analyzed reviews.

The app is model-first. Rule-based logic is used only as a fallback when a model cannot load, cannot run inference, or returns an invalid result.

## Models

- Summary model: `Qwen/Qwen2.5-1.5B-Instruct`
  - Loaded locally through Transformers with `AutoTokenizer` and `AutoModelForCausalLM`.
  - Uses GPU automatically when CUDA-enabled PyTorch is installed.
  - Uses fp16 on CUDA by default for this 1.5B model because it fits the tested 4 GB RTX 3050 and is faster than 4-bit quantization.
  - Uses 4-bit bitsandbytes quantization automatically for larger model names such as Qwen 3B, or when `REVIEWINSIGHT_SUMMARY_QUANTIZATION=4bit`.
  - Prompted to generate a polished 2-4 sentence customer-review summary with concrete details, sentiment, supporting points, and the customer's overall takeaway.
  - Override with `REVIEWINSIGHT_SUMMARY_MODEL` if you want another compatible causal/chat model such as `Qwen/Qwen2.5-3B-Instruct` or a compatible seq2seq model such as `google/flan-t5-large`.

- Sentiment model: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - Loaded through the Transformers `sentiment-analysis` pipeline.
  - Produces positive, neutral, or negative sentiment with a confidence score.
  - Override with `REVIEWINSIGHT_SENTIMENT_MODEL` if you want another compatible text-classification model.

Transformers downloads model files automatically if they are not already cached. Set `REVIEWINSIGHT_MODEL_LOCAL_ONLY=1` only when you want Transformers to use locally cached model files without downloading.

On a CPU-only Torch install, local Qwen generation can still take tens of seconds per summary. On this machine, Qwen 3B on CPU measured about 57 seconds cold and 23 seconds warm for one short review. CUDA PyTorch plus Qwen 1.5B fp16 on the RTX 3050 measured about 3.9 seconds warm for the same short review. Install CUDA PyTorch for GPU inference:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
.\.venv\Scripts\python.exe -m pip install --upgrade transformers accelerate bitsandbytes
```

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

### `POST /analysis/batch`

Analyzes many reviews in one request and returns a product-level report.

Request body:

```json
{
  "texts": [
    "The battery lasts all day and setup was simple.",
    "The case cracked after a week and support was slow."
  ]
}
```

Response includes review count, overall sentiment, sentiment counts, one model-generated report summary, common issues, praised features, recurring complaints, main like/dislike reasons, and per-review sentiment details.

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
$env:REVIEWINSIGHT_SUMMARY_MODEL = "google/flan-t5-large"
$env:REVIEWINSIGHT_SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
$env:REVIEWINSIGHT_INFERENCE_DEVICE = "auto"
$env:REVIEWINSIGHT_SUMMARY_QUANTIZATION = "auto"
$env:REVIEWINSIGHT_SENTIMENT_BATCH_SIZE = "16"
$env:REVIEWINSIGHT_SUMMARY_MAX_NEW_TOKENS = "120"
$env:REVIEWINSIGHT_MODEL_LOCAL_ONLY = "1"
$env:REVIEWINSIGHT_DB_PATH = "data/reviewinsight.db"
```

The default SQLite database is `data/reviewinsight.db`.
