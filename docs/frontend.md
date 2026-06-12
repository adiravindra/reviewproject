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
  streamlit_app.py              # Home / overview page
  api_client.py                 # Shared FastAPI client helpers
  ui.py                         # Shared Streamlit rendering helpers
  pages/
    1_Review_Input.py
    2_Sentiment_Analysis.py
    3_Keyword_Themes.py
    4_Summarization.py
    5_Insights_Dashboard.py
    6_API_Health.py
```

## Page Map

| Streamlit page | FastAPI route | Purpose |
| --- | --- | --- |
| Home / Overview | `/health` | Show project overview, backend status, and placeholder analysis KPIs. |
| Review Input | `/reviews`, `/reviews/batch` | Clean and validate single or batch review input. |
| Sentiment Analysis | `/sentiment` | Analyze one review and show sentiment, score, and placeholder confidence. |
| Keyword / Themes | `/keywords` | Extract recurring keywords and business themes from multiple reviews. |
| Summarization | `/summarize` | Summarize one or more reviews. |
| Insights Dashboard | `/insights` | Show overall sentiment, sentiment distribution, themes, complaints, summary, and action items. |
| API Health | `/health` | Show backend status, project name, and version for development checks. |

## Shared Sidebar

Every page should include a sidebar control for the FastAPI backend URL. The default value is:

```text
http://127.0.0.1:8000
```

This keeps local development simple while allowing the user to point Streamlit at a different backend later.

## Page Details

### Home / Overview

The home page should introduce ReviewInsight as a Customer Review Intelligence Dashboard. It should show:

- Backend connection status from `/health`
- Placeholder KPI cards for total reviews, positive sentiment, top theme, and open action items
- A short page guide so users know where to go for each analysis task

### Review Input

The review input page should support:

- A single-review form that calls `/reviews`
- A batch-review form where one review per line calls `/reviews/batch`
- A table of cleaned reviews returned by the backend
- A placeholder CSV upload section marked as a future extension

### Sentiment Analysis

The sentiment page should support:

- A single review text area
- A call to `/sentiment`
- Metrics for sentiment and score
- A placeholder confidence indicator for future ML model output
- A small explanation that the current logic is rule-based

### Keyword / Themes

The keyword page should support:

- Batch review input with one review per line
- A call to `/keywords`
- Keyword frequency table
- Theme frequency table and bar chart
- Placeholder section for future topic modeling

### Summarization

The summarization page should support:

- Batch review input with one review per line
- A call to `/summarize`
- Summary result panel
- Review count metric
- Placeholder controls for future summary length and tone

### Insights Dashboard

The insights page is the main business-analysis view. It should support:

- Batch review input with one review per line
- A call to `/insights`
- Overall sentiment, review count, and action item metrics
- Sentiment distribution chart
- Positive themes
- Negative themes
- Common complaints
- Suggested action items
- Summary panel

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
- Use the existing FastAPI routes; do not add new backend routes for this UI phase.
- Keep placeholders visually present but clearly tied to future project phases.
