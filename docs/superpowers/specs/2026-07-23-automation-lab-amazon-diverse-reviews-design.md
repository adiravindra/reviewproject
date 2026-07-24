# Automation Lab Amazon and Diverse Review Import Design

**Date:** 2026-07-23
**Status:** Approved

## Context

ReviewInsight currently imports Amazon reviews through Apify Actor
`axesso_data/amazon-reviews-scraper`. A live Console run showed that Actor
starts successfully but exits before collection with:

```text
Actor usage only allowed for paying user. Please make sure you have sufficient quota.
```

The existing `APIFY_API_TOKEN` is valid and continues to work for Google Maps.
The failure is therefore an Actor billing restriction, not an Amazon URL,
ASIN, or token-format failure.

ReviewInsight will replace Axesso with Apify Actor
`automation-lab/amazon-reviews-scraper`. The Actor's Console pricing for the
current Free plan is `$0.01` per run start plus `$2.00 per 1,000` reviews
(`$0.002` per review), with platform usage included. Pricing and availability
remain external and may change.

## Goals

- Replace the active Axesso Amazon Actor with Automation Lab's Amazon Reviews
  Scraper while keeping the provider adapter replaceable.
- Use the existing backend-only `APIFY_API_TOKEN`.
- Preserve the shared limits `10`, `20`, `50`, and `100`.
- Import a naturally varied review sample without star, keyword, or
  positive-sentiment filtering.
- Preserve provider order and every usable review up to the selected limit.
- Preserve the current cache, refresh, analysis, report, history, and demo
  flows.
- Continue analyzing only the first 40 imported reviews and disclosing
  `40 of N reviews analyzed`.
- Preserve actual imported counts and rating values in the existing source and
  review models.
- Keep all automated tests offline and quota-free.

## Non-goals

- Do not add an Amazon-provider selector or fallback Actor.
- Do not use Amazon account credentials, cookies, browser sessions, or Amazon
  API credentials.
- Do not manufacture rating balance by reordering, duplicating, or dropping
  otherwise usable reviews.
- Do not guarantee that every source contains positive, neutral, and negative
  reviews.
- Do not add discard-reason provenance or change the existing requested versus
  retrieved count model.
- Do not migrate existing cache records or rewrite historical reports.
- Do not add `a.co` short-link resolution in this provider replacement.

## Architecture

The existing `ReviewProviderAdapter` protocol and provider registry remain the
replacement boundary. The Amazon adapter continues to own:

- Actor identity and endpoint;
- request construction;
- timeout and safe provider-error mapping;
- response-shape validation;
- mapping provider records into `ProviderReviewCandidate`.

The service, cache, API, dashboard, normalization, analysis, report, and
history layers remain provider-neutral.

The active Amazon provider identity becomes:

```text
provider_key   = apify_automation_lab_amazon
provider_label = Apify (Automation Lab)
```

The new provider key isolates Automation Lab cache entries from existing
Axesso cache entries. Old cache data remains untouched. Historical reports
whose provider is `Apify (Axesso)` or `Outscraper` remain readable and retain
their original provenance.

## Amazon Request

The adapter will call:

```text
POST https://api.apify.com/v2/acts/automation-lab~amazon-reviews-scraper/run-sync-get-dataset-items
```

Authentication remains the recommended private header:

```text
Authorization: Bearer <APIFY_API_TOKEN>
```

For one validated Amazon.com ASIN and a selected limit, the request body is
exactly:

```json
{
  "asins": [
    "0321965515"
  ],
  "marketplace": "US",
  "maxReviewsPerProduct": 50,
  "sort": "helpful"
}
```

`maxReviewsPerProduct` is the selected shared limit. The adapter will not add
`filterByStars`, a keyword filter, a positive-only filter, or any other Actor
input field.

Existing Amazon URL validation and ASIN extraction remain unchanged. Tracking
query parameters do not affect the extracted ASIN.

## Amazon Response Mapping

The synchronous dataset response must be a JSON list of objects. Individual
review records are mapped as follows:

| Automation Lab field | ReviewInsight candidate field |
| --- | --- |
| `title` | `title` |
| `body` | `body` |
| `rating` | `rating` |
| `date` | `date` |
| `asin` | source identity |

If the response does not provide product metadata in the returned dataset,
the source title falls back to `Amazon product <ASIN>`.

The adapter discards author names, author URLs, provider review IDs, verified
flags, helpful counts, review URLs, marketplace fields, scrape timestamps,
media, and any other provider-only fields. Raw responses are not persisted.

## Diversity and Correctness

Amazon uses `sort: "helpful"` with no `filterByStars`, keyword filter, or
positive-only filter.

Google Maps keeps `reviewsSort: "mostRelevant"` with no rating filter.

Both adapters preserve provider order and retain every usable review up to the
selected limit.

ReviewInsight does not artificially manufacture a rating balance by
reordering or dropping reviews; doing so could distort the provider's
requested sorting and provenance.

Mixed-rating fixtures include positive, neutral, and negative reviews, such as
5-, 3-, and 1-star entries. Tests prove all ratings survive the adapter and
normalization flow.

A source does not fail merely because its real reviews are uniform or too few
to cover every sentiment. Diversity depends on what Amazon or Google exposes,
so the application can request an unbiased sample but cannot guarantee one.

Actual imported counts and rating values remain visible for judging whether
the sample is useful.

Existing normalization may continue excluding duplicate, empty, too-short, or
otherwise unusable review text. ReviewInsight continues showing requested and
actual imported counts without adding discard-reason provenance.

## Google Maps

The Google Maps Actor remains:

```text
compass/google-maps-reviews-scraper
```

Its request continues to use:

```json
{
  "startUrls": [
    {
      "url": "<validated Google Maps place URL>"
    }
  ],
  "maxReviews": 50,
  "reviewsSort": "mostRelevant",
  "reviewsOrigin": "google",
  "personalData": false,
  "language": "en"
}
```

No Google request or production decoding change is required for diversity.
Tests will make the absence of a rating filter and preservation of mixed
ratings explicit.

## Errors and Privacy

The replacement uses the existing application-owned error vocabulary for
missing credentials, authentication, quota, request rejection, unavailable
provider, timeout, malformed response, and insufficient usable reviews.

Logs contain only the provider key, application-owned error category, and HTTP
status. They do not contain tokens, source URLs, raw response bodies, reviewer
data, or exception text.

The dashboard continues displaying safe error messages returned by the API.

## Testing

Implementation follows test-driven development.

Automated tests use sanitized fixtures, fake HTTP sessions, mocks, and
temporary storage only. They make no live Apify, Automation Lab, Compass,
Amazon, Google Maps, or Groq request.

Tests cover:

- exact Automation Lab Actor endpoint and Bearer authentication;
- exact four-field Amazon request for limits `10`, `20`, `50`, and `100`;
- absence of Amazon star, keyword, and positive-only filters;
- mixed 5-, 3-, and 1-star Amazon response decoding in provider order;
- mixed 5-, 3-, and 1-star Google response decoding in provider order;
- mixed ratings surviving normalization;
- provider-only and personal fields being discarded;
- empty, malformed, transport, HTTP, timeout, and credential failures;
- new provider label and cache-key isolation;
- preserved cache, explicit refresh, API, dashboard, analysis, report, demo,
  and historical compatibility flows;
- full test-suite and Python compile verification.

After offline implementation and verification, work stops before any live
provider smoke test. A live Amazon or Google Maps request may run only after
the user gives explicit approval with awareness that it can consume Apify
credits.

## Documentation

Active setup and provider documentation will:

- replace Axesso with Automation Lab;
- describe the exact free-plan pricing observed in Apify Console;
- retain the mutable-pricing caveat;
- explain that both imports request unfiltered provider-ranked samples;
- preserve the unofficial-provider, Amazon/Google terms, privacy, retention,
  and cache caveats;
- preserve historical Axesso and Outscraper provenance.

## Acceptance Criteria

- Amazon imports use `automation-lab/amazon-reviews-scraper`.
- The Amazon JSON body contains exactly `asins`, `marketplace`,
  `maxReviewsPerProduct`, and `sort`.
- Amazon uses `sort: "helpful"` and no sentiment filter.
- Google Maps keeps `reviewsSort: "mostRelevant"` and no rating filter.
- Mixed positive, neutral, and negative fixture reviews remain in provider
  order through normalization.
- Shared limits, display count, 40-review analysis cap, cache, refresh,
  reports, history, and demo behavior remain intact.
- Historical Axesso and Outscraper reports remain readable.
- Automated tests remain entirely offline.
- No live provider request occurs without explicit approval.
