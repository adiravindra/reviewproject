# Automation Lab Amazon and Diverse Reviews Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the paywalled Axesso Amazon Actor with Automation Lab's free-plan-compatible Amazon Reviews Scraper and prove that Amazon and Google Maps preserve naturally mixed review ratings without positive-only filters.

**Architecture:** Keep the existing provider registry and `ReviewProviderAdapter` boundary. Change only the Amazon Actor identity, exact request body, response decoder, provider metadata, fixture, and active documentation; leave the Google request unchanged but add mixed-rating contract coverage. The service, cache, API, dashboard, analysis, report, history, and demo layers remain provider-neutral.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Requests, Streamlit, SQLite, `unittest`, Apify synchronous Actor API.

## Global Constraints

- Amazon Actor: `automation-lab/amazon-reviews-scraper`.
- Google Maps Actor remains `compass/google-maps-reviews-scraper`.
- Use only the existing backend-only `APIFY_API_TOKEN`.
- Amazon request JSON contains exactly `asins`, `marketplace`, `maxReviewsPerProduct`, and `sort`.
- Amazon uses `sort: "helpful"` with no `filterByStars`, keyword, or positive-only filter.
- Google Maps keeps `reviewsSort: "mostRelevant"` with no rating filter.
- Shared review limits remain exactly `10`, `20`, `50`, and `100`.
- Preserve provider order and every usable review up to the selected limit.
- Do not reorder, duplicate, or drop usable reviews to manufacture rating balance.
- A source may legitimately contain uniform ratings or fewer reviews than requested.
- Keep requested and actual imported counts; do not add discard-reason provenance.
- Display all imported reviews up to 100 and analyze only the first 40, preserving the `40 of N reviews analyzed` disclosure.
- Preserve cache, explicit refresh, analysis, report, history, and demo flows.
- Give Automation Lab a new provider/cache identity; do not migrate cache data.
- Preserve historical reports labeled `Apify (Axesso)` and `Outscraper`.
- Never persist or log API tokens, raw provider bodies, reviewer names, profile URLs, provider review IDs, helpful counts, media, or other provider-only fields.
- Automated tests use sanitized fixtures, fake HTTP sessions, mocks, and temporary storage only.
- Automated tests must not contact Apify, Automation Lab, Compass, Amazon, Google Maps, or Groq.
- Stop and obtain explicit user approval before any live provider smoke request.
- Do not modify `review_intelligence_flow.png`.

---

## File Map

- `backend/app/imports/apify_amazon.py`: Automation Lab Actor identity, exact request, safe error handling, and response-to-candidate mapping.
- `backend/app/imports/apify.py`: Google Maps adapter; production behavior remains unchanged.
- `backend/app/imports/registry.py`: Existing provider-neutral registry; no production change expected.
- `backend/app/imports/normalizer.py`: Existing provider-neutral order, quality, rating, and date normalization; no production change expected.
- `tests/fixtures/apify_automation_lab_amazon_reviews.json`: New sanitized mixed-rating Automation Lab response.
- `tests/fixtures/apify_axesso_amazon_reviews.json`: Retired active fixture; remove after all references move.
- `tests/fixtures/apify_google_maps_reviews.json`: Expand to a mixed 5-/3-/1-star response.
- `tests/test_import_adapters.py`: Exact endpoints, bodies, decoding, privacy, error taxonomy, and natural-order assertions.
- `tests/test_import_policy.py`: Default Amazon provider metadata and unchanged URL/ASIN policy.
- `tests/test_import_normalizer.py`: Provider-neutral mixed-rating order preservation.
- `tests/test_import_cache.py`: New provider key isolation from the historical Axesso key.
- `tests/test_history.py`: Historical Axesso and Outscraper provenance compatibility.
- `tests/test_import_documentation.py`: Active Actor, pricing, diversity, and setup-document audits.
- `README.md`: Operator setup, active Actor, pricing, diversity, cache, and privacy caveats.
- `docs/architecture.md`: Active provider boundary and request behavior.
- `docs/project_status.md`: Current milestone/provider status and offline verification scope.

---

### Task 1: Replace the Amazon Actor Adapter

**Files:**
- Create: `tests/fixtures/apify_automation_lab_amazon_reviews.json`
- Modify: `tests/test_import_adapters.py`
- Modify: `tests/test_import_policy.py`
- Modify: `backend/app/imports/apify_amazon.py`
- Delete: `tests/fixtures/apify_axesso_amazon_reviews.json`

**Interfaces:**
- Consumes: `extract_amazon_asin(source_url: str) -> str | None`, `IMPORT_LIMITS`, `ProviderImportResult`, `ProviderReviewCandidate`, `ReviewImportError`, and `classify_provider_status(status_code: int) -> None`.
- Produces: `ApifyAmazonReviewsAdapter.fetch(source_url: str, limit: int) -> ProviderImportResult` with `provider_key = "apify_automation_lab_amazon"` and `provider_label = "Apify (Automation Lab)"`.
- Produces constants: `AUTOMATION_LAB_ACTOR_ID`, `AUTOMATION_LAB_ENDPOINT`, and `AUTOMATION_LAB_TIMEOUT`.

- [ ] **Step 1: Add a sanitized Automation Lab fixture**

Create `tests/fixtures/apify_automation_lab_amazon_reviews.json` with provider order deliberately spanning positive, neutral, and negative ratings:

```json
[
  {
    "asin": "B0GR6F79MT",
    "title": "Most useful positive review",
    "body": "The laptop is fast, quiet, and lasts through a full workday.",
    "rating": 5,
    "date": "Reviewed in the United States on July 20, 2026",
    "author": "discard-reviewer-marker",
    "authorUrl": "https://example.invalid/discard-profile",
    "reviewId": "discard-review-id",
    "helpfulVotes": 42,
    "reviewUrl": "https://example.invalid/discard-review-url",
    "isVerifiedPurchase": true,
    "scrapedAt": "2026-07-20T12:00:00.000Z"
  },
  {
    "asin": "B0GR6F79MT",
    "title": "Useful but mixed",
    "body": "Performance is steady, although the port selection is only adequate.",
    "rating": 3,
    "date": "Reviewed in the United States on July 18, 2026",
    "author": "discard-neutral-reviewer"
  },
  {
    "asin": "B0GR6F79MT",
    "title": "Important reliability concern",
    "body": "The display began flickering after several days of ordinary use.",
    "rating": 1,
    "date": "Reviewed in the United States on July 16, 2026",
    "author": "discard-negative-reviewer"
  }
]
```

- [ ] **Step 2: Write failing request, metadata, decoding, and privacy tests**

In `tests/test_import_adapters.py`, replace Axesso imports and the main Amazon contract test with:

```python
from backend.app.imports.apify_amazon import (
    AUTOMATION_LAB_ENDPOINT,
    AUTOMATION_LAB_TIMEOUT,
    ApifyAmazonReviewsAdapter,
)


def test_automation_lab_uses_exact_unfiltered_request_for_each_allowed_limit(self):
    """Send one ASIN with the exact approved natural-sample input."""

    for limit in (10, 20, 50, 100):
        with self.subTest(limit=limit):
            session = FakeSession(
                FakeResponse(
                    payload=load_fixture(
                        "apify_automation_lab_amazon_reviews.json"
                    )
                )
            )
            with patch.dict(
                os.environ,
                {"APIFY_API_TOKEN": "  test-apify-token  "},
                clear=False,
            ):
                result = ApifyAmazonReviewsAdapter(session=session).fetch(
                    "https://www.amazon.com/dp/B0GR6F79MT"
                    "?ref=share&social_share=example&th=1",
                    limit,
                )

            self.assertEqual(len(session.calls), 1)
            method, url, kwargs = session.calls[0]
            self.assertEqual((method, url), ("post", AUTOMATION_LAB_ENDPOINT))
            self.assertEqual(
                kwargs["headers"]["Authorization"],
                "Bearer test-apify-token",
            )
            self.assertNotIn("token=", url)
            self.assertEqual(kwargs["timeout"], AUTOMATION_LAB_TIMEOUT)
            self.assertEqual(
                kwargs["json"],
                {
                    "asins": ["B0GR6F79MT"],
                    "marketplace": "US",
                    "maxReviewsPerProduct": limit,
                    "sort": "helpful",
                },
            )
            self.assertEqual(result.title, "Amazon product B0GR6F79MT")
            self.assertEqual(result.source_key, "B0GR6F79MT")
            self.assertEqual(
                [review.rating for review in result.reviews],
                [5, 3, 1],
            )
            self.assertEqual(
                [review.title for review in result.reviews],
                [
                    "Most useful positive review",
                    "Useful but mixed",
                    "Important reliability concern",
                ],
            )
            for marker in (
                "discard-reviewer-marker",
                "discard-profile",
                "discard-review-id",
                "discard-review-url",
                "discard-neutral-reviewer",
                "discard-negative-reviewer",
            ):
                self.assertNotIn(marker, repr(result))
```

Rename the remaining Amazon tests from `axesso` to `automation_lab`, point them
at the new fixture, and retain the existing fake-only cases for:

```python
(
    (FakeResponse(400, []), "provider_request_rejected"),
    (FakeResponse(401, []), "provider_auth_failed"),
    (FakeResponse(402, []), "provider_quota_exhausted"),
    (FakeResponse(404, []), "provider_request_rejected"),
    (FakeResponse(409, []), "provider_request_rejected"),
    (FakeResponse(422, []), "provider_request_rejected"),
    (FakeResponse(429, []), "provider_unavailable"),
    (FakeResponse(503, []), "provider_unavailable"),
    (requests.Timeout("secret timeout"), "import_timeout"),
    (requests.ConnectionError("secret socket"), "provider_unavailable"),
    (
        FakeResponse(
            200,
            json_error=requests.exceptions.JSONDecodeError(
                "secret malformed JSON",
                "secret provider body",
                0,
            ),
        ),
        "provider_response_invalid",
    ),
    (FakeResponse(200, {}), "provider_response_invalid"),
    (FakeResponse(200, [1]), "provider_response_invalid"),
)
```

In `tests/test_import_policy.py`, add:

```python
from backend.app.imports.apify_amazon import ApifyAmazonReviewsAdapter
from backend.app.imports.registry import build_default_registry


def test_default_amazon_adapter_uses_automation_lab_identity(self):
    """Expose a new cache/provenance identity for the replacement Actor."""

    adapter = build_default_registry()["amazon"]

    self.assertIsInstance(adapter, ApifyAmazonReviewsAdapter)
    self.assertEqual(adapter.provider_key, "apify_automation_lab_amazon")
    self.assertEqual(adapter.provider_label, "Apify (Automation Lab)")
    self.assertIs(adapter.allowed_limits, IMPORT_LIMITS)
```

- [ ] **Step 3: Run the focused tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters tests.test_import_policy
```

Expected: FAIL because Automation Lab constants, provider metadata, exact body,
and response field mapping do not exist and the old Axesso fixture is still
active.

- [ ] **Step 4: Implement the minimal Automation Lab adapter**

In `backend/app/imports/apify_amazon.py`, replace the Axesso constants and
metadata with:

```python
AUTOMATION_LAB_ACTOR_ID = "automation-lab~amazon-reviews-scraper"
AUTOMATION_LAB_ENDPOINT = (
    "https://api.apify.com/v2/acts/"
    "automation-lab~amazon-reviews-scraper/run-sync-get-dataset-items"
)
AUTOMATION_LAB_TIMEOUT = (5, 120)


class ApifyAmazonReviewsAdapter:
    """Implement Amazon imports through one replaceable Automation Lab call."""

    provider_key = "apify_automation_lab_amazon"
    provider_label = "Apify (Automation Lab)"
    platform = "amazon"
    allowed_limits = IMPORT_LIMITS
```

Remove `math` because page-based calculation is no longer used. Replace the
POST call with:

```python
response = self.session.post(
    AUTOMATION_LAB_ENDPOINT,
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
    json={
        "asins": [asin],
        "marketplace": "US",
        "maxReviewsPerProduct": limit,
        "sort": "helpful",
    },
    timeout=AUTOMATION_LAB_TIMEOUT,
)
```

Keep the existing safe status, timeout, Requests JSON decode, transport, and
schema exception ordering. Replace Axesso-specific successful-record filtering
and candidate mapping with:

```python
first = items[0] if items else {}
source_key = str(first.get("asin") or "").strip().upper() or asin
title = f"Amazon product {source_key}"
reviews = tuple(
    ProviderReviewCandidate(
        title=item.get("title"),
        body=item.get("body"),
        rating=item.get("rating"),
        date=item.get("date"),
    )
    for item in items
)
return ProviderImportResult(title, source_url, source_key, reviews)
```

Update safe log copy from `Amazon review import failed` only if needed; do not
include the source URL, token, response body, or exception text.

- [ ] **Step 5: Remove the retired active fixture**

Delete:

```text
tests/fixtures/apify_axesso_amazon_reviews.json
```

Run:

```powershell
rg -n "apify_axesso_amazon_reviews|AXESSO_|axesso_uses|axesso_statuses|axesso_logs" backend tests
```

Expected: no matches.

- [ ] **Step 6: Run focused tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters tests.test_import_policy
```

Expected: PASS with no live HTTP calls and no uncaptured warning output.

- [ ] **Step 7: Review and commit Task 1**

Run:

```powershell
git diff --check
git diff -- backend/app/imports/apify_amazon.py tests/test_import_adapters.py tests/test_import_policy.py tests/fixtures
```

Confirm the request body has exactly four keys and no star/keyword filter.

Commit:

```powershell
git add backend/app/imports/apify_amazon.py tests/test_import_adapters.py tests/test_import_policy.py tests/fixtures/apify_automation_lab_amazon_reviews.json tests/fixtures/apify_axesso_amazon_reviews.json
git commit -m "feat: switch Amazon imports to Automation Lab"
```

---

### Task 2: Prove Natural Rating Diversity for Both Providers

**Files:**
- Modify: `tests/fixtures/apify_google_maps_reviews.json`
- Modify: `tests/test_import_adapters.py`
- Modify: `tests/test_import_normalizer.py`

**Interfaces:**
- Consumes: `ApifyGoogleMapsAdapter.fetch(source_url: str, limit: int) -> ProviderImportResult`.
- Consumes: `normalize_provider_result(result: ProviderImportResult, limit: int) -> NormalizedProviderResult`.
- Produces: Contract evidence that 5-, 3-, and 1-star reviews remain in provider order and are not filtered by either integration.

- [ ] **Step 1: Write failing Google diversity assertions**

In `test_apify_uses_one_private_bearer_request_and_disables_personal_data`,
retain the exact current Google request assertion and add:

```python
self.assertEqual(
    kwargs["json"],
    {
        "startUrls": [{"url": source_url}],
        "maxReviews": 10,
        "reviewsSort": "mostRelevant",
        "reviewsOrigin": "google",
        "personalData": False,
        "language": "en",
    },
)
self.assertTrue(
    {
        "filterByStars",
        "starRatings",
        "filterByRating",
        "minimumRating",
    }.isdisjoint(kwargs["json"])
)
self.assertEqual(
    [review.rating for review in result.reviews],
    [5, 3, 1],
)
```

- [ ] **Step 2: Write a failing provider-neutral order test**

Add to `tests/test_import_normalizer.py`:

```python
def test_preserves_provider_order_across_positive_neutral_and_negative_ratings(self):
    """Keep natural provider order without manufacturing sentiment balance."""

    result = ProviderImportResult(
        title="Mixed source",
        source_url="https://example.test/mixed",
        source_key="mixed-1",
        reviews=(
            ProviderReviewCandidate(
                "Positive",
                "This review describes a consistently excellent experience.",
                5,
                "2026-07-20",
            ),
            ProviderReviewCandidate(
                "Neutral",
                "This review describes an adequate but uneven experience.",
                3,
                "2026-07-19",
            ),
            ProviderReviewCandidate(
                "Negative",
                "This review describes a serious and repeatable failure.",
                1,
                "2026-07-18",
            ),
        ),
    )

    normalized = normalize_provider_result(result, limit=10)

    self.assertEqual(
        [review.rating for review in normalized.reviews],
        [5, 3, 1],
    )
    self.assertEqual(
        [
            review.text.startswith(expected)
            for review, expected in zip(
                normalized.reviews,
                ("Positive", "Neutral", "Negative"),
                strict=True,
            )
        ],
        [True, True, True],
    )
```

- [ ] **Step 3: Run the focused tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters tests.test_import_normalizer
```

Expected: the Google rating assertion FAILS because the existing fixture
contains only 5- and 4-star records. The provider-neutral order test may pass
immediately because it locks in existing correct behavior; it is a
characterization guard, not a request for new normalizer logic.

- [ ] **Step 4: Replace the Google fixture with mixed ratings**

Replace `tests/fixtures/apify_google_maps_reviews.json` with:

```json
[
  {
    "text": "Friendly staff and excellent coffee during a busy morning.",
    "stars": 5,
    "publishedAtDate": "2026-07-20T12:00:00.000Z",
    "title": "Test Cafe",
    "placeId": "ChIJFixturePlace",
    "url": "https://www.google.com/maps/place/Test+Cafe",
    "name": "discard-reviewer-marker",
    "reviewerUrl": "https://example.invalid/discard-profile",
    "responseFromOwnerText": "discard-owner-marker",
    "reviewImageUrls": [
      "https://example.invalid/discard-image"
    ]
  },
  {
    "text": "The visit was acceptable, but service speed varied considerably.",
    "stars": 3,
    "publishedAtDate": "2026-07-18T09:30:00.000Z",
    "title": "Test Cafe",
    "placeId": "ChIJFixturePlace",
    "url": "https://www.google.com/maps/place/Test+Cafe"
  },
  {
    "text": "The order was incorrect and the issue was not resolved.",
    "stars": 1,
    "publishedAtDate": "2026-07-16T08:15:00.000Z",
    "title": "Test Cafe",
    "placeId": "ChIJFixturePlace",
    "url": "https://www.google.com/maps/place/Test+Cafe"
  }
]
```

Do not change `backend/app/imports/apify.py`; its existing body is already
unfiltered and approved.

- [ ] **Step 5: Run focused tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_adapters tests.test_import_normalizer
```

Expected: PASS. The decoded and normalized rating order is `[5, 3, 1]` for
both provider contracts.

- [ ] **Step 6: Review and commit Task 2**

Run:

```powershell
git diff --check
git diff -- tests/fixtures/apify_google_maps_reviews.json tests/test_import_adapters.py tests/test_import_normalizer.py
```

Commit:

```powershell
git add tests/fixtures/apify_google_maps_reviews.json tests/test_import_adapters.py tests/test_import_normalizer.py
git commit -m "test: preserve mixed provider ratings"
```

---

### Task 3: Preserve Cache and Historical Provider Compatibility

**Files:**
- Modify: `tests/test_import_cache.py`
- Modify: `tests/test_history.py`

**Interfaces:**
- Consumes: `CacheIdentity(platform, provider, contract_version, source_hash, requested_limit, ordering)`.
- Consumes: existing `HistoryStore.save`, `HistoryStore.list_runs`, and `HistoryStore.get`.
- Produces: Explicit evidence that the new Automation Lab cache identity does not reuse Axesso entries and old Axesso/Outscraper reports still round-trip unchanged.

- [ ] **Step 1: Add the cache-isolation test**

Add to `tests/test_import_cache.py`:

```python
def test_automation_lab_identity_does_not_reuse_historical_axesso_entry(self):
    """Start the replacement Actor with a fresh cache namespace."""

    axesso = CacheIdentity(
        "amazon",
        "apify_axesso_amazon",
        "1",
        "B000000000",
        20,
        "most_relevant",
    )
    automation_lab = CacheIdentity(
        "amazon",
        "apify_automation_lab_amazon",
        "1",
        "B000000000",
        20,
        "most_relevant",
    )
    self.store.put(axesso, collection(), NOW, NOW + timedelta(days=30))

    self.assertIsNotNone(self.store.get(axesso, NOW))
    self.assertIsNone(self.store.get(automation_lab, NOW))
```

- [ ] **Step 2: Add historical Axesso compatibility beside Outscraper**

Add to `tests/test_history.py`:

```python
def test_historical_axesso_reports_round_trip_with_stable_provenance(self):
    """Keep old Axesso labels readable after the active Actor changes."""

    run_id = self.store.save(
        make_report(
            title="Amazon product B000000000",
            platform="amazon",
            provider="Apify (Axesso)",
        )
    )

    item = self.store.list_runs()[0]
    restored = self.store.get(run_id)

    self.assertEqual(
        (item.platform, item.provider),
        ("amazon", "Apify (Axesso)"),
    )
    self.assertEqual(
        (restored.source.platform, restored.source.provider),
        ("amazon", "Apify (Axesso)"),
    )
```

Do not remove or rewrite
`test_historical_outscraper_reports_round_trip_with_stable_provenance`.

- [ ] **Step 3: Run compatibility tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_cache tests.test_history
```

Expected: PASS. These are characterization tests for existing generic cache
and history boundaries; no production migration or implementation change is
expected.

- [ ] **Step 4: Review and commit Task 3**

Run:

```powershell
git diff --check
git diff -- tests/test_import_cache.py tests/test_history.py
```

Commit:

```powershell
git add tests/test_import_cache.py tests/test_history.py
git commit -m "test: preserve historical Amazon provenance"
```

---

### Task 4: Update Active Provider and Diversity Documentation

**Files:**
- Modify: `tests/test_import_documentation.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`

**Interfaces:**
- Consumes: approved Actor identity, exact request, observed Free-plan pricing, natural-diversity policy, and live-test approval gate.
- Produces: Active operator documentation with no Axesso setup claim while explicitly preserving historical Axesso and Outscraper provenance.

- [ ] **Step 1: Write failing documentation audits**

In `tests/test_import_documentation.py`, replace active Axesso requirements
with:

```python
for required in (
    "automation-lab/amazon-reviews-scraper",
    "compass/google-maps-reviews-scraper",
    "$0.01",
    "$2.00 per 1,000",
    "$0.03",
    "$0.05",
    "$0.11",
    "$0.21",
    'sort: "helpful"',
    'reviewsSort: "mostRelevant"',
    "no star-rating filter",
    "pricing and availability can change",
    "provider-side retention",
    "Apify (Axesso)",
    "Outscraper",
):
    with self.subTest(required=required):
        self.assertIn(required, readme)
```

For the combined `docs/architecture.md` and `docs/project_status.md` audit,
require:

```python
for required in (
    "automation-lab/amazon-reviews-scraper",
    "compass/google-maps-reviews-scraper",
    "apify_automation_lab_amazon",
    "10/20/50/100",
    'sort: "helpful"',
    'reviewsSort: "mostRelevant"',
    "provider order",
    "first 40",
    "fixture",
    "no Amazon or Google account credentials",
):
    with self.subTest(required=required):
        self.assertIn(required, combined)
```

Retain assertions that `.env.example` contains only a blank
`APIFY_API_TOKEN`, and add:

```python
self.assertNotIn(
    "axesso_data/amazon-reviews-scraper",
    readme,
)
```

Do not globally ban `Apify (Axesso)` or `Outscraper`; documentation must name
them when explaining preserved historical provenance.

- [ ] **Step 2: Run the documentation test to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_documentation
```

Expected: FAIL on the old Actor, old cost estimates, and missing diversity
language.

- [ ] **Step 3: Update `README.md`**

Replace the active Amazon provider line with:

```markdown
- **Amazon:** ReviewInsight calls public Actor
  [`automation-lab/amazon-reviews-scraper`](https://apify.com/automation-lab/amazon-reviews-scraper)
  for one validated `amazon.com` ASIN. It requests `sort: "helpful"` and does
  not send a star-rating, keyword, or positive-only filter.
```

Keep the Google Actor line and add:

```markdown
Google Maps keeps `reviewsSort: "mostRelevant"` and sends no rating filter.
Both providers return their own ranked order; ReviewInsight preserves that
order and every usable review up to the selected limit. It does not rearrange
or discard usable reviews to manufacture sentiment balance, so a real source
can still be uniform or contain fewer reviews than requested.
```

Replace Axesso pricing estimates with:

```markdown
Automation Lab's Free-plan Console pricing observed on July 23, 2026 is
`$0.01` per run start plus `$2.00 per 1,000` reviews (`$0.002` per review),
with platform usage included. Approximate maximum event costs for imports of
10, 20, 50, and 100 reviews are `$0.03`, `$0.05`, `$0.11`, and `$0.21`.
Provider pricing and availability can change.
```

Update privacy copy to name Automation Lab instead of Axesso. Preserve:

```markdown
Historical saved reports labeled `Apify (Axesso)` or `Outscraper` remain
readable with their original provenance.
```

- [ ] **Step 4: Update `docs/architecture.md`**

Document the active Amazon adapter:

```markdown
`ApifyAmazonReviewsAdapter` calls
`automation-lab/amazon-reviews-scraper` with one ASIN, marketplace `US`, the
selected `maxReviewsPerProduct`, and `sort: "helpful"`. Its provider key is
`apify_automation_lab_amazon`. No star or keyword filter is sent.
```

Document the unchanged Google behavior:

```markdown
`ApifyGoogleMapsAdapter` keeps `reviewsSort: "mostRelevant"` and sends no
rating filter. Both adapters preserve provider order through the shared
normalizer.
```

Retain cache, refresh, privacy, 40-review analysis, error, and historical
compatibility boundaries.

- [ ] **Step 5: Update `docs/project_status.md`**

Replace the active Axesso milestone status with:

```markdown
Amazon imports use `automation-lab/amazon-reviews-scraper` through the existing
replaceable adapter boundary. Amazon requests helpful reviews without a
sentiment filter; Google Maps requests most-relevant reviews without a rating
filter. Mixed fixture coverage proves 5-, 3-, and 1-star reviews remain in
provider order.
```

State that all automated verification is fixture-only and that live provider
smoke verification still requires explicit user approval.

- [ ] **Step 6: Run documentation and repository audits**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_import_documentation
rg -n "axesso_data/amazon-reviews-scraper|apify_axesso_amazon|Axesso currently|Axesso cost" README.md docs/architecture.md docs/project_status.md .env.example
rg -n "OUTSCRAPER_API_KEY|Outscraper account" README.md docs/architecture.md docs/project_status.md .env.example
```

Expected:

- documentation tests PASS;
- no active Axesso Actor/key/cost references;
- no active Outscraper credential or account setup;
- historical `Apify (Axesso)` and `Outscraper` compatibility text remains.

- [ ] **Step 7: Review and commit Task 4**

Run:

```powershell
git diff --check
git diff -- README.md docs/architecture.md docs/project_status.md tests/test_import_documentation.py
```

Commit:

```powershell
git add README.md docs/architecture.md docs/project_status.md tests/test_import_documentation.py
git commit -m "docs: document Automation Lab review imports"
```

---

### Task 5: Full Offline Verification and Review Gate

**Files:**
- Review only: all files changed since design commit `e95e229`

**Interfaces:**
- Consumes: the complete implementation from Tasks 1–4.
- Produces: fresh evidence for tests, compilation, diff quality, requirements coverage, and pre-merge review.

- [ ] **Step 1: Run every focused import test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_import_adapters `
  tests.test_import_policy `
  tests.test_import_normalizer `
  tests.test_import_service `
  tests.test_import_cache `
  tests.test_import_api `
  tests.test_import_models `
  tests.test_import_documentation
```

Expected: PASS with zero failures/errors and no live HTTP.

- [ ] **Step 2: Run dashboard, analysis, report, history, and demo regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_dashboard_mvp `
  tests.test_api_mvp `
  tests.test_service_mvp `
  tests.test_history `
  tests.test_demo_data
```

Expected: PASS. Imported collections still show up to 100 reviews, analysis
submits only the first 40, partial-analysis disclosure remains, and history
restores old provider labels.

- [ ] **Step 3: Prove tests and application code contain no accidental live path**

Run:

```powershell
rg -n "requests\\.(get|post)|httpx\\.|urlopen|ApifyClient" tests
rg -n "automation-lab|compass|amazon\\.com|google\\.com" tests
```

Inspect every match. Expected: provider network boundaries in tests use
`FakeSession`, `Mock`, saved fixtures, or temporary storage; no test can spend
quota.

- [ ] **Step 4: Run the full repository test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_*.py
```

Expected: all tests PASS. Bare-mode Streamlit `ScriptRunContext` warnings are
known test-runner noise; there must be zero failures and zero errors.

- [ ] **Step 5: Run compile and diff checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
git diff --check main...HEAD
git status --short
git diff --stat main...HEAD
git diff main...HEAD
```

Expected:

- compile command exits `0`;
- diff check prints nothing;
- only approved code, fixtures, tests, and documentation are changed;
- `review_intelligence_flow.png` is absent from the diff.

- [ ] **Step 6: Request a pre-merge code review**

Use `superpowers:requesting-code-review` against:

```text
Base: main
Head: current feature branch
Requirements: docs/superpowers/specs/2026-07-23-automation-lab-amazon-diverse-reviews-design.md
Plan: docs/superpowers/plans/2026-07-23-automation-lab-amazon-diverse-reviews.md
```

The reviewer must verify:

- exact four-field Amazon input;
- no positive-only filter in either adapter;
- 5-/3-/1-star order preservation;
- safe error and privacy boundaries;
- new provider/cache identity;
- historical Axesso and Outscraper compatibility;
- no live tests;
- no unrelated diagram change.

Fix every Critical or Important finding with a new red-green test cycle, then
rerun Steps 1–5 and request re-review.

- [ ] **Step 7: Stop before live smoke testing**

Report offline results and ask the user for explicit approval before calling
either Actor. State the maximum selected-limit cost using current observed
pricing. Do not infer approval from the implementation request.

If the user explicitly approves later, perform at most:

```text
1 Amazon import for one product with varied public ratings
1 Google Maps import for one place with varied public ratings
```

Use the smallest useful limit first, do not refresh repeatedly, inspect actual
ratings/counts/provider order, and report the exact runs and observed cost.

- [ ] **Step 8: Commit review-driven changes, if any**

If review required changes:

```powershell
git add backend/app/imports/apify_amazon.py tests/fixtures tests/test_import_adapters.py tests/test_import_policy.py tests/test_import_normalizer.py tests/test_import_cache.py tests/test_history.py tests/test_import_documentation.py README.md docs/architecture.md docs/project_status.md
git commit -m "fix: address Automation Lab import review"
```

If no files changed, do not create an empty commit.

- [ ] **Step 9: Finish the branch only after the live-test gate is resolved**

Use `superpowers:finishing-a-development-branch`. The user previously asked
for completed code to be merged to `main` and pushed, but do not merge until:

- offline verification is green;
- pre-merge review is clear;
- the user either approves the optional live smoke test and it is complete, or
  explicitly declines/skips it.

After merging, rerun the full test suite on `main`, verify `main` matches
`origin/main`, and push without force.
