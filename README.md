# ReviewInsight

ReviewInsight is a beginner-friendly Customer Review Intelligence Dashboard. The goal is to analyze customer reviews and show useful business signals such as sentiment, topic, urgency, priority, and a short summary.

This version includes a FastAPI backend, SQLite analysis history, and a Streamlit dashboard that calls the backend for analysis flows. Real machine learning and GenAI models can replace the current rule-based services later.

## Tech Stack

- Python 3.12
- FastAPI
- Streamlit
- Hugging Face Transformers
- scikit-learn
- pandas
- Plotly
- matplotlib
- PyTorch
- SQLite history storage

## Windows PowerShell Setup

From the project folder:

```powershell
cd C:\Users\adith\Desktop\Work\reviewproject
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Verify imports:

```powershell
python -c "import fastapi, streamlit, pandas, sklearn, transformers, torch, plotly, matplotlib; print('All imports worked')"
```

## Helper Scripts

The project includes cross-platform Python scripts that work on Windows, macOS, and Linux as long as you run them from the project folder with the virtual environment active.

Run the full app, including FastAPI and Streamlit:

```powershell
python -m scripts.run_app
```

Then open:

```text
http://127.0.0.1:8501
```

Run tests and Python compile checks:

```powershell
python -m scripts.run_tests
```

Run a smoke test that starts FastAPI and Streamlit, checks both health endpoints, then stops them:

```powershell
python -m scripts.smoke
```

Optional custom ports:

```powershell
python -m scripts.run_app --backend-port 8010 --streamlit-port 8510
python -m scripts.smoke --backend-port 8010 --streamlit-port 8510
```

## Run FastAPI Manually

```powershell
uvicorn backend.app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Analyze one review without saving it:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/single -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow."}'
```

Analyze and save a review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/single -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow.","save_to_history":true}'
```

Analyze and save a JSON batch:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/batch -ContentType "application/json" -Body '{"reviews":[{"text":"Support was fast."},{"text":"Shipping was slow."}]}'
```

View saved analysis history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/runs
```

## Run Streamlit Manually

```powershell
streamlit run dashboard\streamlit_app.py
```

## Current Project Status

- Project structure exists.
- Dependencies are listed in `requirements.txt`.
- FastAPI uses `/analysis/single`, `/analysis/batch`, `/analysis/csv`, `/analysis/runs`, `/analysis/runs/{run_id}`, `/analysis/runs/{run_id}/reviews/{review_index}`, and `/analysis/latest` as the main workflow.
- Streamlit has a product-style Home/Add Reviews input page plus top-nav Overview, Review Details, Sentiment, Topics, Urgency, Summaries, and History pages that explore the loaded analysis.
- Analysis history is stored locally in SQLite at `data/reviewinsight.db` by default. Override it with `REVIEWINSIGHT_DB_PATH`.
- Real ML models are not connected yet.
