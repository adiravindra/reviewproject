# ReviewInsight

ReviewInsight is a beginner-friendly Customer Review Intelligence Dashboard. The goal is to analyze customer reviews and show useful business signals such as sentiment, topic, urgency, and a short summary.

This version is a working skeleton. It includes a FastAPI backend and a Streamlit dashboard with placeholder analysis logic. Real machine learning will be added later.

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

## Run FastAPI

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

## Run Streamlit

```powershell
streamlit run dashboard\streamlit_app.py
```

## Current Project Status

- Project structure exists.
- Dependencies are listed in `requirements.txt`.
- FastAPI has `/health` and `/analyze` endpoints.
- Streamlit has a simple dashboard with review input, placeholder analysis, and a sample chart.
- Real ML models are not connected yet.
