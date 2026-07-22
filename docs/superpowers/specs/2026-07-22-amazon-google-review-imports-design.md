# Amazon and Google Maps Review Imports Design

## Goal

Add a small, local proof of concept that imports real written reviews from an
Amazon product URL or a Google Maps place URL, lets the user inspect the
normalized evidence, and then sends that evidence through the existing Groq
analysis and SQLite report-history pipeline.

The first version uses Outscraper for Amazon and Apify's Compass Google Maps
Reviews Scraper for Google Maps. Both integrations are backend-only,
unofficial scraping services. End users provide only a public product or place
URL; they never provide an Amazon or Google account, browser cookie, session
token, or other source-site credential.

## Confirmed scope

The first milestone supports:

- one platform and one public URL per import;
- `amazon.com` product URLs with limits of 5, 10, or 12 written reviews;
- Google Maps place URLs with limits of 5, 10, or 20 written reviews;
- provider-backed import only after an explicit user action;
- a local normalized-result cache and an explicit refresh action;
- the actual number of usable reviews returned, even when it is below the
  requested limit;
- visible platform, provider, original-source, cache, and retrieval-time
  provenance;
- the existing evidence review, Groq analysis, metrics, report, and history
  flow; and
- fixture- and fake-backed automated tests that never spend provider or Groq
  quota.

The milestone does not add multi-product batches, arbitrary Amazon
marketplaces, application-managed pagination, background refreshes, schedules,
jobs, queues, webhooks, user accounts, cloud deployment, provider selection in
the UI, reviewer profiles, media, owner responses, or a universal scraping
framework.

## Chosen provider split

### Amazon: Outscraper Amazon Reviews API

Outscraper's `GET /amazon-reviews` endpoint accepts an Amazon product URL or
ASIN, has a documented maximum of 12 reviews per query, and supports a
synchronous response. The published free tier includes the first 500 Amazon
reviews in each 30-day pricing period and lists API access. Published paid
pricing begins at $2 per 1,000 reviews after the first 500 and drops to $1 per
1,000 after 5,000.

This is a good fit for the first milestone because its provider limit is
already close to ReviewInsight's desired evidence size. The application will
use `async=false`, request only one product, and never paginate. It will send
the backend-only `OUTSCRAPER_API_KEY` in the provider header and will not
accept or forward Amazon credentials, cookies, or session data.

Provider references, checked July 22, 2026:

- [Outscraper Amazon Reviews endpoint](https://docs.outscraper.com/endpoints/amazon-reviews/)
- [Outscraper Amazon Reviews pricing](https://outscraper.com/amazon-reviews-scraper/)

### Google Maps: Apify Compass Google Maps Reviews Scraper

The `compass/google-maps-reviews-scraper` Actor accepts Google Maps place URLs,
supports a maximum-review input, and exposes a synchronous Apify API endpoint
that returns dataset items. At the time of this design, the Actor is maintained
by Apify, is rated 4.8, and advertises pricing from $0.30 per 1,000 scraped
reviews. Apify's free plan supplies $5 of non-rollover monthly platform credit,
requires no payment card, and blocks further free-plan usage when the credit is
exhausted.

The application will call the synchronous dataset-items endpoint for one place
with at most 20 reviews. The backend-only `APIFY_API_TOKEN` will be sent in an
authorization header rather than placed in a user-visible form or application
log. The first version will not poll asynchronous runs, schedule Actors, or
retain provider output intentionally after normalization.

Provider references, checked July 22, 2026:

- [Compass Google Maps Reviews Scraper and API](https://apify.com/compass/google-maps-reviews-scraper/api)
- [Apify plan and platform pricing](https://apify.com/pricing)
- [Apify storage retention](https://docs.apify.com/storage)

### Why the other evaluated options are not selected

- OpenWeb Ninja offers 100 free Amazon requests per month with no card, but its
  anonymous top-reviews endpoint now returns only eight reviews. Deeper review
  access requires an Amazon session cookie, which is outside the approved
  security and UX boundary.
- RapidAPI's OpenWeb Ninja listing exposes the same limits behind an additional
  marketplace and bandwidth boundary. Other Amazon review listings have lower
  or less stable free allowances.
- Outscraper publishes an attractive 500-review Google Maps free tier and a
  documented reviews endpoint, but its current pricing table only explicitly
  lists API access on the paid Google Maps Reviews tiers. It remains the first
  Google fallback to live-evaluate if the Apify Actor becomes unsuitable.
- The official Google Places API is limited to a maximum of five reviews.
  Requesting reviews uses the Place Details Enterprise + Atmosphere SKU, which
  currently has 1,000 free monthly events and then starts at $25 per 1,000.
  More importantly, official Places content carries Google branding, author
  attribution, source-link, ordering-disclosure, and caching/storage rules that
  conflict with ReviewInsight's current cached evidence and full-report history
  model. It is therefore not a drop-in adapter replacement.

## Architecture

The existing staged boundary remains intact:

```text
Streamlit
  -> GET /api/import/options
  -> POST /api/import
       -> ReviewImportService
            -> platform URL policy
            -> ImportCacheStore
            -> provider adapter registry
                 amazon      -> OutscraperAmazonAdapter
                 google_maps -> ApifyGoogleMapsAdapter
            -> shared review normalizer
       <- CollectionResult
  -> user inspects normalized evidence
  -> POST /api/analyze
       -> existing Groq validation and analysis
       -> existing deterministic metrics
       -> existing SQLite report history
```

Collection and analysis stay separate. `backend.app.service.run_analysis`
continues to accept only a validated `CollectionResult`; it will not know about
platform selection, provider credentials, caching, URLs, or upstream response
shapes.

### Component responsibilities

#### ReviewImportService

The import service owns one import transaction. It validates platform policy,
builds the cache key, returns an existing cache entry unless refresh was
explicitly requested, selects the configured adapter from a registry, invokes
it once, normalizes its provider-neutral result, requires at least two usable
reviews, writes the normalized cache entry, and returns `CollectionResult`.

The service depends only on the adapter protocol, cache-store protocol, URL
policy, and shared Pydantic models. Tests can replace every dependency with a
fake.

#### Provider adapters

Every adapter implements the same narrow contract:

```text
provider_key
platform
allowed_limits
fetch(source_url, limit) -> ProviderImportResult
```

`ProviderImportResult` contains a provider-neutral source title, original or
canonical source URL, stable source key when available, and candidate reviews.
Candidate reviews may contain provider review ID, title, body, rating, and date;
they never need author, avatar, profile, media, or account identifiers.

Adapters own credential lookup, provider request construction, response-shape
decoding, and upstream-status classification. They do not use SQLite, invoke
Groq, render UI, or return raw provider exceptions or bodies.

#### Adapter registry

The application composition root maps `amazon` and `google_maps` to adapter
instances. The import service and API route depend on the protocol rather than
concrete provider classes. Replacing a provider requires adding a new adapter,
registering it for the platform, updating its environment documentation and
fixtures, and adjusting platform limits only if the replacement cannot support
the existing choices.

The cache key contains the adapter's provider key and cache-contract version.
Changing provider or normalization semantics therefore cannot accidentally
reuse evidence fetched through an older adapter.

#### ImportCacheStore

Import caching uses a separate standard-library SQLite database at
`data/review_import_cache.db`. Keeping it separate from
`data/review_history.db` prevents transient provider-cache concerns from
changing the atomic report-history boundary.

The cache stores only validated, normalized collection JSON plus:

- platform;
- provider key and cache-contract version;
- normalized source-key hash;
- requested limit and ordering;
- fetched-at timestamp; and
- expiry timestamp.

It never stores provider credentials, request headers, raw response bodies,
reviewer names, profile links, avatars, media, owner responses, or provider run
logs.

## Public API contracts

### `GET /api/import/options`

Returns the platform labels and limits currently supported by the registered
adapters. The dashboard uses this response to populate its source and limit
controls without importing provider modules or hardcoding provider names.

Example shape:

```json
{
  "platforms": [
    {"key": "amazon", "label": "Amazon product", "limits": [5, 10, 12]},
    {"key": "google_maps", "label": "Google Maps place", "limits": [5, 10, 20]}
  ]
}
```

The endpoint exposes no credential status, token, internal endpoint, or
provider-specific request parameter.

### `POST /api/import`

Request:

```json
{
  "platform": "amazon",
  "url": "https://www.amazon.com/dp/B000000000",
  "limit": 10,
  "refresh": false
}
```

`platform` is restricted to registered platform keys. `limit` must be one of
the platform's advertised values. `refresh` defaults to false and is the only
way to bypass an existing live cache entry.

The response remains the existing `CollectionResult`, with richer source
provenance. `SourceInfo` gains backward-compatible fields with defaults for
older history rows:

- `platform`: `generic`, `amazon`, `google_maps`, or `demo`;
- `provider`: public provider label or `null`;
- `requested_count`: requested review limit or `null`;
- `retrieved_count`: actual normalized review count;
- `retrieved_at`: provider-fetch timestamp or `null`;
- `cache_status`: `not_applicable`, `miss`, `hit`, or `refresh`.

Provider-backed sources use a generic `provider_api` extractor value rather
than embedding a vendor in the extractor enum. This keeps extraction method,
platform, and provider as separate concepts.

The original public URL remains in `SourceInfo.url`. The UI treats
`len(reviews)` as the authoritative number available for evidence and analysis;
`retrieved_count` must equal that length.

### Existing endpoints

- `POST /api/collect` remains available for the current generic static
  JSON-LD/HTML flow but is no longer used for the Amazon/Google source choices.
- `GET /api/demo`, `POST /api/analyze`, and the history endpoints retain their
  staged responsibilities.
- Analysis requests still accept only source metadata and two to forty
  normalized reviews. They never accept provider selection or credentials.

## URL policy and source identity

The API rejects embedded credentials, fragments irrelevant to identity, and
platform/host mismatches before spending provider quota.

Amazon version one accepts only HTTPS `amazon.com` product URLs containing a
valid 10-character ASIN in a recognized `/dp/`, `/gp/product/`, or equivalent
product path. Search, category, seller, review-detail, shortened, and arbitrary
Amazon URLs are rejected. The ASIN is the cache source key. Supporting other
Outscraper-documented Amazon domains is a later policy extension, not an
adapter redesign.

Google Maps version one accepts HTTPS place URLs on `google.com`,
`maps.google.com`, and `maps.app.goo.gl` when the path is recognizably Maps- or
place-related. It does not accept free-text place queries. Before provider
output is available, the normalized URL hash is the cache source key. If the
provider returns a stable place ID, it is retained only as non-personal source
provenance. The first milestone has no cache-alias subsystem: cache identity
remains the normalized input URL hash, so two different valid URLs for the same
place may produce separate cache entries and provider requests.

Provider adapters receive only a URL that has passed the platform allowlist.
Although the backend does not fetch that URL directly, allowlisting prevents an
arbitrary value from being forwarded with a privileged provider token.

## Normalization

Both adapters feed candidate reviews into one normalizer so provider changes do
not alter the Groq evidence contract.

The normalizer:

1. collapses whitespace;
2. combines a non-duplicate review title with the body using a clear separator;
3. drops missing bodies and text shorter than ten characters;
4. caps text at the existing 5,000-character schema boundary;
5. accepts only unambiguous integer ratings from one through five;
6. converts an unambiguous date to ISO `YYYY-MM-DD`, otherwise leaves the date
   absent rather than guessing;
7. deduplicates exact case-insensitive normalized text;
8. applies the requested limit after normalization; and
9. assigns local sequential IDs (`r1`, `r2`, and so on) rather than persisting
   provider or reviewer identifiers.

At least two normalized written reviews are required. A provider may return
fewer usable reviews than requested; that is a success when at least two remain,
and the UI must show the actual count. Star-only ratings do not become reviews.

## Cache and explicit refresh behavior

Cache retention is 30 days for this local POC. A cache entry is live until its
expiry timestamp and is removed lazily during cache reads or writes; there is
no background cleanup process.

- First **Import reviews** for a cache key: one provider fetch, cache status
  `miss`.
- Repeated **Import reviews** before expiry: no provider request, cache status
  `hit`.
- **Refresh from source**: exactly one provider fetch even when a live cache
  entry exists; successful normalized evidence atomically replaces the entry
  and reports cache status `refresh`.
- Failed refresh: preserve and continue displaying the previous collection in
  Streamlit state and leave the existing cache entry unchanged.
- Import after expiry: the user's explicit import action performs one new
  provider fetch and replaces the expired entry.
- Different platform, source, limit, ordering, provider, or cache-contract
  version: distinct cache key.

The first version always requests the provider's most-relevant/default order.
There is no sorting UI, which avoids multiplying cache entries and quota use.

## Estimated free-tier usage and spend control

The application controls spend through per-request caps, caching, one-source
requests, no pagination, no background work, and explicit refresh. It does not
attempt to reproduce provider billing totals or add an application-side monthly
quota ledger in the first milestone.

For Amazon, 20 uncached or refreshed imports at the normal 10-review choice use
about 200 of Outscraper's published 500 free reviews per 30-day period. At the
maximum 12-review choice, the complete free allowance supports 41 full imports
with eight reviews left. Cache hits consume no provider reviews.

For Google Maps, 20 maximum-size refreshes use at most 400 reviews. At the
Actor's advertised $0.30 per 1,000-review price, the review-event portion is
about $0.12. Even 100 maximum-size refreshes would be about $0.60 for 2,000
review events, leaving most of Apify's $5 monthly free credit for run, storage,
and other platform charges. These are planning estimates, not billing
guarantees; Actor and platform prices can change.

Operators should keep Outscraper in a non-overage or prepaid configuration and
use Apify's free-plan hard stop during the POC. The documentation must instruct
operators to check current provider pricing before enabling the integration.

## Credentials and secrets

The repository-root `.env` may define:

```dotenv
OUTSCRAPER_API_KEY=
APIFY_API_TOKEN=
```

Existing process-environment precedence remains unchanged. Neither value is
accepted by an API request, stored in SQLite, returned in an error, rendered in
Streamlit, included in a cache key, or logged. Each adapter reads only its own
credential when it is actually selected for a cache miss or refresh. A cache
hit can succeed without contacting or validating the provider.

The application does not request or use `AMAZON_USERNAME`, `AMAZON_PASSWORD`,
Amazon cookies, Google credentials, Google cookies, browser profiles, or
session tokens.

## Failure handling

Provider and cache failures use a small application-owned vocabulary:

| Code | HTTP status | Meaning |
|---|---:|---|
| `invalid_import_url` | 422 | URL does not match the selected platform policy. |
| `unsupported_import_platform` | 422 | Platform is not one of the supported values. |
| `unsupported_import_limit` | 422 | Limit is not advertised for that platform. |
| `missing_provider_key` | 400 | The selected backend provider credential is absent. |
| `provider_auth_failed` | 401 | The provider rejected the backend credential. |
| `provider_quota_exhausted` | 429 | Free credit, quota, or configured spending capacity is exhausted. |
| `no_reviews` | 422 | Fewer than two usable written reviews remain after normalization. |
| `provider_response_invalid` | 502 | A successful upstream response does not match the adapter contract. |
| `import_failed` | 502 | The provider could not complete the import safely. |
| `provider_unavailable` | 503 | The provider is temporarily unavailable or rate limited without a definitive quota response. |
| `import_timeout` | 504 | The bounded provider request did not finish. |
| `cache_failed` | 500 | The local import cache could not be read or updated. |

Outscraper and Apify status codes are mapped inside their adapters. Raw response
bodies, task logs, provider request IDs, authorization headers, exception text,
and tracebacks never cross the FastAPI boundary. Unknown adapter codes map to
the generic `import_failed` envelope.

Provider calls use bounded connect and read timeouts. Outscraper's small
synchronous request receives a shorter budget; the synchronous Apify Actor run
receives up to 60 seconds. The dashboard import request budget is slightly
longer than the backend's maximum provider budget. There are no automatic
retries in version one because a retry can spend quota or create a second Actor
run. The user can explicitly retry or refresh.

A failed initial import leaves no collection. A failed refresh preserves the
currently displayed evidence and tells the user it was not replaced. Groq is
never invoked by an import action. Analysis failure continues to preserve the
imported evidence under the existing behavior.

## Dashboard flow

The opening workspace changes from a generic URL-only form to:

1. **Review source** selector populated from `/api/import/options`.
2. Platform-specific URL label and example placeholder.
3. **Review limit** selector populated from the selected platform's advertised
   limits.
4. Primary **Import reviews** action.
5. Existing explicit **Use bundled demo data** action.

After a successful import, the evidence workspace shows:

- source title;
- original clickable URL;
- `Amazon via Outscraper` or `Google Maps via Apify`;
- `Retrieved X usable written reviews - Requested Y`;
- fetched-at time; and
- `Fresh import`, `Cached result`, or `Explicit refresh` status.

The evidence table and **Analyze with Groq** action retain their current roles.
A secondary **Refresh from source** action appears only for provider-backed
collections. Selecting it clearly warns that it contacts the provider and may
consume free-tier usage. It never triggers automatically when the page loads,
history refreshes, a report is loaded, or Streamlit reruns.

Loaded history reports display their saved source, provider, requested and
actual counts, and original URL. They do not offer refresh because history is a
saved analysis snapshot; the user must return to the import workspace to fetch
new evidence.

## Report history and schema compatibility

Successful analyses continue to persist their normalized review evidence in
`data/review_history.db`. History therefore remains an analysis snapshot and is
not served from the transient import cache.

The history summary schema gains nullable `platform` and `provider` columns so
the sidebar can distinguish Amazon, Google Maps, generic static, and demo runs
without parsing every report JSON document. Schema initialization performs
idempotent additive migration for existing databases. Existing rows remain
loadable through default source-provenance values; no destructive migration or
history rewrite is permitted.

Provider replacement does not rewrite old reports. A report imported through
Outscraper remains labeled as Outscraper even if a later Amazon adapter changes.

## Terms, attribution, privacy, and storage caveat

Outscraper and the Apify Actor are unofficial services that retrieve public
content from Amazon and Google Maps. Their availability does not grant
ReviewInsight additional rights to copy, analyze, retain, redistribute, or
commercialize source content. Amazon's conditions restrict automated data
mining and extraction, and Google Maps' end-user terms restrict copying, mass
downloads, and bulk feeds. The legal effect depends on jurisdiction and use;
the application documentation must not claim that scraping is categorically
permitted.

Relevant source-platform references, checked July 22, 2026:

- [Amazon Conditions of Use](https://www.amazon.com/gp/help/customer/display.html?nodeId=GLSBYFE9MGKKQXXM)
- [Google Maps Additional Terms](https://maps.google.com/help/terms_maps/?refresh=1)

The UI and README must state that:

- imports use an unofficial scraping provider;
- users are responsible for ensuring their use and retention are permitted;
- the POC is intended for small, local evaluation rather than redistribution;
- review text is sent to Groq when analysis is explicitly started; and
- raw provider datasets, reviewer identity, and media are deliberately not
  retained by ReviewInsight.

Visible provenance uses `Amazon via Outscraper` and `Google Maps via Apify`,
retains the original source URL, and never implies that Amazon or Google
endorses ReviewInsight. Source and provider labels appear before analysis, in
the report hero, supporting evidence, and history.

Review text may itself contain names or other personal information even after
reviewer metadata is discarded. The local cache is limited to 30 days, but
successful report history retains normalized evidence until the operator
deletes the local history database. Production use would require explicit
retention controls, deletion UI, privacy terms, and a legal review; those are
outside this POC.

Apify may retain actor run and dataset data under its own plan retention policy.
The adapter should request only the fields needed by ReviewInsight. The first
milestone will not attempt programmatic deletion of provider-side runs or
datasets; provider-side retention is documented as an operator concern, and an
operator may manually delete retained Apify data when needed.

## Provider replacement analysis

### Replacing Outscraper for Amazon

A replacement implements the adapter protocol and maps its response to
`ProviderImportResult`. The API route, cache store, normalizer, Groq service,
report rendering, and history store remain unchanged. The registry and
credential documentation change. If the new provider supports fewer than 12
reviews, its `allowed_limits` changes and `/api/import/options` automatically
drives the UI.

OpenWeb Ninja is technically straightforward but would advertise at most five
and eight reviews under the no-cookie rule. An Apify Amazon Actor could support
larger limits but introduces Actor run and dataset behavior similar to the
Google adapter.

### Replacing Apify for Google Maps

Outscraper can implement the same protocol with a direct Google Maps Reviews
endpoint. The registry, provider credential, fixtures, timeout, and failure
mapping change; the application-facing collection and report contracts do not.
Its free API entitlement must be confirmed before selection.

The official Google Places API is not a transparent transport swap. A compliant
official adapter would lower the maximum to five and require a source policy
that disables or redesigns persistent caching and raw-review history while
adding Google branding, author attribution, per-review Google Maps links, and
ordering disclosures. The adapter boundary localizes data retrieval, but terms
and display policy intentionally remain explicit application concerns.

## Testing strategy

All automated tests use saved provider fixtures and fake HTTP sessions. Test
discovery, CI, and ordinary local verification make no Outscraper, Apify,
Amazon, Google Maps, or Groq request.

### Model and policy tests

- Accept only registered platforms and their advertised limits.
- Reject platform/URL mismatches, embedded credentials, unsupported Amazon
  paths, non-place Google URLs, and free-text queries.
- Preserve backward-compatible generic and demo source provenance.
- Require `retrieved_count == len(reviews)` and at least two reviews.

### Adapter contract tests

- Assert exact provider endpoint, method, authentication header, timeout, and
  one-source limit payload.
- Prove no cookie, session, browser-profile, or end-user credential field is
  sent.
- Normalize representative Outscraper Amazon and Apify Google fixture
  responses.
- Cover fewer results than requested, duplicates, star-only entries, missing
  text, malformed ratings/dates, oversized text, and provider schema drift.
- Prove reviewer names, IDs, avatars, profiles, media, owner responses, raw
  bodies, and secrets never enter the normalized result.
- Map authentication, quota, rate-limit, timeout, unavailable, malformed, and
  unknown failures to exact safe errors.

### Cache tests

- First import calls the adapter once and atomically saves one validated entry.
- Live cache hit calls no adapter and reports the original fetch time.
- Explicit refresh calls exactly once and atomically replaces the entry.
- Failed refresh leaves the old cache entry intact.
- Expired and corrupt entries are handled safely.
- Platform, source, limit, ordering, provider, and cache-contract version
  isolate cache entries.
- Cache JSON contains no credential or reviewer-identity marker.

### API tests

- Options reflect the registered adapters without exposing provider internals.
- Import passes the exact validated request once to the service.
- Import never calls analysis or report history.
- Every public failure code maps to the documented status and safe message.
- Existing collect, demo, analysis, and history routes keep their behavior.

### Dashboard tests

- Source and limit controls come from import options.
- Import and demo remain separate explicit actions.
- Actual count, requested count, original source, provider, fetched time, and
  cache status are visible before analysis and in saved reports.
- Refresh appears only for provider imports, warns about usage, and never runs
  on a passive rerun.
- Failed refresh preserves displayed evidence.
- Analyze submits only the displayed normalized source and reviews.

### History and documentation tests

- Existing history databases migrate additively and older reports still load.
- Amazon and Google reports round-trip with stable historical provider labels.
- Current documentation lists both backend provider variables, free-tier
  estimates, unofficial-service caveats, cache retention, and fixture-only
  testing.
- Source audits reject credential inputs, cookies, session-token fields, and
  retired direct-source scraping claims.

An optional manual smoke checklist may exercise one known Amazon product URL
and one Google Maps place URL after the operator configures provider keys. It is
never part of automated tests and must use the smallest limits.

## Main files and areas expected to change during implementation

- `backend/app/models.py`: import request/options and richer source provenance.
- New `backend/app/imports/` package: adapter protocol, registry, URL policy,
  normalizer, Outscraper adapter, Apify adapter, and import service.
- New `backend/app/import_cache.py`: isolated SQLite cache.
- `backend/app/main.py`: import options and import endpoints plus safe errors.
- `backend/app/history.py`: additive platform/provider summary migration.
- `dashboard/api_client.py`: options/import client calls and timeouts.
- `dashboard/streamlit_app.py`: platform-aware form, provenance, cache state,
  and explicit refresh interaction.
- `.env.example`, `README.md`, `docs/architecture.md`, and
  `docs/project_status.md`: setup, provider limits, usage, caveats, and current
  scope.
- New Amazon and Google provider fixture files plus focused model, adapter,
  cache, API, dashboard, history, and documentation tests.

The Groq analyzer, deterministic metrics, supervisor topology, and report
visualization logic should change only where richer source provenance must be
displayed or documented.

## Acceptance criteria

- A user can select Amazon or Google Maps, paste an allowed URL, select a small
  limit, import reviews, inspect actual normalized evidence, and analyze it
  through the existing Groq pipeline.
- Amazon imports use only Outscraper's backend API key; Google Maps imports use
  only Apify's backend token. No end-user source credentials, cookies, or
  sessions exist anywhere in the flow.
- The UI shows the original source, provider, requested count, actual usable
  count, fetch time, and cache status before analysis and in history.
- Repeated imports use the local cache; only first import, post-expiry import,
  or explicit refresh contacts a provider. No passive UI action spends quota.
- Per-request limits, no pagination, no retries, and no background work keep
  usage within the documented POC estimates.
- Provider adapters are independently testable and replaceable without changes
  to Groq analysis, deterministic metrics, report history payloads, or report
  rendering contracts.
- Provider, source-platform, attribution, storage, and terms caveats are visible
  and accurately documented without claiming official endorsement or blanket
  legal permission.
- Automated tests use fixtures and fakes only, preserve all existing coverage,
  and pass without configured provider or Groq credentials.
- No implementation begins until this design is reviewed and approved and a
  separate implementation plan is written.
