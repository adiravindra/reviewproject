# ReviewInsight Frontend Design

This document describes the Streamlit frontend for ReviewInsight. The UI is an analysis workspace that uses the standardized FastAPI analysis workflow and SQLite-backed saved runs.

## Frontend Goals

- Keep FastAPI as the source of analysis logic.
- Keep Home/Add Reviews as the only review input surface.
- Use `/analysis/single` for typed reviews, with optional history saving.
- Use `/analysis/batch` for API-style JSON review batches.
- Use `/analysis/csv` for CSV uploads.
- Let dashboard pages explore a selected analysis run from Streamlit session state or fall back to `/analysis/latest`.
- Let History list SQLite saved runs from `/analysis/runs` and load one selected run into the workspace.

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
| Home / Start Analysis | `/health`, `/analysis/runs`, `/analysis/single`, `/analysis/batch`, `/analysis/csv` | Start analysis from pasted text, CSV upload, API-style JSON, or future input placeholders. |
| Overview | Session state, `/analysis/latest` fallback | Show loaded-run KPIs, charts, topics, and summary. |
| Review Details | Session state, `/analysis/latest` fallback | Inspect one analyzed review from the loaded run. |
| Sentiment | Session state, `/analysis/latest` fallback | Show loaded-run sentiment counts, distribution, and review-level sentiment. |
| Topics | Session state, `/analysis/latest` fallback | Show loaded-run top topics and review-level categories. |
| Urgency | Session state, `/analysis/latest` fallback | Show loaded-run urgency counts, average urgency, and most urgent reviews. |
| Summaries | Session state, `/analysis/latest` fallback | Show loaded-run overall and per-review summaries. |
| History | `/analysis/runs`, `/analysis/runs/{run_id}` | Show SQLite saved runs and load one selected run into the workspace. |

## Shared Navigation

Every page renders the shared top navigation bar and hides Streamlit's default sidebar navigation. Home and History expose a collapsible backend URL control. The default value is:

```text
http://127.0.0.1:8000
```

## Current Workflow

```text
Typed review -> /analysis/single -> optional SQLite history
JSON batch -> /analysis/batch -> saved SQLite run
CSV upload -> /analysis/csv -> saved SQLite run
Dashboard pages -> selected run in session state or /analysis/latest
History -> /analysis/runs -> optional load from /analysis/runs/{run_id}
```

## Page Details

### Home / Start Analysis

The home page shows backend status, saved-run counts, and tabs for the available input workflows.

- The typed review tab calls `/analysis/single`.
- A "Save this analysis to history" checkbox controls the `save_to_history` request field.
- Unsaved typed results render as a single-review card only.
- Saved typed results also place the returned analysis run into the dashboard workspace.
- CSV uploads call `/analysis/csv`, save a run, and place it into the workspace.
- API-style JSON payloads call `/analysis/batch`, save a run, and place it into the workspace.

### Dashboard Pages

Overview, Review Details, Sentiment, Topics, Urgency, and Summaries read the loaded analysis from `st.session_state["latest_analysis"]`. If no run is loaded, `workspace_analysis()` tries `/analysis/latest`.

### History

The History page calls `/analysis/runs` to list saved SQLite runs. The user can select one saved run, load it through `/analysis/runs/{run_id}`, and then explore that run from the other dashboard pages.

## Error Handling

The Streamlit frontend shows friendly errors when:

- The user submits empty review input.
- FastAPI is not running.
- The backend returns an error response.
- The backend returns invalid JSON.

## Implementation Notes

- Keep API calls in `dashboard/api_client.py`.
- Keep reusable UI helpers in `dashboard/ui.py`.
- Keep page files focused on page layout and rendering.
- Keep placeholders visually present but tied to future project phases.
