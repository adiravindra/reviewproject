# Single Review Analysis Design

## Goal

Add a first-version backend service that analyzes one customer review and returns a frontend-ready structured result without saving an analysis run to history.

## Scope

The new endpoint is `POST /api/analyze/single`. It accepts JSON with a required `text` field and returns:

- `text`: the cleaned original review text
- `sentiment`: `positive`, `neutral`, or `negative`
- `topics`: zero or more detected categories from the requested topic taxonomy
- `urgency_score`: a float from `0` to `1`
- `urgency_label`: `low`, `medium`, or `high`
- `summary`: a short one-sentence summary

Empty or whitespace-only input returns a 422 response with a clear validation message.

## Architecture

The implementation will keep route handling thin. A focused rule-based service will own the single-review analysis logic and expose an `analyze_single_review_text(text: str)` function returning a typed result. The FastAPI route will validate input through the existing review-cleaning helper path, call the service, and serialize the response through Pydantic schemas.

The Streamlit home page will call the new route for typed/pasted review analysis and render the returned single-review result in a clean card layout. Existing saved analysis routes remain unchanged for CSV, API payloads, history, and dashboard pages.

## Rules

Sentiment starts from the existing rule-based sentiment service. Topic detection uses explicit keyword sets for:

- pricing
- bugs/crashes
- performance
- UI/UX
- login/auth
- support
- feature request

Urgency increases for crashes, login failures, payment issues, lost data, broken features, and urgent wording. The first version uses additive keyword signals capped at `1.0`, then maps scores below `0.34` to `low`, scores below `0.67` to `medium`, and higher scores to `high`.

## Testing

Tests will cover the service and route behavior first, including:

- a high-urgency negative review with crash/login/payment terms
- a positive low-urgency review
- empty input returning 422
- the dashboard API client posting to `/api/analyze/single`
- a UI helper producing card fields from the backend result

## Replacement Path

The service boundary should make future ML replacement straightforward: the route and frontend can keep the same response contract while the internal scoring, topic classification, and summary generation are replaced later.
