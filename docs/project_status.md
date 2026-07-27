# Project Status

**Date:** July 23, 2026
**Status:** Amazon and Google Maps review imports use fixture-tested Apify adapters with shared limits; optional manual live provider smoke verification still requires explicit user approval.

## Current feature inventory

- `GET /api/import/options` supplies provider-neutral labels and shared 10/20/50/100 limits. The dashboard uses one **Source URL** field. Amazon imports use `automation-lab/amazon-reviews-scraper` through the existing replaceable adapter boundary. Amazon requests helpful reviews without a sentiment filter; Google Maps requests most-relevant reviews without a rating filter. Mixed fixture coverage proves 5-, 3-, and 1-star reviews remain in provider order.
- The sole import credential is backend `APIFY_API_TOKEN`; it is read only on a cache miss or explicit refresh. The app needs no Amazon or Google account credentials, cookies, browser state, or session tokens.
- Google input sets `personalData: false`; Automation Lab may return public reviewer fields transiently, so the adapter discards identities, profiles, media, variations, helpful-vote data, provider IDs, and raw responses.
- Normalized evidence is isolated in `data/review_import_cache.db` for 30 days. Explicit **Refresh from source** is the only cache bypass.
- Imports have no application-side follow-up pagination, background work, polling, schedules, webhooks, or automatic retries. One miss/refresh makes at most one provider request. No Actor copy, task, schedule, webhook, build, custom configuration, or Actor ID environment variable is required.
- Apify provider-side retention remains an operator concern; version one does not automatically delete Actor runs or datasets.
- All automated verification is fixture-only: saved provider fixture files and fake HTTP sessions cover automated import tests, so they spend no provider or Groq quota. Live provider smoke verification still requires explicit user approval.
- All imported evidence remains visible up to 100 reviews. Groq analyzes only the first 40 in provider order; larger reports disclose `40 of N reviews analyzed`, while source provenance retains the actual imported count.

- `run_app.py` remains the only supported complete-application launcher. It loads the repository-root `.env` without overriding existing shell or system values, starts FastAPI on `127.0.0.1:8000`, and launches Streamlit on `127.0.0.1:8501` only after the backend is healthy.
- One shared 30-second deadline begins when FastAPI launches and remains active through Streamlit startup without resetting. The browser opens only after FastAPI `GET /health` returns HTTP 200 with exactly `{"status":"ok"}` and the subsequently launched Streamlit `GET /_stcore/health` returns HTTP 200. Timeout or child exit returns a failure and cleans up whichever children were started.
- The UI accepts a public review-page URL in a bordered extraction workspace, calls `POST /api/collect`, and displays a grouped source summary and normalized evidence before analysis. Collection is static HTTP only and prefers JSON-LD before conservative HTML review cards.
- `GET /api/demo` loads the ten-review bundled local dataset only after the user selects **Use bundled demo data**. Demo provenance is visible with `🧪 DEMO DATA`; failed live extraction never activates that dataset.
- `POST /api/analyze` accepts the already displayed source and review evidence, validates `GROQ_API_KEY`, uses the Llama Versatile Groq configuration, validates structured insights, and computes metrics in Python. Theme-level insights permit positive, neutral, negative, or mixed sentiment, while individual review classifications remain three-state.
- The source summary and review table remain visible throughout the pre-analysis stage. Once a report exists, that workspace is replaced by the evidence-first report hierarchy: source and sentiment hero, four metrics, executive summary, **Customer signals**, **Recurring themes**, **Customer priorities**, and the source/review evidence retained only in the collapsed **Supporting review evidence** expander. Positive, negative, neutral, mixed, and action treatments share one card anatomy and paired text/icon cues.
- Responsive behavior keeps desktop actions and report groups side by side where space permits, then stacks actions, charts, themes, and insight panels at narrower widths while retaining a compact two-column metric grid on mobile.
- Successful reports are written atomically to local SQLite at `data/review_history.db`. `GET /api/history` returns newest-first summaries, and `GET /api/history/{run_id}` restores one saved report.
- The backend exposes safe actionable errors for invalid URLs, blocked sites, timeouts, malformed structured review data, missing reviews, missing or invalid Groq configuration, unavailable Groq validation, model-output parsing, and history failures. Recoverable analysis errors explicitly tell the user that the collected reviews remain available for another attempt.
- Credentials, headers, raw AI responses, upstream response bodies, internal exceptions, and tracebacks do not cross the FastAPI boundary.

## Provider operations and responsible use

Live imports require one Apify account and a backend-only Apify API token in
`APIFY_API_TOKEN`. The application does not require Amazon or Google account
credentials, browser cookies or session tokens. No Actor copy, task, schedule,
build, webhook, custom Actor configuration, or Actor ID environment variable is
required.

- Amazon uses the public
  [`automation-lab/amazon-reviews-scraper`](https://apify.com/automation-lab/amazon-reviews-scraper)
  Actor with `sort: "helpful"` and no star-rating filter.
- Google Maps uses the public
  [`compass/google-maps-reviews-scraper`](https://apify.com/compass/google-maps-reviews-scraper)
  Actor with `reviewsSort: "mostRelevant"` and no rating filter.
- Both sources support 10, 20, 50, or 100 imported reviews. The dashboard keeps
  all imported evidence visible and sends only the first 40 reviews to Groq;
  larger reports disclose `40 of N reviews analyzed`.
- Normalized imports are cached for 30 days. **Refresh from source** is the only
  action that deliberately bypasses a live cache entry and can spend provider
  quota again.

Automation Lab's Free-plan Console pricing observed on July 23, 2026 was
`$0.01` per run start plus `$2.00 per 1,000` reviews. Approximate maximum event
costs for 10, 20, 50, and 100 reviews were `$0.03`, `$0.05`, `$0.11`, and
`$0.21`. These values are planning estimates, not billing guarantees; provider
pricing and availability can change. Operators should check current Actor
availability, billing, and spending limits before a manual live request.

Both Actors are unofficial scraping services. Their availability does not grant
users permission to copy, analyze, retain, redistribute, or commercialize
source content. Operators remain responsible for confirming their use is
permitted and should review the
[Amazon Conditions of Use](https://www.amazon.com/gp/help/customer/display.html?nodeId=GLSBYFE9MGKKQXXM)
and
[Google Maps Additional Terms](https://maps.google.com/help/terms_maps/?refresh=1).

Review Intelligence discards provider reviewer identities, profiles, avatars,
media, helpful-vote data, owner responses, provider IDs, and raw response
bodies. Review text can still contain personal information and is sent to Groq
only after explicit analysis. Apify provider-side retention can apply to Actor
runs and datasets; version one does not delete those automatically. Historical
reports labeled `Apify (Axesso)` or `Outscraper` remain readable with their
original provenance, but neither is an active setup provider.

## Runtime and configuration

The active non-secret settings are:

```dotenv
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
GROQ_API_KEY=
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
APIFY_API_TOKEN=
```

`GROQ_API_KEY` is required only when analysis begins. It is never entered through the UI. The model override is optional; the default remains `llama-3.3-70b-versatile`.

## Automated coverage

Focused tests cover:

- strict collection, analysis, source, demo, and history contracts;
- Groq key trimming, validation status mapping, structured-output validation, and response sanitization;
- static collection safety, redirects, limits, JSON-LD priority, HTML fallback, and specific failure codes;
- SQLite first-use schema creation, atomic save, newest-first summaries, round trips, and safe failures;
- staged API routes, safe error envelopes, dashboard HTTP boundaries, accessible presentation helpers, and history navigation;
- supervisor dotenv precedence, exact FastAPI readiness, independent dual-service readiness order, the shared startup deadline, one-shot browser behavior, child lifecycle, and cleanup;
- redesigned dashboard source structure, responsive CSS contracts, and retained Streamlit runtime coverage for visible pre-analysis evidence, collapsed post-analysis evidence, report order, and chart payloads; and
- current-facing documentation/source audits for retired configuration or model-choice language.

Run the full local checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

## Automated verification record

On July 23, 2026, the complete fixture/fake-backed unittest discovery command passed **196/196 tests**, and `compileall -q backend dashboard tests run_app.py` exited with status 0. The automated suite itself does not contact a live review source or Groq; the separate installed-Chrome record below covers the provider-backed bundled demo.

## Installed-Google-Chrome verification

On July 21, 2026, the supported `run_app.py` launcher started FastAPI first, observed its exact health response, and then started Streamlit successfully. In installed Google Chrome, the explicit bundled demo loaded all 10 reviews, provider-backed Groq analysis completed, the mixed report was saved, and history restored the report. The report was inspected at the normal desktop width and at a true 430-by-900 viewport; the narrow layout stacked charts and insight panels without horizontal overflow. A final fresh Chrome run completed with no warning or error console entries.

The reproduced 502 root cause was a contract mismatch: Groq correctly produced `mixed` for a recurring theme with both favorable and unfavorable evidence, while the theme schema accepted only the three individual-review states. The schema and prompt now distinguish those two contracts. The previous non-fatal Vega extent warnings were removed by giving both charts explicit data-derived numeric domains.

This pass intentionally covered the bundled demo workflow requested for this branch. Live third-party extraction and provider-independent invalid-source cases remain covered by fixtures and should be re-smoked when choosing a specific external source for a presentation.

## Known limitations

- Static HTML collection cannot support pages that require client-side rendering, login, pagination, or access-control circumvention.
- External page markup can change; only URLs verified with the completed collector are suitable for a live presentation.
- Groq access, quotas, model availability, and later generative request success remain external service concerns even after pre-analysis validation succeeds.
- Bundled demo collection avoids a live source-page request, but **Analyze with Groq** still requires a valid configured credential, provider/network access, and available quota.
- SQLite history is intentionally local to this machine and has no multi-user synchronization or backup layer.
- Automated tests use fixtures and fakes; live sources and real model calls require the separate local smoke check.
