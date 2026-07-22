# Amazon and Google Maps Review Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-only Outscraper Amazon and Apify Google Maps review imports that feed the existing evidence, Groq analysis, report, and history flow without live calls in automated tests.

**Architecture:** A platform registry selects one narrow provider adapter. `ReviewImportService` validates the platform URL, checks an isolated 30-day SQLite cache, invokes the adapter once on a miss or explicit refresh, normalizes provider output, and returns the existing `CollectionResult` with additive provenance. FastAPI exposes provider-neutral options/import endpoints; Streamlit consumes those endpoints and never receives credentials.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, requests, SQLite, Streamlit, unittest, saved JSON fixtures.

## Global Constraints

- Amazon uses Outscraper with limits `5`, `10`, or `12`; Google Maps uses `compass/google-maps-reviews-scraper` with limits `5`, `10`, or `20`.
- Accept one public URL and make at most one provider request per explicit miss or refresh; no pagination, automatic retries, jobs, polling, schedules, or webhooks.
- Never request Amazon/Google user credentials, cookies, browser profiles, or session tokens.
- Provider credentials are backend-only `OUTSCRAPER_API_KEY` and `APIFY_API_TOKEN` values.
- Keep the static `/api/collect`, demo, Groq analysis, deterministic metrics, and report-history flows compatible.
- Cache normalized evidence for 30 days in `data/review_import_cache.db`; only explicit refresh bypasses a live entry.
- Automated tests use fixtures, injected fake sessions, temporary SQLite files, and mocks only. They never call Outscraper, Apify, Amazon, Google Maps, or Groq.
- Persist no reviewer names, profiles, avatars, media, owner responses, raw provider bodies, provider request logs, cookies, or credentials.
- Do not add a provider selector, batch import, non-`amazon.com` marketplace support, background cleanup, or official Google Places mode.

## External setup checklist

No external setup is required to run automated tests or the existing demo. Live imports require all items for the selected platform:

- **Amazon:** create an Outscraper account, obtain an API key, confirm the Amazon Reviews API is enabled, and set `OUTSCRAPER_API_KEY` in the repository-root `.env` or process environment. Keep the account on the published first-500-reviews-per-30-days free allowance or a prepaid/non-overage configuration. Review current pricing before enabling it.
- **Google Maps:** create an Apify account, remain on the `$0` Free plan unless intentionally upgrading, obtain the API token from Console **Settings / API & Integrations**, and set `APIFY_API_TOKEN`. The Free plan currently includes `$5` monthly non-rollover usage, needs no card, and hard-stops at the free limit. If a paid plan is used, configure the lowest practical platform spending limit before testing.
- **Apify Actor:** no Actor copy, task, schedule, build, webhook, or custom Actor ID is required. The application calls the public `compass/google-maps-reviews-scraper` Actor directly using `compass~google-maps-reviews-scraper`, with one `startUrls` item, `maxReviews`, `reviewsSort: mostRelevant`, `reviewsOrigin: google`, `personalData: false`, and `language: en`.
- **Groq:** `GROQ_API_KEY` remains required only when the user explicitly selects **Analyze with Groq** after import; it is not needed to import or read cached reviews.
- Do not place real secrets in `.env.example`, source, test fixtures, screenshots, logs, or requests from the browser.
- If an account, key/token, Actor availability, free-plan/spending configuration, or environment value is missing, stop before any manual live smoke request. Implementation and automated verification still proceed with fixtures.

---

### Task 1: Shared import contracts, URL policies, and provider-neutral normalization

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/imports/__init__.py`
- Create: `backend/app/imports/contracts.py`
- Create: `backend/app/imports/policies.py`
- Create: `backend/app/imports/normalizer.py`
- Create: `tests/test_import_models.py`
- Create: `tests/test_import_policy.py`
- Create: `tests/test_import_normalizer.py`

**Interfaces:**
- Produces `ImportRequest`, `ImportOptions`, `ImportPlatformOption`, additive `SourceInfo` fields, and additive `HistoryItem` fields.
- Produces `ReviewImportError`, `ProviderReviewCandidate`, `ProviderImportResult`, `ReviewProviderAdapter`, `ValidatedImportSource`, `validate_import_source()`, and `normalize_provider_result()`.

- [ ] **Step 1: Write failing model tests**

Cover defaults for old generic/demo payloads, `provider_api` provenance, platform limits, extra-field rejection, and imported `retrieved_count == len(reviews)` validation. Use an imported source such as:

```python
SourceInfo(
    url="https://www.amazon.com/dp/B000000000",
    title="Amazon product B000000000",
    extractor="provider_api",
    is_demo=False,
    platform="amazon",
    provider="Outscraper",
    requested_count=10,
    retrieved_count=2,
    retrieved_at="2026-07-22T12:00:00+00:00",
    cache_status="miss",
)
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_models -v`

Expected: import errors for missing import models and unsupported `provider_api` provenance.

- [ ] **Step 3: Add the public models and compatibility defaults**

Add `platform="generic"`, nullable provider/count/time fields, and `cache_status="not_applicable"` defaults to `SourceInfo`; add `provider_api` to the extractor literal. Add nullable `platform` and `provider` defaults to `HistoryItem`. Add strict request/options models. Preserve the existing demo validator and validate imported counts at the collection boundary without rejecting old stored reports that omit the additive fields.

- [ ] **Step 4: Run model tests and the existing model/API/history tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_models tests.test_api_mvp tests.test_history tests.test_demo_data -v`

Expected: all selected tests pass.

- [ ] **Step 5: Write failing URL-policy and normalization tests**

Accept HTTPS `amazon.com` `/dp/{ASIN}` and `/gp/product/{ASIN}` URLs; accept Google `/maps/place/`, `/maps/reviews/`, `google.com/maps?cid=...`, and non-root `maps.app.goo.gl` URLs. Reject credentials, HTTP, platform mismatches, Amazon search/review-detail pages, Google free-text/search URLs, and unsupported hosts. Normalize whitespace/title/body, integer ratings, ISO dates, duplicates, short/star-only entries, and apply limits after filtering.

- [ ] **Step 6: Run policy and normalizer tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_policy tests.test_import_normalizer -v`

Expected: import errors for the absent modules.

- [ ] **Step 7: Implement narrow contracts, policies, and normalizer**

Use immutable dataclasses for provider candidates/results and a protocol with:

```python
class ReviewProviderAdapter(Protocol):
    provider_key: str
    provider_label: str
    platform: str
    allowed_limits: tuple[int, ...]

    def fetch(self, source_url: str, limit: int) -> ProviderImportResult: ...
```

Return an ASIN cache identity for Amazon and a SHA-256 normalized-input-URL identity for Google. The normalizer must emit only local `Review(id="rN", ...)` objects and never carry provider/reviewer IDs.

- [ ] **Step 8: Run the focused tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_models tests.test_import_policy tests.test_import_normalizer -v`

Commit: `feat: add review import contracts and normalization`

### Task 2: Outscraper and Apify provider adapters

**Files:**
- Create: `backend/app/imports/outscraper.py`
- Create: `backend/app/imports/apify.py`
- Create: `backend/app/imports/registry.py`
- Create: `tests/fixtures/outscraper_amazon_reviews.json`
- Create: `tests/fixtures/apify_google_maps_reviews.json`
- Create: `tests/test_import_adapters.py`

**Interfaces:**
- Consumes the Task 1 adapter protocol and provider-neutral result types.
- Produces `OutscraperAmazonAdapter`, `ApifyGoogleMapsAdapter`, and `build_default_registry()`.

- [ ] **Step 1: Save minimal sanitized provider fixtures**

The Outscraper fixture mirrors `{status, data: [[reviews...]]}` with only `query`, `product_asin`, `title`, `body`, `rating`, `date`, and `product_url`. The Apify fixture is a list with `text`, `stars`, `publishedAtDate`, `title`, `placeId`, and `url`, plus deliberate reviewer/owner/media markers that tests prove are discarded.

- [ ] **Step 2: Write failing adapter contract tests**

Assert Outscraper sends one GET to `https://api.outscraper.com/amazon-reviews`, header `X-API-KEY`, params `query`, `limit`, `async=false`, and a minimal `fields` list with timeout `(5, 30)`. Assert Apify sends one POST to `https://api.apify.com/v2/acts/compass~google-maps-reviews-scraper/run-sync-get-dataset-items`, bearer auth, input:

```python
{
    "startUrls": [{"url": source_url}],
    "maxReviews": limit,
    "reviewsSort": "mostRelevant",
    "reviewsOrigin": "google",
    "personalData": False,
    "language": "en",
}
```

and timeout `(5, 60)`. Assert neither request has cookies/session fields or tokens in URLs.

- [ ] **Step 3: Run adapter tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters -v`

Expected: import errors for absent adapters.

- [ ] **Step 4: Implement the adapters with injected sessions and credential readers**

Read and trim only the selected provider environment variable at fetch time. Map missing key, `401/403`, quota `402/429`, timeout, other rate-limit/unavailable `5xx`, transport errors, invalid JSON/schema, and non-success Outscraper status to `ReviewImportError` codes. Decode only expected fields into provider-neutral candidates; discard all identity/media/owner fields.

- [ ] **Step 5: Run adapter tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters -v`

Expected: all adapter tests pass with fake sessions and fixtures; no network request occurs.

- [ ] **Step 6: Commit**

Commit: `feat: add Outscraper and Apify review adapters`

### Task 3: Isolated import cache and orchestration service

**Files:**
- Create: `backend/app/import_cache.py`
- Create: `backend/app/imports/service.py`
- Create: `tests/test_import_cache.py`
- Create: `tests/test_import_service.py`

**Interfaces:**
- Produces `ImportCacheStore.get(cache_key)`, `ImportCacheStore.put(cache_key, collection, metadata, expires_at)`, `ReviewImportService.options()`, and `ReviewImportService.import_reviews(request)`.

- [ ] **Step 1: Write failing cache tests**

Use temporary SQLite paths and a controllable UTC clock. Cover lazy schema creation, atomic upsert, 30-day expiry, corrupt JSON, metadata-separated keys, credential/reviewer-marker absence, and safe `cache_failed` errors.

- [ ] **Step 2: Run cache tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_cache -v`

Expected: import error for absent cache store.

- [ ] **Step 3: Implement the isolated SQLite cache**

Create `review_import_cache` with key, platform, provider, contract version, source hash, requested limit, ordering, fetched/expiry times, and normalized collection JSON. Initialize lazily, use transactions, validate cached JSON through `CollectionResult`, delete expired/corrupt entries lazily, and map filesystem/SQLite/validation failures without raw details.

- [ ] **Step 4: Run cache tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_cache -v`

- [ ] **Step 5: Write failing service tests**

Cover registry-driven options, invalid platform/limit/URL before adapter calls, cache hit without key access, first miss, explicit refresh, failed refresh preserving the old cache, expiry, fewer-than-requested success, fewer-than-two failure, exact call count, provenance, and cache separation by provider/contract/source/limit/order.

- [ ] **Step 6: Run service tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_service -v`

Expected: import error for absent service.

- [ ] **Step 7: Implement the orchestration service**

Use the default ordering key `most_relevant`, cache contract version `1`, and 30-day TTL. On a hit, return a copy with `cache_status="hit"`; on miss/refresh, call exactly once, normalize, require two reviews, construct provider provenance, atomically save, and return `miss` or `refresh`. Never invoke analysis or history.

- [ ] **Step 8: Run focused tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_import_cache tests.test_import_service -v`

Commit: `feat: cache and orchestrate review imports`

### Task 4: Provider-neutral FastAPI routes and safe errors

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `tests/test_api_mvp.py`

**Interfaces:**
- Adds `GET /api/import/options` and `POST /api/import`.
- `create_app(..., import_service=None)` remains injectable and does not eagerly call providers.

- [ ] **Step 1: Write failing route and error tests**

Assert the exact route set, options response, exact one-call import request, no analysis/history calls, validation mapping, every approved import error/status/message, unknown-error sanitization, and no token/raw-body marker in responses.

- [ ] **Step 2: Run API tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp -v`

Expected: missing routes and unsupported `create_app(import_service=...)`.

- [ ] **Step 3: Add import composition and routes**

Construct the default registry/cache/service only when none is injected. Map `ReviewImportError` through an `IMPORT_ERRORS` allowlist. Map request-validation locations to `unsupported_import_platform`, `unsupported_import_limit`, or `invalid_import_url`. Keep `/api/collect`, demo, analyze, and history handlers unchanged except imports and additive route registration.

- [ ] **Step 4: Run API and regression tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp tests.test_collector_mvp tests.test_service_mvp tests.test_analyzer_mvp -v`

Expected: all selected tests pass without configured provider keys.

- [ ] **Step 5: Commit**

Commit: `feat: expose safe review import API`

### Task 5: Additive history provenance migration

**Files:**
- Modify: `backend/app/history.py`
- Modify: `tests/test_history.py`

**Interfaces:**
- `analysis_history` gains nullable `platform` and `provider` summary columns.
- Existing databases and old report JSON remain readable.

- [ ] **Step 1: Write failing migration and round-trip tests**

Create a legacy table with the old schema, initialize `HistoryStore`, and assert idempotent `ALTER TABLE` additions. Save imported Amazon/Google reports, list stable provider/platform summaries, and verify an old report with missing provenance loads with compatibility defaults.

- [ ] **Step 2: Run history tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_history -v`

Expected: missing summary columns/fields.

- [ ] **Step 3: Implement additive migration and persistence**

After `CREATE TABLE IF NOT EXISTS`, inspect `PRAGMA table_info` and add only missing nullable columns. Include platform/provider in inserts and summary selects. Never rewrite existing report JSON or drop/recreate the table.

- [ ] **Step 4: Run history tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_history tests.test_api_mvp -v`

Commit: `feat: preserve import provenance in history`

### Task 6: Dashboard client and staged import UI

**Files:**
- Modify: `dashboard/api_client.py`
- Modify: `dashboard/streamlit_app.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Adds `request_import_options(base_url)` and `request_import(platform, url, limit, refresh, base_url)`.
- Preserves `request_collection()` for compatibility but changes the primary UI to provider imports.

- [ ] **Step 1: Write failing dashboard-client tests**

Assert options GET timeout `5`, import POST payload and timeout `65`, safe transport decoding, and strict result shapes. Update all-stage timeout coverage without removing collection/demo/analysis/history cases.

- [ ] **Step 2: Run dashboard tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardClientTests -v`

Expected: missing client functions.

- [ ] **Step 3: Implement the two client functions**

Reuse `_perform_request` and `_decode_success`; pass no provider names, endpoints, credentials, cookies, or sessions in request JSON.

- [ ] **Step 4: Write failing UI source/runtime tests**

Cover options-driven source/limit controls, explicit import and demo actions, actual/requested/provider/original URL/fetched/cache provenance, refresh only for provider collections, refresh warning, no passive refresh, failed-refresh state preservation, history provenance, and analysis forwarding only source/reviews.

- [ ] **Step 5: Run UI tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v`

- [ ] **Step 6: Implement the staged UI with minimal helper changes**

Load options without provider contact, render a platform selectbox and allowed-limit selectbox, import only on form submit, keep demo explicit, render provider provenance, and add a secondary **Refresh from source** button that calls import with `refresh=True`. The refresh helper must not clear current collection/report before success; initial import may replace old state only after success. Loaded history has no refresh action.

- [ ] **Step 7: Run dashboard and end-to-end unit tests, then commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp tests.test_api_mvp tests.test_history -v`

Commit: `feat: add staged provider import dashboard`

### Task 7: Configuration, usage, terms, and architecture documentation

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Modify: `tests/test_documentation.py`
- Modify: `tests/test_live_source_documentation.py`

**Interfaces:**
- Documents all operator setup and caveats without exposing secrets or claiming official endorsement.

- [ ] **Step 1: Write failing documentation audits**

Require `OUTSCRAPER_API_KEY`, `APIFY_API_TOKEN`, actor ID, per-platform limits, 30-day cache, explicit refresh, fixture-only tests, free-tier estimates, no-cookie/session rule, unofficial-service statement, source terms links, Apify retention note, and manual smoke stop conditions. Reject browser credential fields and claims that imports are official APIs.

- [ ] **Step 2: Run documentation tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_documentation tests.test_live_source_documentation -v`

- [ ] **Step 3: Update configuration and documentation**

Add blank provider variables to `.env.example`; add setup checklist, API routes, cache/storage behavior, free-tier planning estimates, safe errors, unofficial provider/terms/privacy caveats, and fixture-only verification commands. Keep the generic static collector documented as a preserved compatibility endpoint, not the primary Amazon/Google flow.

- [ ] **Step 4: Run documentation tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_documentation tests.test_live_source_documentation -v`

Commit: `docs: document review import setup and limits`

### Task 8: Full verification and approved-scope review

**Files:**
- Review all modified files; change only defects found by verification.

- [ ] **Step 1: Run the complete fixture-only test suite**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`

Expected: zero failures and no live provider/Groq request.

- [ ] **Step 2: Compile all Python sources**

Run: `.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py`

Expected: exit code `0` and no output.

- [ ] **Step 3: Audit secrets and forbidden source-credential flows**

Run: `rg -n "AMAZON_(USERNAME|PASSWORD)|GOOGLE_(USERNAME|PASSWORD)|cookie|session[_-]?token|token=.*APIFY|X-API-KEY.*[A-Za-z0-9]{16}" backend dashboard tests .env.example README.md docs`

Expected: only deliberate documentation/tests denying these flows; no literal secret or browser credential input.

- [ ] **Step 4: Review diff against every acceptance criterion**

Confirm one request per miss/refresh, low limits, 30-day cache, explicit refresh, actual counts and provenance, no passive provider work, additive history, adapter replacement boundary, unofficial/terms/storage caveats, and preserved generic/demo/Groq/history behavior.

- [ ] **Step 5: Inspect repository state and final diff**

Run: `git diff --check`, `git status --short`, and `git diff --stat main...HEAD`.

Expected: no whitespace errors or unrelated files.

- [ ] **Step 6: Commit any verification fixes separately**

Commit only if Step 1-5 required changes, using a focused `fix:` message.
