# Groq Mixed Sentiment and History Sidebar Design

## Problem

A Google Maps analysis can fail with HTTP 502 when Groq assigns `mixed` to an
individual review. The provider rejects the generated `AgentInsights` tool call
because `ReviewSentiment.sentiment` currently permits only `positive`,
`neutral`, and `negative`. The dashboard also configures Streamlit's sidebar
with automatic initial visibility, so the History panel can start collapsed.

## Approved design

- Treat `mixed` as a valid individual-review sentiment throughout the public
  schema, deterministic metrics, and dashboard visualization.
- Keep the existing positive-percentage calculation: only positive reviews
  count toward the numerator, while all analyzed reviews remain in the
  denominator.
- Preserve the existing evidence-only Groq prompt and update it to explicitly
  allow `mixed` for an individual review containing meaningful positive and
  negative evidence.
- Start Streamlit with the sidebar expanded.
- Load saved history automatically on the first dashboard run, while retaining
  the manual refresh and selected-report controls.
- Preserve safe API errors and never expose provider responses or credentials.

## Verification

- Add regression tests proving that `mixed` validates and is counted.
- Add dashboard tests proving that mixed sentiment is displayed and that page
  configuration expands the sidebar.
- Run the focused tests, then the complete test suite.
- Start the local app and use Google Chrome to verify the Google Maps import,
  Groq analysis, saved-history refresh, and visible History sidebar.
