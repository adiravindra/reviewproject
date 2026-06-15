# ReviewInsight Frontend Design

This document describes the Streamlit frontend for ReviewInsight. The UI is an analysis workspace that maps to the FastAPI routes instead of a single prompt-style page.

## Frontend Goals

- Give each major backend capability its own Streamlit page.
- Make the app feel like a review analysis dashboard, not a generic text prompt.
- Keep placeholder sections visible for planned features such as CSV upload, model confidence, topic modeling, and richer trends.
- Keep FastAPI as the source of analysis logic. Streamlit should collect inputs, call the API, and render results.

## App Structure

```text
dashboard/
  streamlit_app.py              # Home / start analysis page
  api_client.py                 # Shared FastAPI client helpers
  ui.py                         # Shared Streamlit rendering helpers
  pages/
    1_Sentiment_Analysis.py
    2_Topic_Category_Analysis.py
    3_Urgency_Priority.py
    4_GenAI_Summary_Insights.py
    5_Overall_Dashboard.py
    6_History.py
    7_API_Health.py
```

## Page Map

| Streamlit page | FastAPI route | Purpose |
| --- | --- | --- |
| Home / Start Analysis | `/analysis/review`, `/analysis/csv`, `/analysis/reviews`, `/dashboard/metrics`, `/health` | Start analysis from pasted text, CSV upload, API-style JSON, or future input placeholders. |
| Sentiment Analysis | `/analysis/review` | Analyze one review and show sentiment in the full saved analysis result. |
| Topic / Category Analysis | `/analysis/reviews` | Extract review-level topics and top topic counts from multiple reviews. |
| Urgency / Priority Analysis | `/analysis/reviews` | Show low, medium, and high priority breakdowns and a priority worklist. |
| GenAI Summary / Insights | `/analysis/reviews` | Show deterministic MVP summaries with placeholders for future GenAI controls. |
| Overall Dashboard | `/dashboard/metrics` | Show saved-history rollups for sentiment, urgency, topics, and summaries. |
| History | `/history` | Show past review analysis runs saved by the backend. |
| API Health | `/health` | Show backend status, project name, and version for development checks. |

## Shared Sidebar

Every page should include a sidebar control for the FastAPI backend URL. The default value is:

```text
http://127.0.0.1:8000
```

This keeps local development simple while allowing the user to point Streamlit at a different backend later.

## Page Details

### Home / Start Analysis

The home page introduces ReviewInsight as a Customer Review Intelligence Dashboard and provides the primary input workflow. It shows:

- Backend connection status from `/health`
- Saved analysis KPI cards from `/dashboard/metrics`
- Tabs for typed reviews, CSV upload, API-style JSON payloads, and future input methods
- The latest analysis result with metrics, charts, summary, and review table

### Sentiment Analysis

The sentiment page supports:

- A single review text area
- A call to `/analysis/review`
- Saved result metrics, charts, summary, and analyzed review details

### Topic / Category Analysis

The topic page supports:

- Batch review input with one review per line
- A call to `/analysis/reviews`
- Topic bar chart, topic table, review-level categories, and extracted keywords

### Urgency / Priority Analysis

The urgency page supports:

- Batch review input with one review per line
- A call to `/analysis/reviews`
- Low, medium, and high priority metrics
- A priority queue chart and review worklist

### GenAI Summary / Insights

The summary page supports:

- Batch review input with one review per line
- A call to `/analysis/reviews`
- Summary result panel
- Placeholder controls for future summary length and audience

### Overall Dashboard

The dashboard page supports:

- A call to `/dashboard/metrics`
- History-level KPIs
- Sentiment, urgency, and topic charts
- Recent saved summaries

### History

The history page supports:

- A call to `/history`
- A table of saved runs with source, review count, sentiment, priority, and summary

### API Health

The health page should support:

- A call to `/health`
- Status, project, and version display
- A clear error message if the backend is not reachable

## Error Handling

The Streamlit frontend should show friendly errors when:

- The user submits empty review input
- FastAPI is not running
- The backend returns an error response
- The backend returns invalid JSON

## Implementation Notes

- Keep API calls in `dashboard/api_client.py`.
- Keep reusable UI helpers in `dashboard/ui.py`.
- Keep page files focused on page layout and rendering.
- Use FastAPI as the source of analysis logic.
- Keep placeholders visually present but clearly tied to future project phases.
