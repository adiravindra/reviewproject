# ReviewInsight

ReviewInsight is a beginner-friendly Customer Review Intelligence Dashboard. The goal is to analyze customer reviews and show useful business signals such as sentiment, topic, urgency, priority, and a short summary.

This version includes a FastAPI backend, local JSON analysis history, and a Streamlit dashboard that calls the backend for analysis flows. Real machine learning and GenAI models can replace the current rule-based services later.

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
- Local JSON history storage
- Optional SQLite later

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

Analyze a review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analyze -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow."}'
```

Analyze and save a review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/review -ContentType "application/json" -Body '{"text":"The product is easy to use, but shipping was slow.","source":"manual"}'
```

View saved analysis history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/history
```

## Run Streamlit Manually

```powershell
streamlit run dashboard\streamlit_app.py
```

## Current Project Status

- Project structure exists.
- Dependencies are listed in `requirements.txt`.
- FastAPI has `/health`, legacy `/analyze`, full analysis, CSV upload, history, and dashboard metrics endpoints.
- Streamlit has a product-style analysis homepage plus sentiment, topic, urgency, summary, overall dashboard, history, and API health pages.
- Analysis history is stored locally in `data/review_history.json`, which is ignored by git.
- Real ML models are not connected yet.
