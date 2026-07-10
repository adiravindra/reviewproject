# Website Review Intelligence Design

## Goal

Replace ReviewInsight's single-review Hugging Face workflow with one URL-to-insights workflow. A user submits a public product, business, restaurant, hotel, place, or similar review page; the backend collects available reviews, normalizes and deduplicates them, analyzes the collection with LangChain and a configurable external LLM, saves the completed report, and returns a product- or place-level dashboard payload.

The implementation is a proof of concept. It must stay synchronous, bounded, honest about scraping failures, and easy to extend without introducing background-job or browser-automation infrastructure.

## Existing System

The repository currently contains:

- A FastAPI backend with single-review and batch-text routes.
- A Streamlit frontend centered on a pasted review.
- Local Hugging Face sentiment and summarization wrappers with rule-based fallbacks.
- SQLite persistence for individual review analyses.
- One unit-test module focused on the Hugging Face wrappers.

The old single-review routes, schemas, UI, prompts, Hugging Face model loading, local sentiment and summarization code, model warmup, fallback analysis, dependencies, documentation, obsolete tests, and old review-sample utilities that serve only that workflow will be removed. The URL-based collection analysis will be the only active analysis workflow.

## Chosen Architecture

The system will expose one synchronous `POST /analysis/website` endpoint:

```text
URL submission
  -> public-URL and SSRF validation
  -> bounded HTTP fetch
  -> scraper registry
      -> JSON-LD / Schema.org scraper
      -> static HTML review-card scraper
      -> future browser scraper interface
  -> normalize and deduplicate
  -> deterministic rating statistics
  -> LangChain batch analysis
  -> structured synthesis
  -> atomic SQLite save
  -> Streamlit dashboard response
```

This design avoids partially completed job state and background infrastructure. Streamlit will show an honest combined loading state rather than a fabricated percentage.

## Configuration and Safety Limits

The initial defaults are:

- Maximum response body: 2 MiB per page.
- Maximum pagination depth: three same-origin pages.
- Scraping deadline: 25 seconds, with bounded connection and read timeouts.
- Maximum unique reviews analyzed: 60.
- LLM batch size: 15 reviews.
- Maximum batch calls: four.
- Maximum synthesis calls: one.
- Maximum total LLM calls: five.
- Provider-call timeout: 20 seconds per call.
- Overall application deadline: 120 seconds.
- Minimum valid reviews: two.
- Collections with fewer than five reviews receive a low-sample warning.

These values will be centralized in application settings. Limits that are useful to tune for a demo may be overridden through environment variables, while safe hard ceilings remain enforced in code.

The frontend timeout will be slightly longer than the backend's overall deadline so backend timeout errors can be rendered instead of appearing as client connection failures.

## URL Validation and HTTP Fetching

Only `http` and `https` URLs are accepted. Validation will reject malformed URLs, embedded credentials, loopback addresses, private and link-local networks, and non-public resolved addresses. Redirect targets will be revalidated before following them to prevent redirects into private networks.

The HTTP layer will use a descriptive user agent, explicit timeouts, redirect limits, content-type checks, and streaming size enforcement. It will identify common denial and anti-bot responses without attempting to bypass them. Protected and JavaScript-heavy pages will produce clear structured errors.

## Scraper Registry

The scraper registry is the primary extraction extension point. Each scraper receives fetched static HTML plus page metadata and returns a provider-neutral extraction result. Adding browser rendering later must require a new scraper or fetcher implementation, not changes to orchestration, analysis, persistence, or the dashboard.

Extraction order:

1. JSON-LD and embedded Schema.org review data.
2. Static HTML review-card extraction.
3. No browser fallback in this version.

The JSON-LD scraper will support review objects found directly, in lists, and under nested entities such as `mainEntity`, `Product`, `Restaurant`, `LocalBusiness`, `Hotel`, `Place`, and related Schema.org types. It will capture entity names, review bodies, ratings, authors, dates, and source URLs when present.

The static HTML scraper will use conservative, review-specific semantic attributes and common review-card patterns. It will not treat arbitrary paragraphs or comments as reviews. If neither extractor can confidently find reviews, the registry returns an unsupported-source or no-reviews result rather than guessing.

Implementation will verify and document at least one public static demonstration source that works with these generic extractors. Because external markup is outside the project's control, a source is listed as demonstrated only after an end-to-end check. If no stable public source can be verified at implementation time, the documentation will say so and use deterministic HTML fixtures for tests rather than claiming compatibility that cannot be reproduced.

Pagination is followed only when the selected scraper identifies a trustworthy same-origin next-page link. The fetcher enforces the global page and time limits. If a later page fails after at least two valid reviews were collected, analysis may continue with a warning. Failure on the first page is an error.

## Normalized Review Model

Each stored normalized review contains:

- Stable internal review ID.
- Cleaned review text.
- Optional rating normalized to a 1-5 scale.
- Optional original rating and rating scale when needed for traceability.
- Optional author.
- Optional publication date.
- Optional source URL.

Whitespace is normalized without rewriting customer wording. Empty and obviously invalid entries are removed. Exact duplicates are detected case-insensitively after normalization. The analysis cap is applied only after cleaning and deduplication.

Authors remain in storage and dashboard metadata where appropriate but are excluded from LLM prompts. Prompts receive review ID, text, rating, and date only when useful.

Collection metadata distinguishes:

- Extraction candidates found.
- Unique valid reviews.
- Reviews analyzed.
- Duplicates removed.
- Invalid reviews removed.
- Reviews omitted by the analysis cap.
- Pages attempted and successfully extracted.
- Partial-success and low-sample warnings.

## API Contracts

Request:

```json
{
  "url": "https://example.com/product"
}
```

Successful responses separate:

- `source`: requested URL, canonical URL, entity name and type, page title, scraper name, and page counts.
- `collection`: found, valid, analyzed, duplicate, invalid, and truncated counts plus warnings.
- `metrics`: deterministic review and rating statistics plus code-counted sentiment classifications.
- `insights`: LLM-generated executive summary, strengths, complaints, aspects, opportunities, and representative reviews.
- `reviews`: normalized reviews included in the analysis.
- `analysis`: provider, model, batch count, and completion timestamp.

The response includes the number of reviews found versus analyzed and clearly indicates partial extraction or truncation.

History routes return website-level summaries and allow the frontend to load a complete stored report without rerunning scraping or analysis.

## Deterministic Metrics

The application calculates these values in code:

- Reviews found, valid, analyzed, skipped, and rated.
- Average normalized rating.
- One- through five-star distribution using documented deterministic bucketing.
- Counts of positive, neutral, and negative per-review classifications returned by the structured batch analysis.
- Overall sentiment derived from those counts.

The LLM never performs arithmetic for dashboard metrics. LLM-created themes, summaries, and recommendations remain visibly separate from deterministic statistics.

## LangChain Provider Boundary

LangChain is used for all active language-model analysis. Provider-specific construction is isolated behind a factory selected by environment variables.

Initial providers:

- Default: Google Gemini through `langchain-google-genai`, using `gemini-2.5-flash-lite` unless overridden.
- Alternative: Groq through `langchain-groq`, with the model selected through configuration.

The orchestration and batch-analysis services depend only on a small structured-chat interface, not Gemini or Groq classes. API keys are read from provider-standard environment variables and are never hardcoded, logged, or committed.

There is no local-model or rule-based analysis fallback. Missing credentials, provider failures, timeouts, and invalid structured outputs produce explicit LLM errors.

## Batch Analysis and Synthesis

Up to 60 reviews are partitioned into batches of 15. Each batch call returns validated structured output containing:

- A sentiment classification for every supplied review ID.
- Positive themes with supporting review IDs.
- Complaints with supporting review IDs.
- Important aspects.
- Candidate improvement opportunities.

Structured output validation verifies that returned review IDs exist in the supplied batch and that every review received exactly one sentiment classification. One bounded retry may be used for invalid structured output without exceeding the five-call design limit; if retry capacity would violate the call ceiling, the request fails explicitly.

The synthesis call receives structured batch outputs rather than all raw review text. It consolidates semantically similar themes, complaints, aspects, and opportunities; writes the executive summary; and selects representative review IDs. Application code resolves those IDs back to the original normalized review text, preventing fabricated quotations.

## Error Contract

All failures use one envelope:

```json
{
  "error": {
    "code": "blocked_source",
    "message": "The website blocked automated access.",
    "stage": "scraping",
    "retryable": false,
    "details": {
      "url": "https://example.com/product"
    }
  }
}
```

Supported error codes:

- `invalid_url`: malformed, unsafe, private, loopback, or unsupported-scheme URL.
- `unsupported_source`: accessible page whose review structure is not supported.
- `blocked_source`: access denial, anti-bot response, or recognizable challenge page.
- `no_reviews_found`: supported extraction completed without review candidates.
- `insufficient_reviews`: fewer than two usable reviews remain after cleaning.
- `scrape_failed`: connection, timeout, oversized response, content, parsing, or unexpected scraper failure.
- `llm_failed`: missing credentials, provider rejection, timeout, or invalid structured output.
- `request_timeout`: overall application deadline exceeded.

HTTP statuses remain semantically appropriate while the JSON shape stays consistent. Internal exception text, API keys, and raw provider bodies are not returned to clients.

## Persistence

Persistence happens once, after the full response has passed validation. Scraping or LLM failures create no history record.

A new `website_analysis_runs` table stores the complete response payload plus indexed summary fields needed by history: ID, completion time, source URL, entity name, review count, average rating, overall sentiment, executive summary, provider, and model.

Existing `analysis_runs` rows may remain untouched in an already-created local database, but the new application will neither read nor write them. Fresh databases create only the new active website-analysis table. This preserves local data without retaining the old workflow in application code.

## Streamlit Dashboard

The Analysis page becomes a URL-first workspace with:

- Prominent public URL input.
- Concise supported-source and limit guidance.
- One `Analyze Reviews` action.
- An honest combined loading status for page access, collection, and analysis.
- Clear success and structured failure states.

The completed dashboard shows:

- Source identity, entity type, URL, completion time, scraper, and warnings.
- Reviews found and analyzed, average rating, rated-review count, and overall sentiment.
- Rating-distribution and sentiment charts based on deterministic metrics.
- Executive summary.
- Common positive themes.
- Recurring complaints.
- Important aspects.
- Prioritized improvement opportunities.
- Representative positive, neutral or mixed, and negative reviews using stored original text.
- An expandable normalized-review collection.
- An optional diagnostic raw-JSON expander.

The History page lists website analyses rather than individual reviews. Each entry shows source, date, review count, average rating, sentiment, and summary. Expanding an entry renders the stored report without scraping or LLM calls.

## Testing Strategy

Tests use HTML fixtures, fake HTTP responses, fake LangChain-compatible structured models, and temporary SQLite databases. The suite does not call live websites or real LLM providers.

Coverage includes:

- URL and redirect safety, including private IP and embedded-credential rejection.
- JSON-LD extraction across direct, list, and nested entity shapes.
- Conservative static HTML extraction and extractor priority.
- Same-origin pagination, page and size limits, blocked-page detection, and partial success.
- Cleaning, rating normalization, deduplication, invalid removal, and review caps.
- Deterministic metric calculations.
- Batch partitioning, LLM-call ceilings, author exclusion, structured validation, and review-ID resolution.
- Gemini and Groq provider selection behind the shared factory.
- Successful orchestration and atomic save behavior.
- Proof that failed scraping or analysis produces no history record.
- Every API error code and envelope.
- Frontend API client error preservation and history loading.
- Dashboard formatting helpers.
- One end-to-end backend test with fixture HTML, fake fetching, fake LLM results, and temporary SQLite.

## Implementation Stages and Commits

Implementation proceeds test-first in small logical commits:

1. Remove the Hugging Face and single-review workflow.
2. Add schemas, errors, settings, and normalized review processing.
3. Add URL safety, bounded fetching, scraper registry, JSON-LD extraction, static HTML fallback, pagination, and fixtures.
4. Add deterministic metrics and LangChain provider and batch analysis.
5. Add the synchronous website endpoint and atomic persistence and history.
6. Replace the Streamlit input and build website-level dashboard and history views.
7. Complete integration tests, dependency cleanup, environment examples, architecture documentation, and README.
8. Run full verification and create a final corrective commit only if required.

No changes will be pushed unless explicitly requested.
