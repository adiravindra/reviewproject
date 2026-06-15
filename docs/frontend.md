# ReviewInsight Frontend Design

This document describes the Streamlit frontend for ReviewInsight. The UI is an analysis workspace that maps to the FastAPI routes instead of a single prompt-style page.

## Frontend Goals

- Give each major backend capability its own Streamlit page.
- Make the app feel like a review analysis dashboard, not a generic text prompt.
- Keep Home/Add Reviews as the only review input surface.
- Keep FastAPI as the source of analysis logic. Streamlit should collect inputs, call the API, and render results.
- Let the other pages explore the loaded analysis from Streamlit session state or backend history.

## App Structure

```text
dashboard/
  streamlit_app.py              # Home / start analysis page
  api_client.py                 # Shared FastAPI client helpers
  ui.py                         # Shared Streamlit rendering helpers
  pages/
    1_Overview.py
    2_Review_Details.py
    3_Sentiment.py
    4_Topics.py
    5_Urgency.py
    6_Summaries.py
    7_History.py
```

## Page Map

| Streamlit page | FastAPI route | Purpose |
| --- | --- | --- |
| Home / Start Analysis | `/analysis/review`, `/analysis/csv`, `/analysis/reviews`, `/dashboard/metrics`, `/health` | Start analysis from pasted text, CSV upload, API-style JSON, or future input placeholders. |
| Overview | Session state, `/analysis/latest` fallback | Show loaded-run KPIs, charts, topics, and summary. |
| Review Details | Session state, `/analysis/latest` fallback, `/analysis/runs/{run_id}/reviews/{review_index}` API support | Inspect one analyzed review from the loaded run. |
| Sentiment | Session state, `/analysis/latest` fallback | Show loaded-run sentiment counts, distribution, and review-level sentiment. |
| Topics | Session state, `/analysis/latest` fallback | Show loaded-run top topics and review-level categories. |
| Urgency | Session state, `/analysis/latest` fallback | Show loaded-run urgency counts, average urgency, and most urgent reviews. |
| Summaries | Session state, `/analysis/latest` fallback | Show loaded-run overall and per-review summaries. |
| History | `/history` | Show past review analysis runs saved by the backend. |

## Shared Navigation

Every page should render the shared top navigation bar and hide Streamlit's default sidebar navigation. Home and History expose a collapsible backend URL control. The default value is:

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
- Loaded analysis saved in Streamlit session state and backend JSON history

### Overview

The overview page supports:

- Empty state when no reviews are loaded or saved
- Loaded-run KPIs for total reviews, sentiment, urgency, and priority
- Sentiment and urgency charts
- Top topic and summary sections

### Review Details

The review details page supports:

- Empty state when no reviews are loaded or saved
- A selector for one loaded review
- Sentiment, topic, urgency, score, full text, summary, and keywords

### Sentiment

The sentiment page supports:

- Empty state when no reviews are loaded or saved
- Positive, neutral, and negative counts
- Sentiment distribution chart
- Review-level sentiment table

### Topics

The topic page supports:

- Empty state when no reviews are loaded or saved
- Top topic chart and table
- Review-level topics and keywords

### Urgency

The urgency page supports:

- Empty state when no reviews are loaded or saved
- Low, medium, and high priority metrics
- Average urgency
- Priority chart and most urgent reviews

### Summaries

The summary page supports:

- Empty state when no reviews are loaded or saved
- Loaded-run summary
- Per-review summaries
- Placeholders for future GenAI controls

### History

The history page supports:

- A call to `/history`
- A table of saved runs with source, review count, sentiment, priority, and summary

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
