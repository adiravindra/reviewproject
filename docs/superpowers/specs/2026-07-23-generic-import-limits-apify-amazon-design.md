# Generic Import Limits and Apify Amazon Design

**Date:** 2026-07-23
**Status:** Approved for implementation planning

## Summary

ReviewInsight will use one generic source URL field and the same requested review
limits for Amazon and Google Maps: `10`, `20`, `50`, and `100`.

Amazon imports will move from Outscraper to Axesso Data's Apify Actor,
`axesso_data/amazon-reviews-scraper`. Google Maps will continue using
`compass/google-maps-reviews-scraper`. Both adapters will use the existing
backend-only `APIFY_API_TOKEN`.

This remains a small proof of concept. It will perform one bounded provider run
per cache miss or explicit refresh, retain only normalized review evidence, and
use fixtures and mocks for all automated tests.

## Goals

- Replace the platform-specific URL field label with `Source URL`.
- Use a generic placeholder that asks for an Amazon product or Google Maps place
  URL.
- Offer requested limits of `10`, `20`, `50`, and `100` for both platforms.
- Replace the Outscraper Amazon adapter with a replaceable Axesso Apify adapter.
- Preserve the existing import, evidence review, Groq analysis, report history,
  cache, refresh, and bundled demo flows.
- Continue displaying requested and actual retrieved counts because providers
  can return fewer written reviews than requested.
- Require no Amazon or Google credentials, cookies, browser state, or session
  tokens.

## Non-goals

- Bulk scraping, automatic pagination beyond the selected limit, background
  refresh, schedules, retries, or multi-product imports.
- Guaranteeing that Amazon returns the requested number of reviews.
- Collecting or displaying reviewer identities, profiles, avatars, images,
  owner responses, or raw provider responses.
- Supporting Amazon marketplaces other than `amazon.com` in this milestone.
- Integrating an Amazon open dataset.
- Changing the Groq analysis schema, report history model, or bundled demo.

## User experience

The dashboard retains the source selector because the selected platform controls
URL validation and adapter routing. The URL field will always use:

- label: `Source URL`;
- placeholder: `Paste an Amazon product or Google Maps place URL`.

The review-limit selector will be populated from the backend and will contain
`10`, `20`, `50`, and `100`. It will continue defaulting to the second option,
which becomes `20`.

After import, the dashboard will continue showing:

- platform and provider;
- original source URL;
- requested review count;
- actual normalized review count;
- retrieval time and cache status.

A request for 50 or 100 reviews is a ceiling, not a promise. When Amazon exposes
fewer anonymous written reviews, the import succeeds with the smaller actual
count as long as at least two usable reviews remain.

## Provider architecture

The existing `ReviewProviderAdapter` boundary remains unchanged. The registry
will contain:

```text
amazon      -> ApifyAmazonReviewsAdapter
google_maps -> ApifyGoogleMapsAdapter
```

Both adapters use `APIFY_API_TOKEN`, but each owns its Actor identifier, input
shape, response decoding, timeouts, and provider error mapping. No Actor task,
copy, schedule, webhook, or custom build is required.

The shared allowed-limit constant will be `10, 20, 50, 100`. Both adapters will
expose that constant through `allowed_limits`, and `GET /api/import/options`
will continue deriving its response from the registry rather than duplicating
limits in the dashboard.

## Amazon request mapping

The Amazon adapter will call:

```text
POST https://api.apify.com/v2/acts/axesso_data~amazon-reviews-scraper/run-sync-get-dataset-items
```

Authentication will use the existing bearer header. The adapter will extract the
ASIN from the already validated `amazon.com` URL and submit one Actor input item:

```json
{
  "input": [
    {
      "asin": "B000000000",
      "domainCode": "com",
      "sortBy": "helpful",
      "maxPages": 2
    }
  ]
}
```

`maxPages` will be `ceil(requested_limit / 10)`, bounded to `1..10`. Axesso
prices results per review and controls pagination internally. The adapter will
decode only product title, review title, review body, rating, and date. The
shared normalizer will deduplicate, filter, and truncate the decoded candidates
to the exact requested limit.

Axesso may return reviewer names, profile paths, helpful counts, images,
variations, and other fields. The adapter will ignore those fields and will not
persist the raw response. Unlike the Google Maps Actor, Axesso does not publish
a `personalData: false` input, so ReviewInsight can minimize retained data but
cannot prevent the provider from including public reviewer fields in its
transient response.

The Amazon run will use one bounded synchronous request with a `(5, 120)`
connect/read timeout for at most ten pages. It will not automatically retry a
failed run.

## Google Maps behavior

The existing Compass adapter and request shape remain unchanged except for the
shared allowed limits. It will continue sending:

- one `startUrls` item;
- the selected `maxReviews`;
- `reviewsSort: mostRelevant`;
- `reviewsOrigin: google`;
- `personalData: false`;
- `language: en`.

The existing Google URL policy remains unchanged in this milestone.

## Cache and compatibility

The 30-day SQLite cache and explicit refresh behavior remain unchanged.

Amazon cache entries will naturally separate because the new adapter uses a new
provider key. Existing Google Maps cache entries for limits 10 and 20 remain
compatible. Previously cached five-review entries become unreachable because
five is no longer an accepted limit; they may expire normally.

No database migration is required. Historical reports attributed to Outscraper
remain readable and keep their original provenance. New Amazon reports will use
provider label `Apify (Axesso)`.

## Failure handling

Existing application-owned errors remain in use:

- missing `APIFY_API_TOKEN`;
- provider authentication failure;
- quota exhaustion or provider unavailability;
- timeout or transport failure;
- malformed provider response;
- invalid platform URL;
- unsupported limit;
- fewer than two usable written reviews.

Provider diagnostics, response bodies, tokens, and reviewer information will not
be returned to the UI. A failed refresh preserves the last successful collection
and cache entry.

## Cost and usage controls

Axesso currently advertises `$0.90 per 1,000 reviews`, with platform usage
included. Approximate maximum review-event costs are:

- 10 reviews: `$0.009`;
- 20 reviews: `$0.018`;
- 50 reviews: `$0.045`;
- 100 reviews: `$0.09`.

The free plan's `$5` monthly credit can cover a small proof of concept, but
pricing and Actor availability may change. Google Maps uses the Compass Actor's
separate pay-per-review pricing.

Usage remains bounded by:

- one product or place per request;
- a maximum requested limit of 100;
- one provider run per cache miss or explicit refresh;
- a 30-day normalized cache;
- no automatic retry, background refresh, or scheduled runs;
- fixture-only automated tests.

Sources:

- <https://apify.com/axesso_data/amazon-reviews-scraper>
- <https://apify.com/axesso_data/amazon-reviews-scraper/pricing>
- <https://apify.com/compass/google-maps-reviews-scraper>
- <https://apify.com/pricing>

## Terms and storage caveat

Both Actors are unofficial scraping services. Their availability does not grant
ReviewInsight or its users permission to copy, retain, redistribute, or
commercialize source content. Amazon's terms restrict automated access, and
review text can contain personal information. Operators remain responsible for
confirming permitted use and retention.

Apify may retain Actor run and dataset data under its storage policy.
ReviewInsight will retain only normalized fields in its local cache and report
history and will not automatically delete provider-side run data in this
milestone.

## Replaceability

The Amazon provider remains replaceable through the existing adapter protocol.
A future Actor or open-dataset adapter can replace Axesso by implementing the
same `fetch(source_url, limit)` contract, advertising compatible limits, and
returning provider-neutral candidates. The service, cache, API, dashboard,
analysis, and history layers should not require provider-specific changes.

## Expected code changes

- Add an Axesso Amazon adapter and fixture.
- Remove the Outscraper adapter from the registry and remove its credential from
  active setup documentation.
- Retain compatibility for historical `Outscraper` report provenance.
- Define and use one shared `10, 20, 50, 100` limit set.
- Change the dashboard URL label and placeholder to generic wording.
- Update README, architecture, status, environment example, and provider usage
  estimates.
- Update adapter, service, API, dashboard, documentation, and compatibility
  tests.

## Test strategy

Automated tests will use fixtures, fake HTTP sessions, temporary SQLite files,
and mocks only. They will not contact Apify, Axesso, Compass, Amazon, Google
Maps, Outscraper, or Groq.

Tests will verify:

- both platforms advertise `10, 20, 50, 100`;
- five and other unsupported limits are rejected before provider work;
- the generic URL label and placeholder are rendered;
- the Axesso request uses bearer authentication, one ASIN, `domainCode: com`,
  `sortBy: helpful`, and the expected page count for each allowed limit;
- only title, body, rating, date, product title, and source provenance survive
  response decoding;
- reviewer, profile, image, variation, and raw-response fields are discarded;
- responses are normalized, deduplicated, and capped at the selected limit;
- provider failures map to existing safe application errors;
- caching prevents repeated Actor runs and explicit refresh performs one run;
- old history rows with `provider="Outscraper"` remain readable;
- the demo, Groq analysis contract, and history flow remain unchanged.

An optional live Amazon smoke test may be performed only after explicit user
approval. It will use a known public `amazon.com` product URL, request ten
reviews, make no Groq call, and report the actual count without displaying
reviewer identity.
