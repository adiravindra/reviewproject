# ReviewInsight High-Level Architecture

ReviewInsight is a Customer Review Intelligence Dashboard. It will take review data from a user interface, API request, uploaded file, or sample dataset, then process the text and return useful business insights such as sentiment, topic, urgency, and summaries.

The current project is a working skeleton. The FastAPI backend and Streamlit dashboard are in place with placeholder analysis logic. The data processing, machine learning, GenAI, and storage layers are planned next steps.

## Architecture Diagram

```text
┌────────────────────────────┐
│     Review Data Input      │
│  CSV Upload / API / Sample │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│        Streamlit UI        │
│ Upload reviews, view charts│
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│      FastAPI Backend       │
│ API routes + orchestration │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│   Data Processing Layer    │
│ Clean, validate, deduplicate│
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────────────────────┐
│            ML / GenAI Pipeline             │
│                                            │
│  Sentiment Classifier                      │
│  Topic / Category Detector                 │
│  Urgency / Priority Scorer                 │
│  GenAI Summary Generator                   │
└──────────────┬─────────────────────────────┘
               │
               ▼
┌────────────────────────────┐
│       Storage Layer        │
│ SQLite / CSV / JSON outputs│
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│    Dashboard & Insights    │
│ Sentiment charts, topics,  │
│ trends, summaries, examples│
└────────────────────────────┘
```

## Main Components

### 1. Review Data Input

This is where review text enters the system.

Planned input options:

- Manual text entry from the Streamlit dashboard
- CSV upload with many customer reviews
- API request to the FastAPI backend
- Sample review data for demos and testing

Current status:

- Manual single-review input exists in the Streamlit dashboard.
- The backend accepts review text through the `/analyze` API route.
- CSV upload and sample datasets are planned for a future version.

### 2. Streamlit UI

The Streamlit dashboard is the user-facing part of the project. It should make the review analysis easy to test and explain.

Responsibilities:

- Accept customer review input
- Later, support CSV uploads
- Send review text to the backend or run placeholder display logic
- Show sentiment, topic, urgency, and summary
- Display charts and simple business insights

Current file:

- `dashboard/streamlit_app.py`

Current status:

- Shows the title `ReviewInsight Dashboard`
- Provides a customer review text area
- Provides an `Analyze Review` button
- Displays placeholder sentiment, topic, urgency, and summary
- Displays a sample Plotly chart

### 3. FastAPI Backend

The FastAPI backend is the API layer for ReviewInsight. It receives review data, coordinates analysis, and returns structured results.

Responsibilities:

- Provide API routes for health checks and review analysis
- Validate incoming request data
- Call future processing and ML functions
- Return consistent JSON responses to the frontend

Current file:

- `backend/app/main.py`

Current routes:

- `GET /health`
- `POST /analyze`

Current `/health` response:

```json
{
  "status": "ok",
  "project": "ReviewInsight"
}
```

Current `/analyze` response fields:

- `sentiment`
- `topic`
- `urgency`
- `summary`

Current status:

- The route exists and returns placeholder values.
- No real ML model is connected yet.

### 4. Data Processing Layer

The data processing layer will prepare raw review text before it reaches the ML or GenAI pipeline.

Planned responsibilities:

- Remove empty reviews
- Trim extra whitespace
- Normalize text where useful
- Validate required fields
- Deduplicate repeated reviews
- Prepare batches of reviews from CSV uploads

Example processing steps:

1. Receive raw review text.
2. Check that the text is not empty.
3. Clean extra spaces and line breaks.
4. Remove duplicate rows if analyzing a CSV file.
5. Pass cleaned review data to the ML pipeline.

Current status:

- Basic whitespace trimming exists in the `/analyze` route.
- A separate processing module has not been added yet.

### 5. ML / GenAI Pipeline

This layer will eventually produce the core intelligence in ReviewInsight.

Planned modules:

- Sentiment Classifier
- Topic / Category Detector
- Urgency / Priority Scorer
- GenAI Summary Generator

Planned responsibilities:

- Classify reviews as positive, neutral, or negative
- Detect common topics such as shipping, product quality, price, support, or usability
- Score urgency based on complaint severity or business importance
- Generate short summaries for individual reviews or groups of reviews

Possible tools:

- Hugging Face Transformers for sentiment or summarization
- scikit-learn for simple topic or category models
- pandas for batch analysis
- PyTorch as the deep learning backend

Current status:

- No real ML or GenAI model is active yet.
- The API and dashboard return placeholder values so the application flow can be tested first.

### 6. Storage Layer

The storage layer will keep input reviews and analysis results.

Possible storage options:

- SQLite database for local structured storage
- CSV files for exports
- JSON files for API-style output or saved analysis results

Planned stored fields:

- Review text
- Sentiment
- Topic
- Urgency
- Summary
- Created timestamp
- Source, such as manual input, CSV upload, or API

Current status:

- Storage is not implemented yet.
- The app currently returns analysis results directly without saving them.

### 7. Dashboard & Insights

This is the final output layer where users understand the review data.

Planned insights:

- Sentiment distribution chart
- Topic/category counts
- Urgency breakdown
- Review trends over time
- Example positive and negative reviews
- Short summaries of customer pain points

Current status:

- A sample sentiment chart exists in Streamlit.
- Real dashboard insights will be added after the ML and storage layers are built.

## Current Request Flow

The current single-review flow works like this:

1. A user enters review text in the Streamlit dashboard.
2. The dashboard displays placeholder analysis results.
3. The FastAPI backend can also receive review text through `POST /analyze`.
4. The backend returns placeholder sentiment, topic, urgency, and summary.

The future flow will connect Streamlit to FastAPI directly, then FastAPI will call the processing and ML layers before returning results.

## Planned Future Flow

```text
User enters or uploads reviews
        │
        ▼
Streamlit sends data to FastAPI
        │
        ▼
FastAPI validates request
        │
        ▼
Data processing cleans and prepares reviews
        │
        ▼
ML / GenAI pipeline analyzes reviews
        │
        ▼
Results are saved to SQLite, CSV, or JSON
        │
        ▼
Streamlit displays charts and insights
```

## Project Status

Completed:

- Basic project structure
- FastAPI app skeleton
- `/health` route
- `/analyze` route with placeholder response
- Streamlit dashboard skeleton
- Manual review text input
- Placeholder analysis output
- Sample Plotly chart

Planned next steps:

- Connect Streamlit to the FastAPI `/analyze` endpoint
- Add CSV upload support
- Move text cleaning into a separate processing module
- Add real sentiment classification
- Add topic/category detection
- Add urgency scoring
- Add optional SQLite storage
- Build richer dashboard charts and filters
