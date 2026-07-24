# Generic Import Limits and Apify Amazon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task, with the
> review checkpoints and fixture-only test boundaries below.

**Goal:** Replace the active Outscraper Amazon integration with Axesso Data's
Apify Amazon Reviews Actor, give Amazon and Google Maps the shared limits
`10/20/50/100`, use one generic source URL field, and analyze no more than the
first 40 imported reviews while preserving actual import provenance.

**Architecture:** The existing provider registry and adapter protocol remain the
replacement boundary. A new `ApifyAmazonReviewsAdapter` owns the Axesso request
and response shape; the existing Google adapter changes only its advertised
limits. The import service continues to validate, cache, normalize, and attach
provenance. The dashboard displays up to 100 imported reviews but builds an
analysis request from the first 40. The analysis service accepts the validated
`AnalysisRequest` directly so a source can truthfully say 100 reviews were
retrieved while the report contains the 40-review analyzed subset.

**Tech stack:** Python 3.12, FastAPI, Pydantic v2, requests, SQLite,
Streamlit, unittest, saved JSON fixtures.

**Approved design:** `docs/superpowers/specs/2026-07-23-generic-import-limits-apify-amazon-design.md`

## External setup and live-call boundary

- Live Amazon and Google Maps imports require an **Apify account** and an
  **Apify API token**. The user has said the token was added, but implementation
  and automated verification must not assume or expose its value.
- No Outscraper account, API key, card, or environment variable is needed after
  this milestone.
- Set the token only as backend environment variable `APIFY_API_TOKEN`, normally
  in the repository-root `.env`. No Amazon or Google account credentials,
  cookies, browser state, or session tokens are needed.
- No Actor copy, task, schedule, webhook, build, custom Actor configuration, or
  Actor ID environment variable is required. The application calls public Actor
  IDs `axesso_data~amazon-reviews-scraper` and
  `compass~google-maps-reviews-scraper` directly.
- The Apify Free plan can be used for this proof of concept without adding a
  payment card. No paid plan is required by the application. Before
  intentionally enabling paid usage, the operator should verify current Actor
  pricing and configure the lowest practical Apify platform spending limit.
- Axesso currently advertises `$0.90 / 1,000 reviews`, so maximum uncached
  review-event estimates are `$0.009`, `$0.018`, `$0.045`, and `$0.09` for the
  four limits. Compass has separate Actor pricing. Prices and free credits can
  change and must remain documented as estimates, not guarantees.
- `GROQ_API_KEY` remains required only for the explicit analysis action.
- Automated tests must use saved fixtures, fake HTTP sessions, temporary local
  storage, and mocks. They must not call Apify, Axesso, Compass, Amazon, Google
  Maps, Outscraper, or Groq.
- Do not make an optional live Amazon request during implementation. Before any
  live provider smoke test, stop and confirm the account, token, Actor
  availability, current free/billing/spending settings, and explicit user
  approval.

## Compatibility and scope constraints

- Do not migrate or rewrite history. Existing reports whose provider is
  `Outscraper` must remain readable; new Amazon reports use
  `Apify (Axesso)`.
- Do not migrate the cache. The new Amazon provider key creates an isolated
  cache identity. Old five-review entries become unreachable and can expire.
- Preserve the static collector, bundled demo, insight schema, report layout,
  cache TTL, explicit refresh behavior, and one-save-per-analysis history flow.
- Keep `CollectionResult`'s exact retrieved-count invariant. Only the internal
  analysis service input changes from `CollectionResult` to `AnalysisRequest`.
- Keep the analysis request maximum at 40. Do not add Groq batching, synthesis,
  retries, background jobs, or automatic refresh.
- Continue limiting Amazon URLs to `amazon.com` product paths.
- Do not persist provider response bodies, reviewer names, profile paths,
  images, variations, helpful-vote data, owner responses, or provider IDs.
- The dashboard import client timeout must exceed the Axesso adapter's
  120-second read timeout. This is a necessary compatibility adjustment for the
  new bounded Actor run, not a retry or pagination feature.

---

### Task 1: Expand public import provenance and limits without expanding Groq

**Files:**

- Modify: `backend/app/models.py`
- Modify: `tests/test_import_models.py`
- Modify: `tests/test_demo_data.py`

**Interfaces:**

- `SourceInfo.requested_count`: optional integer `1..100`
- `SourceInfo.retrieved_count`: optional integer `0..100`
- `ImportRequest.limit`: integer `1..100`
- `AnalysisRequest.reviews`: unchanged `2..40`
- Remove the now-inappropriate `AnalysisRequest.to_collection()` helper.

- [ ] **Step 1: Write failing upper-bound and compatibility tests**

Add model tests proving a provider `CollectionResult` with 100 reviews and
`retrieved_count=100` validates, `ImportRequest(limit=100)` validates, and
values above 100 fail. Keep a focused analysis test proving 40 reviews validate
and 41 fail. Replace the demo-contract assertion that calls `to_collection()`
with assertions on `request.source` and `request.reviews`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_models tests.test_demo_data -v
```

Expected: the 100-review provenance/import assertions fail against the current
40-review import bounds.

- [ ] **Step 3: Expand import-only bounds**

Change only the three import provenance/request fields to a maximum of 100.
Leave `AnalysisRequest.reviews` at 40 and leave the strict provider collection
count validator intact. Remove `to_collection()` because deliberate analysis
subsets are not complete import collections.

- [ ] **Step 4: Re-run the focused tests**

Run the Step 2 command.

Expected: all selected tests pass.

- [ ] **Step 5: Commit the contract change**

```powershell
git add backend/app/models.py tests/test_import_models.py tests/test_demo_data.py
git commit -m "feat: allow review imports up to one hundred"
```

---

### Task 2: Add shared limits and reusable Amazon ASIN extraction

**Files:**

- Modify: `backend/app/imports/contracts.py`
- Modify: `backend/app/imports/policies.py`
- Modify: `backend/app/imports/apify.py`
- Modify: `tests/test_import_policy.py`
- Modify: `tests/test_import_service.py`

**Interfaces:**

```python
IMPORT_LIMITS = (10, 20, 50, 100)

def extract_amazon_asin(source_url: str) -> str | None:
    ...
```

- [ ] **Step 1: Write failing shared-limit and ASIN tests**

Assert the constant is exactly `(10, 20, 50, 100)`, the Google adapter exposes
that same tuple, and `extract_amazon_asin()` returns uppercase ASINs for the
three already-supported product paths and `None` for search/wrong paths. Update
the fake service adapter and request helper to use the shared limits with a
default of 20. Assert limit 5 and an arbitrary limit such as 25 are rejected
before adapter or cache work.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_policy tests.test_import_service -v
```

Expected: missing constant/helper assertions or old limit expectations fail.

- [ ] **Step 3: Implement the shared policy**

Define `IMPORT_LIMITS` in the provider-neutral contracts module. Have both
adapters reference the same tuple rather than duplicate it. Extract the
currently embedded Amazon path matching into `extract_amazon_asin()` and have
`validate_import_source()` use it, preserving the current HTTPS and host
allowlist behavior.

- [ ] **Step 4: Re-run focused tests**

Run the Step 2 command.

Expected: all selected tests pass.

- [ ] **Step 5: Commit the shared policy**

```powershell
git add backend/app/imports/contracts.py backend/app/imports/policies.py backend/app/imports/apify.py tests/test_import_policy.py tests/test_import_service.py
git commit -m "refactor: share provider import limits"
```

---

### Task 3: Replace the active Amazon adapter with Axesso on Apify

**Files:**

- Create: `backend/app/imports/apify_amazon.py`
- Modify: `backend/app/imports/normalizer.py`
- Modify: `backend/app/imports/registry.py`
- Delete: `backend/app/imports/outscraper.py`
- Create: `tests/fixtures/apify_axesso_amazon_reviews.json`
- Delete: `tests/fixtures/outscraper_amazon_reviews.json`
- Modify: `tests/test_import_adapters.py`
- Modify: `tests/test_import_normalizer.py`

**Interfaces:**

```python
AXESSO_ACTOR_ID = "axesso_data~amazon-reviews-scraper"
AXESSO_ENDPOINT = (
    "https://api.apify.com/v2/acts/"
    "axesso_data~amazon-reviews-scraper/run-sync-get-dataset-items"
)
AXESSO_TIMEOUT = (5, 120)

class ApifyAmazonReviewsAdapter:
    provider_key = "apify_axesso_amazon"
    provider_label = "Apify (Axesso)"
    platform = "amazon"
    allowed_limits = IMPORT_LIMITS
```

- [ ] **Step 1: Add a sanitized Axesso response fixture**

Use a saved flat dataset-items list containing at least two successful review
rows with representative fields:

```json
{
  "statusCode": 200,
  "statusMessage": "FOUND",
  "asin": "B000000000",
  "productTitle": "Fixture product",
  "title": "Reliable every morning",
  "text": "The controls are simple and the results are consistent.",
  "rating": "5.0 out of 5 stars",
  "date": "Reviewed in the United States on July 20, 2026"
}
```

Include deliberate `userName`, `profilePath`, `imageUrlList`, variation, and
helpful-vote marker values so tests prove they never enter
`ProviderImportResult`.

- [ ] **Step 2: Write failing Axesso request/decoding tests**

For each `(limit, max_pages)` pair `(10,1)`, `(20,2)`, `(50,5)`, `(100,10)`,
assert one POST to `AXESSO_ENDPOINT`, bearer authentication through
`APIFY_API_TOKEN`, timeout `(5, 120)`, and exact payload:

```python
{
    "input": [
        {
            "asin": "B000000000",
            "domainCode": "com",
            "sortBy": "helpful",
            "maxPages": max_pages,
        }
    ]
}
```

Assert the token is not in the URL, the adapter title/source key are taken from
`productTitle`/`asin`, ratings and dates are passed to the shared normalizer,
and every personal/extra fixture marker is absent from `repr(result)`.
Add a normalizer assertion that Axesso's documented
`"5.0 out of 5 stars"` rating becomes integer `5`, while non-integral or
unrecognized ratings remain absent.

Add tests for missing `APIFY_API_TOKEN`, invalid Amazon source shape at the
adapter boundary, malformed non-list/non-object dataset output, JSON decoding
failure, 401/402/429/5xx statuses, timeout, and connection failure. All error
assertions use existing application-owned codes and never raw provider text.

- [ ] **Step 3: Run adapter tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters -v
```

Expected: import failure for the absent Axesso adapter and old Outscraper
expectations.

- [ ] **Step 4: Implement the adapter**

Read only `APIFY_API_TOKEN`, extract the already-validated ASIN with
`extract_amazon_asin()`, calculate `maxPages` as
`min(10, max(1, ceil(limit / 10)))`, and make exactly one synchronous POST.
Validate that the response is a list of objects. Decode only successful review
rows into `ProviderReviewCandidate(title, text, rating, date)`. Return an empty
candidate tuple for a valid no-result response so the import service maps it to
`no_reviews`; malformed envelopes remain `provider_response_invalid`.

Extend `_rating()` only for Axesso's anchored whole-string integer-star form,
such as `1.0 out of 5 stars` through `5.0 out of 5 stars`. Do not round
fractional ratings or extract arbitrary digits from other text.

Do not log or retain the response, personal fields, token, or raw diagnostics.
Do not retry.

- [ ] **Step 5: Switch the registry and remove active Outscraper code**

Register `ApifyAmazonReviewsAdapter()` for `amazon` and retain
`ApifyGoogleMapsAdapter()` for `google_maps`. Remove the Outscraper module and
fixture only after no production or test import references them. This does not
change stored history strings.

- [ ] **Step 6: Re-run adapter and registry/import tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters tests.test_import_normalizer tests.test_import_service tests.test_import_api -v
```

Expected: all selected tests pass without network access.

- [ ] **Step 7: Commit the provider replacement**

```powershell
git add backend/app/imports/apify_amazon.py backend/app/imports/apify.py backend/app/imports/normalizer.py backend/app/imports/registry.py backend/app/imports/outscraper.py tests/fixtures/apify_axesso_amazon_reviews.json tests/fixtures/outscraper_amazon_reviews.json tests/test_import_adapters.py tests/test_import_normalizer.py
git commit -m "feat: import Amazon reviews through Apify Axesso"
```

---

### Task 4: Expose the new limits through the service and HTTP API

**Files:**

- Modify: `tests/test_import_service.py`
- Modify: `tests/test_import_api.py`

**Behavior:**

- `GET /api/import/options` returns `10, 20, 50, 100` for both platforms.
- `POST /api/import` accepts 50 and 100 at the public model boundary.
- Limit 5 is rejected by the import service before a provider call.
- Provider label for new Amazon evidence is `Apify (Axesso)`.

- [ ] **Step 1: Write failing service/API assertions**

Add a two-adapter options test proving both platforms expose the exact shared
limit sequence and options loading makes no provider request. Update Amazon API
fixtures to `Apify (Axesso)` and a supported limit. Add public-boundary tests
for limit 100 validation and above-100 rejection. Keep the service-level test
for 5 so adapter policy—not only Pydantic bounds—is exercised.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_service tests.test_import_api tests.test_import_models -v
```

Expected: remaining old-limit and old-provider assertions fail.

- [ ] **Step 3: Make the smallest fixture/assertion updates**

The production service should continue deriving options from registered
adapters. Do not add dashboard-owned or route-owned limit duplication. Update
only stale test data unless a focused failure exposes a real production gap.

- [ ] **Step 4: Re-run focused tests and commit**

Run the Step 2 command.

Expected: all selected tests pass.

```powershell
git add tests/test_import_service.py tests/test_import_api.py
git commit -m "test: cover expanded provider import limits"
```

---

### Task 5: Preserve import provenance across the 40-review analysis boundary

**Files:**

- Modify: `backend/app/main.py`
- Modify: `backend/app/service.py`
- Modify: `tests/test_api_mvp.py`
- Modify: `tests/test_service_mvp.py`
- Modify: `tests/test_demo_data.py`

**Internal interface:**

```python
def run_analysis(
    request: AnalysisRequest,
    *,
    credential_validator=validate_groq_credentials,
    analyzer=analyze_reviews,
) -> AnalysisResponse:
    ...
```

- [ ] **Step 1: Write failing analysis-subset tests**

Build an `AnalysisRequest` whose provider source has
`requested_count=100/retrieved_count=100` and whose reviews contain the first
40 normalized items. Prove:

- the API passes the exact validated `AnalysisRequest` to the injected service;
- `run_analysis()` analyzes those 40 reviews once;
- response source provenance still reports 100 retrieved;
- metrics and response evidence report exactly 40;
- the returned report is saved once with the same 40 reviews;
- 41 submitted reviews are rejected before service or Groq work.

Retain existing tests for credential preflight order, generic collection
analysis, demo provenance, safe errors, and history-save behavior.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp tests.test_service_mvp tests.test_demo_data -v
```

Expected: current API conversion to `CollectionResult` rejects the deliberate
40-of-100 subset.

- [ ] **Step 3: Change only the internal analysis-service input**

Pass the validated `AnalysisRequest` directly from `/api/analyze` to
`analysis_service`. Update `run_analysis()` to use `request.source` and
`request.reviews`. Keep the HTTP JSON shape, `AnalysisResponse`, insight schema,
metric calculation, Groq credential preflight, exception mapping, and history
save order unchanged.

- [ ] **Step 4: Re-run focused tests**

Run the Step 2 command.

Expected: all selected tests pass and no Groq call occurs.

- [ ] **Step 5: Commit the analysis boundary adjustment**

```powershell
git add backend/app/main.py backend/app/service.py tests/test_api_mvp.py tests/test_service_mvp.py tests/test_demo_data.py
git commit -m "refactor: analyze bounded review subsets"
```

---

### Task 6: Make the dashboard generic and disclose the analyzed subset

**Files:**

- Modify: `dashboard/api_client.py`
- Modify: `dashboard/streamlit_app.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces/behavior:**

```python
MAX_ANALYSIS_REVIEWS = 40

def analysis_call(collection, base_url, *, request=request_analysis):
    analysis_collection = {
        **collection,
        "reviews": list(collection.get("reviews", []))[:MAX_ANALYSIS_REVIEWS],
    }
    return request(analysis_collection, base_url)
```

- [ ] **Step 1: Write failing pure-helper/client tests**

Update the import client test to use limit 20 and expect a timeout longer than
120 seconds (use 130 seconds). Add `analysis_call()` tests proving:

- 40 or fewer reviews are forwarded unchanged in order;
- 50 and 100 imports forward exactly the first 40;
- the input collection remains unchanged;
- source metadata, including `retrieved_count`, is unchanged.

Extend `source_details()` tests so a report displaying 40 reviews from source
metadata with `retrieved_count=100` includes
`40 of 100 reviews analyzed`, while a pre-analysis 100-review collection does
not claim partial analysis.

- [ ] **Step 2: Write failing rendered UI tests**

Update `AppTest` options to the shared limits. Assert the form contains:

- selector label `Review source`;
- text field label `Source URL`;
- generic placeholder `Paste an Amazon product or Google Maps place URL`;
- no `Amazon product URL` or `Google Maps place URL`;
- limits `10/20/50/100`, defaulting to 20.

Load a fixture collection with 50 reviews and assert all 50 are visible before
analysis, a caption explains that Groq will analyze the first 40, the mocked
analysis request receives 40, and the rendered report discloses
`40 of 50 reviews analyzed`.

- [ ] **Step 3: Run dashboard tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: old platform-specific labels/limits, unsliced analysis payload, and
65-second import timeout fail the new assertions.

- [ ] **Step 4: Implement the generic controls and bounded payload**

Use one fixed `Source URL` label and generic placeholder after platform
selection. Keep the backend-supplied option sequence and second-option default.
Use `[10, 20, 50, 100]` only as a defensive local fallback if an option payload
omits limits.

Slice only the copy passed to `request_analysis`; do not mutate
`st.session_state["collection"]`. Before analysis, show
`Groq will analyze the first 40 of N imported reviews.` only when `N > 40`.
When `source_details()` receives fewer displayed report reviews than the
provider source's `retrieved_count`, add exactly
`40 of N reviews analyzed` to report provenance.

Raise the dashboard import request timeout from 65 to 130 seconds so it exceeds
the backend adapter's 120-second read timeout. Do not add a retry.

- [ ] **Step 5: Re-run dashboard tests**

Run the Step 3 command.

Expected: all selected tests pass without Streamlit or HTTP warnings.

- [ ] **Step 6: Commit the UI milestone**

```powershell
git add dashboard/api_client.py dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: add generic bounded review imports"
```

---

### Task 7: Update configuration, provider caveats, and compatibility docs

**Files:**

- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Modify: `tests/test_import_documentation.py`
- Modify: `tests/test_history.py`

- [ ] **Step 1: Write failing documentation and history assertions**

Require:

- `APIFY_API_TOKEN=` remains blank in `.env.example`;
- `OUTSCRAPER_API_KEY` is absent from active setup/configuration;
- both public Actor names, the shared limits, generic URL wording, 40-review
  analysis boundary, 30-day cache, explicit refresh, fixture-only tests, and
  no source credentials/cookies/session tokens are documented;
- Axesso cost estimates and mutable-pricing caveat are documented;
- Apify provider-side storage, unofficial scraping, Amazon/Google terms, and
  local cache/history retention concerns remain explicit;
- no Actor copy/task/schedule/custom configuration is required;
- historical `provider="Outscraper"` rows still list and restore unchanged.

- [ ] **Step 2: Run documentation/history tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_documentation tests.test_history -v
```

Expected: stale Outscraper active-setup and old-limit text fails.

- [ ] **Step 3: Update operator documentation**

Document that both imports use one backend-only Apify token but remain separate,
replaceable, unofficial adapters. Replace Outscraper setup and usage examples
with Axesso. Explain that requesting 100 is a ceiling, Amazon can return fewer
usable written reviews, imports display the actual count, and Groq analyzes only
the first 40.

State that Axesso may return personal fields transiently and does not expose
Google's `personalData: false` control; ReviewInsight discards them but cannot
prevent provider-side processing/storage. Preserve direct links to the Amazon
Conditions of Use, Google Maps Additional Terms, Actor pages, and Apify pricing.

- [ ] **Step 4: Re-run focused documentation/history tests**

Run the Step 2 command.

Expected: all selected tests pass.

- [ ] **Step 5: Commit documentation**

```powershell
git add .env.example README.md docs/architecture.md docs/project_status.md tests/test_import_documentation.py tests/test_history.py
git commit -m "docs: configure Apify review providers"
```

---

### Task 8: Full offline regression and final review

**Files:**

- Review all milestone changes
- Do not add or stage unrelated `review_intelligence_flow.png`

- [ ] **Step 1: Prove no active Outscraper implementation remains**

```powershell
rg -n "OUTSCRAPER_API_KEY|OutscraperAmazonAdapter|outscraper_amazon" backend dashboard .env.example README.md docs tests
```

Expected: no active code/configuration references. Only deliberate historical
compatibility assertions or explanatory migration text may mention
`Outscraper`.

- [ ] **Step 2: Prove test code has no live-provider path**

Inspect adapter tests for injected fake sessions and credential patches. Confirm
there is no test invocation of a real `requests` session, real Apify endpoint,
Amazon/Google page, or Groq client.

- [ ] **Step 3: Run the complete automated suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Expected: all tests pass; zero external quota is consumed.

- [ ] **Step 4: Compile the application**

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: exit code 0 and no output.

- [ ] **Step 5: Review the final diff and workspace**

```powershell
git diff --check
git status --short
git diff --stat
git log -8 --oneline
```

Expected: no whitespace errors; only approved milestone files are modified by
the implementation; unrelated `review_intelligence_flow.png` remains untracked
and unstaged.

- [ ] **Step 6: Request code review and fix only approved-scope findings**

Use `superpowers:requesting-code-review`, then address concrete correctness,
privacy, quota, fixture isolation, or compatibility issues. Re-run the full
suite after any change.

- [ ] **Step 7: Commit final test-only or review corrections if needed**

```powershell
git add .env.example README.md backend/app/main.py backend/app/models.py backend/app/service.py backend/app/imports/apify.py backend/app/imports/apify_amazon.py backend/app/imports/contracts.py backend/app/imports/normalizer.py backend/app/imports/policies.py backend/app/imports/registry.py backend/app/imports/outscraper.py dashboard/api_client.py dashboard/streamlit_app.py docs/architecture.md docs/project_status.md tests/fixtures/apify_axesso_amazon_reviews.json tests/fixtures/outscraper_amazon_reviews.json tests/test_api_mvp.py tests/test_dashboard_mvp.py tests/test_demo_data.py tests/test_history.py tests/test_import_adapters.py tests/test_import_api.py tests/test_import_documentation.py tests/test_import_models.py tests/test_import_normalizer.py tests/test_import_policy.py tests/test_import_service.py tests/test_service_mvp.py
git commit -m "test: verify Apify review import milestone"
```

Do not create an empty commit when no corrections are needed.

## Material risks and planned safeguards

- **Actor response drift:** validate only the minimal dataset list/object shape,
  keep decoding isolated in the Axesso adapter, and map malformed output to
  `provider_response_invalid`.
- **Provider personal fields:** keep deliberate fixture markers and prove they
  are discarded before normalization, cache, analysis, or history.
- **Unexpected usage:** shared low limits, one synchronous run, no retry,
  30-day cache, and explicit refresh only.
- **Long Amazon runs:** backend `(5, 120)` timeout plus dashboard 130-second
  timeout, with no automatic retry after timeout.
- **Requested versus actual count:** retain `requested_count` and
  `retrieved_count`; normalize/filter before enforcing the selected ceiling.
- **100 imported versus 40 analyzed:** keep the import collection untouched,
  pass only a copied first-40 slice to analysis, preserve source provenance,
  disclose the subset, and store only analyzed evidence in report history.
- **Old data:** keep stored `Outscraper` provenance readable and isolate new
  Amazon cache entries by provider key; no database migration.
- **Replaceability:** provider-specific Actor ID, payload, response decoding,
  timeout, and label live only in `apify_amazon.py`; service, API, cache,
  dashboard, analysis, and history remain provider-neutral.

## No planned deviations from the approved design

The only newly explicit implementation detail is raising the dashboard import
timeout to 130 seconds so it does not expire before the approved Axesso
120-second backend read timeout. This is required for the designed synchronous
request and does not expand scope.
