# Reliable Launch and Analysis UI Design

## Goal

Make Review Intelligence reliably runnable from `run_app.py` and redesign the
analysis experience so a user can move from review extraction to a readable,
professional report without restarting either process.

## Root cause

`run_app.py` starts FastAPI and Streamlit together, but its browser-open gate
checks only Streamlit's `/_stcore/health` endpoint. Streamlit can become ready
before FastAPI has bound port 8000 and completed application startup. A user can
therefore see the dashboard and select **Extract reviews** while the backend is
still unavailable.

The extraction handler immediately calls `check_health()`. When that first
probe loses the startup race, `_unavailable()` tells the user to start or
restart the complete application even though the supervisor is already
starting it correctly. The same incomplete readiness gate can expose a stale
dashboard during a port collision until the failed child is noticed.

## Chosen approach

Keep the existing FastAPI, Streamlit, and supervisor boundaries. Strengthen the
supervisor so the application is considered ready only when both child
services answer their health endpoints, and apply a focused Streamlit
information-design refactor to the extraction and report views.

This avoids two larger alternatives:

- Importing backend services directly into Streamlit would remove the startup
  race but break the tested HTTP boundary and couple UI reruns to backend state.
- Replacing Streamlit with a separate React application would provide more
  layout control but add a build pipeline and duplicate a working client layer.

## Runtime architecture

`run_app.py` remains the only supported launcher.

1. Load the repository-root `.env` without overriding inherited values.
2. Start FastAPI and Streamlit with the current Python interpreter.
3. Poll both `http://127.0.0.1:8000/health` and
   `http://127.0.0.1:8501/_stcore/health`.
4. Open the dashboard only after both probes return their expected successful
   responses.
5. If either child exits, stop its peer and return a nonzero status.
6. If both children remain alive but do not become ready within 30 seconds,
   print one actionable startup message, stop both children, and return a
   nonzero status.

The two health probes remain independently injectable so supervisor tests can
model every readiness order without starting real servers.

## Dashboard information architecture

### Workspace header

Use a compact eyebrow, title, and one-sentence description. Keep the URL form
inside a bordered workspace panel with a clear primary action. Place the demo
action beside, or directly below, the primary action depending on available
width. Explain the staged workflow with three concise steps: extract, review,
analyze.

### Evidence stage

After collection, show one source card containing the source title, URL,
extractor, and review count. Keep the evidence table visible before analysis,
but place it in a clearly titled section with supporting copy. The analysis
button belongs directly after this section.

### Report stage

The post-analysis report uses this scan order:

1. Report heading with source context and an overall-sentiment badge.
2. Four equal metric cards: reviews analyzed, average rating, positive share,
   and overall sentiment.
3. A full-width executive summary panel.
4. A two-column distribution section for sentiment and ratings.
5. A responsive grid of recurring-theme cards.
6. Three parallel insight panels: strengths, concerns, and recommended
   actions.
7. Supporting review evidence in a collapsed expander so it remains available
   without duplicating a large table in the primary report flow.

### History

Keep history in the sidebar but improve its hierarchy and readability. Format
timestamps without raw timezone/microsecond noise, keep demo provenance
visible, and use a compact selected-report control with one clear load action.

## Visual system

- Use a neutral white and cool-slate foundation with navy headings and a
  restrained blue action color.
- Positive uses green, neutral uses amber, negative uses red, and mixed uses
  indigo. Each state must include text and an icon so color is never the only
  cue.
- Use one spacing scale across panels, cards, headings, and lists.
- Use subtle borders and shadows to group information rather than heavy
  saturated backgrounds.
- Keep body text at a readable line length and strengthen heading size,
  weight, and vertical rhythm.
- On narrower viewports, metric and insight columns wrap, charts stack, action
  buttons become full width, and the main container uses reduced padding.

All model- and source-supplied text interpolated into HTML must be escaped.

## Error handling

The root fix is the supervisor's combined readiness gate. Dashboard transport
errors remain a defense-in-depth path for a backend that later stops, but the
copy must distinguish an unavailable backend from ordinary collection errors
and must not expose exception details, credentials, headers, or upstream
response bodies.

Live collection errors continue to preserve the submitted URL and never switch
to demo data automatically. Analysis errors continue to preserve the extracted
evidence so the user can retry.

## Testing

### Automated

- Add supervisor tests proving that neither backend-only nor dashboard-only
  readiness opens the browser.
- Add a supervisor test proving the browser opens exactly once after both
  services become ready in either order.
- Add a timeout test proving startup failure stops both children and prints the
  safe readiness message.
- Keep current child-exit, cleanup, dotenv, and browser-open failure coverage.
- Add dashboard formatting tests for the report header, metric cards, theme
  cards, insight panels, semantic colors, responsive CSS, readable history
  labels, and collapsed supporting evidence.
- Run the complete unittest and compileall suites.

### Google Chrome

From a clean supervised launch:

1. Confirm Chrome does not receive the page until both services are healthy.
2. Extract the verified live source at
   `https://web-scraping.dev/product/1`.
3. Confirm five reviews and JSON-LD provenance appear before analysis.
4. Run Groq analysis and confirm the complete report renders and is saved.
5. Refresh history and reload the saved report.
6. Exercise invalid URL and no-review error states without a restart prompt.
7. Exercise bundled demo extraction and analysis with visible demo provenance.
8. Inspect desktop and narrow responsive layouts.
9. Confirm the Chrome console contains no application errors.

