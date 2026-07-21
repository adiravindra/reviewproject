# Analysis UI and Demo Workflow Design

## Goal

Make the analysis screen easier to scan and understand, style every sentiment
state consistently, and make the bundled demo complete reliably from supervised
startup through saved report rendering.

## Confirmed root cause

Both local services start and communicate correctly: FastAPI becomes healthy
before Streamlit starts, `GET /api/demo` returns the ten bundled reviews, and the
dashboard successfully submits those reviews to `POST /api/analyze`.

The failure occurs at Groq's structured-output boundary. A demo theme can
reasonably combine positive and negative evidence, so the model returns
`"sentiment": "mixed"`. `Theme.sentiment` currently accepts only `positive`,
`neutral`, or `negative`. Groq enforces that schema before returning the tool
call and rejects the generated response with `tool_use_failed`. The analyzer
maps that provider exception to `analysis_failed`, and FastAPI returns the
observed HTTP 502.

## Chosen approach

Treat mixed theme sentiment as a valid first-class state. Keep the strict
structured-output contract, but let themes use the same four-state vocabulary
as overall sentiment: positive, neutral, negative, and mixed. This preserves the
model's evidence-based distinction instead of incorrectly relabeling mixed
feedback as neutral, and it avoids an extra paid retry that could fail in the
same way.

The existing FastAPI, Streamlit, Groq, history, and supervisor boundaries remain
in place. The fix is focused on their contracts, failure classification, and
presentation rather than introducing a new service or frontend framework.

## Analysis contract and error handling

- `Theme.sentiment` accepts positive, neutral, negative, or mixed.
- The system prompt explicitly describes mixed as appropriate only when one
  theme contains meaningful positive and negative evidence.
- Review-level sentiments remain limited to positive, neutral, and negative so
  deterministic metrics continue to have stable buckets.
- Model output still requires exactly one sentiment for every submitted review
  ID and rejects missing, duplicate, or invented IDs.
- Provider request failures remain sanitized at the public API boundary. The
  dashboard receives an application-owned error code and actionable message,
  never raw provider output, credentials, headers, tracebacks, or request data.
- The dashboard differentiates transient provider failure from malformed model
  output and preserves the collected demo evidence so analysis can be retried.
- The supervisor continues to enforce backend readiness before dashboard
  startup and cleans up either service if its peer exits.

## Analysis screen information architecture

The report uses a clear top-to-bottom scan order:

1. Source header with demo provenance and overall sentiment.
2. Four compact metric cards for review count, average rating, positive share,
   and overall sentiment.
3. Executive summary with a strong section label and readable line length.
4. Customer signals containing sentiment and rating charts in equal cards.
5. Recurring themes in a responsive card grid.
6. Strengths, concerns, and recommended actions in parallel insight panels.
7. Supporting review evidence in one collapsed section.

Section headings use one consistent eyebrow-and-title treatment with supporting
copy only when it improves comprehension. Related content is grouped inside
subtle bordered surfaces, and vertical spacing distinguishes major sections
from items within a section.

## Visual system

- Use a white and cool-slate foundation, navy headings, and restrained royal
  blue for primary actions and informational emphasis.
- Positive uses green, neutral uses amber, negative uses red, and mixed uses
  indigo. Every state uses the same badge, border, tint, icon, heading, and body
  structure; color is never the only signal.
- Strengths, concerns, and recommendations use the same panel anatomy and list
  spacing. Recommendations remain informational blue rather than borrowing a
  sentiment color.
- Use a single spacing scale for report sections, grids, cards, headings, and
  list items. Remove oversized gaps and align adjacent cards to shared edges.
- Keep headings concise and specific: `Executive summary`, `Customer signals`,
  `Recurring themes`, `Strengths`, `Concerns`, `Recommended actions`, and
  `Supporting review evidence`.
- Keep paragraph width and line height readable, use stronger text contrast for
  metadata, and prevent review tables from dominating the completed report.
- Escape every source- or model-supplied value before inserting it into HTML.

## Responsive behavior

- Desktop uses four metric columns, two chart columns, three theme columns, and
  three aligned insight panels.
- Tablet uses two metric columns, two theme columns, stacked charts when space
  becomes constrained, and wrapped actions.
- Mobile uses two compact metric columns where legible, otherwise one column;
  themes and insight panels stack; section padding tightens; buttons span the
  available width; and the sidebar collapses automatically.
- No viewport may introduce clipped headings, horizontal page scrolling,
  overlapping badges, unreadable chart labels, or truncated action text.

## Testing strategy

### Automated regression coverage

- Prove a theme with `mixed` sentiment validates while review sentiments remain
  restricted to their three deterministic categories.
- Prove the analyzer accepts a complete structured response containing a mixed
  theme and still rejects malformed output and review-ID mismatches.
- Prove provider and malformed-output failures map to distinct safe API and
  dashboard messages without leaking raw exception content.
- Prove positive, neutral, negative, and mixed theme cards share the same markup
  structure and semantic tokens.
- Prove report section order, headings, responsive breakpoints, panel structure,
  and escaped content through retained Streamlit runtime tests.
- Keep supervisor readiness, cleanup, history, collection, and documentation
  coverage passing.

### Chrome end-to-end verification

From a clean `run_app.py` launch:

1. Confirm FastAPI and Streamlit health endpoints are ready and the page is not
   blank or showing a framework overlay.
2. Select **Use bundled demo data** and verify visible demo provenance plus ten
   review rows.
3. Select **Analyze with Groq** and verify a complete report replaces the
   pre-analysis workspace without an HTTP 502.
4. Confirm the report contains metrics, summary, charts, themes, all three
   insight panels, and collapsed supporting evidence.
5. Refresh history and reopen the saved report.
6. Inspect desktop and mobile viewports for spacing, hierarchy, clipping, and
   consistent sentiment styling.
7. Confirm the Chrome console has no relevant application errors or warnings.

## Acceptance criteria

- The bundled demo completes end to end with the configured Groq credential.
- A mixed theme no longer causes provider schema rejection or HTTP 502.
- Required services start in order, remain supervised, and communicate through
  the documented local endpoints.
- The report has clear section hierarchy, consistent spacing, readable copy,
  and consistent semantic styling across sentiment states.
- Automated tests and compilation pass, and the final desktop/mobile Chrome
  workflow passes with screenshot, DOM, interaction, and console evidence.
