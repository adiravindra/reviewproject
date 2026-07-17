# Groq-Only Review Intelligence MVP Design

## Goal

Deliver a stable, presentation-ready local MVP that collects reviews from public
static pages, shows the collected evidence before analysis, produces structured
Groq insights, and stores successful reports in local history. The existing
FastAPI and Streamlit split remains. The runtime stays local, supervised, and
free of browser automation, workers, authentication, and deployment machinery.

## Approved architecture

`run_app.py` continues to load the project `.env`, supervise one FastAPI process
and one Streamlit process, and open the ready dashboard. Streamlit owns user
interaction and presentation. FastAPI owns URL safety, static collection, demo
data loading, Groq credential validation, model analysis, deterministic metrics,
history persistence, and safe error mapping.

The retained processing modules remain focused:

- `collector.py` validates public destinations, performs bounded static HTTP
  retrieval, extracts JSON-LD first, and falls back to conservative HTML review
  cards.
- `credentials.py` reads only `GROQ_API_KEY` and validates it with Groq's
  non-generative model-list endpoint.
- `analyzer.py` constructs only the configured Groq Llama model and returns a
  schema-validated response.
- `service.py` separates collection from analysis so users can inspect reviews
  before any generative request.
- A new `history.py` module owns a small SQLite repository.
- A new demo-data module loads one checked-in JSON dataset containing ten
  realistic mixed-sentiment reviews.

The obsolete Gemini dependency, configuration, credential registry entries,
provider type, provider factory branches, request fields, UI controls, tests,
and documentation are removed. FastAPI and the dashboard HTTP client remain.

## API and user flow

The application uses explicit stages:

1. The user enters a public `http` or `https` product/review-page URL and clicks
   **Extract reviews**.
2. Streamlit calls `POST /api/collect`. FastAPI returns normalized reviews and
   source metadata without invoking Groq.
3. Streamlit displays every bounded review, its rating/date when available, and
   a visible extraction label such as **JSON-LD** or **HTML fallback**.
4. The user clicks **Analyze with Groq**. Streamlit sends the displayed,
   validated collection to `POST /api/analyze`; no provider field exists.
5. FastAPI validates Groq configuration and credentials, performs one
   structured analysis, calculates deterministic metrics, stores the validated
   successful report in SQLite, and returns it.
6. Streamlit renders the report and makes it available from the history view.

The trusted local UI may submit the normalized collection it just received.
FastAPI validates the submitted schema and enforces the same review count and
size bounds before model use. This avoids fetching a live page twice and ensures
the analysis corresponds exactly to the reviews the user inspected.

`GET /api/demo` loads the checked-in dataset and returns the same collection
shape with `extractor="demo"` and `is_demo=true`. It is reached only through an
explicit **Use bundled demo data** action. The dashboard displays a persistent
**DEMO DATA** notice before and after analysis. A failed URL collection never
switches to demo data automatically.

History endpoints list recent successful runs and retrieve one validated report
by integer identifier. History is read-only from the dashboard for this MVP;
deletion, editing, export, accounts, and synchronization are out of scope.

## SQLite history

The database lives at `data/review_history.db`, a generated path already covered
by `.gitignore`. Python's standard-library `sqlite3` module is sufficient, so no
new database package or service is introduced.

One table stores:

- integer primary key;
- UTC creation timestamp;
- source URL when present;
- source title and extractor;
- explicit demo flag;
- review count and overall sentiment for list display;
- the complete validated report as JSON.

The repository creates the directory and schema on first use, uses parameterized
statements, commits each successful insert atomically, orders history newest
first, and validates stored JSON through `AnalysisResponse` when reading.
History write failures produce a safe local-storage error rather than returning
a successful report that appears persisted. Failed collection or analysis runs
are never stored.

SQLite was selected over JSONL because it provides atomic writes, deterministic
ordering, and reliable record retrieval while remaining dependency-free. A
directory of per-run JSON files was rejected because it creates file clutter
and requires a separate indexing convention.

## Groq configuration and analysis

`GROQ_API_KEY` is the only accepted credential variable.
`REVIEWINSIGHT_GROQ_MODEL` optionally overrides the existing
`llama-3.3-70b-versatile` default. The key is read from the inherited environment
or project `.env`; the UI never asks for it and no API response, log, exception,
or history record contains it.

Credential presence and Groq acceptance are checked immediately before analysis
and before page/model work in that stage. Missing configuration, rejected
credentials, temporary Groq unavailability, model invocation failure, and model
output parsing/validation failure use separate stable public codes. Provider
response bodies and raw model responses never cross the backend boundary.

The model receives only bounded review IDs, texts, ratings, and dates. One
structured invocation returns the summary, overall sentiment, themes, strengths,
weaknesses, actions, and one sentiment per review. Returned review IDs must
match the submitted set exactly. Metrics remain deterministic Python
calculations.

## Collection behavior and errors

The current SSRF controls, redirect revalidation, static-only retrieval, timeout,
HTML content-type requirement, response-size cap, deduplication, minimum review
count, and maximum review count remain.

Collection errors become more specific without revealing transport internals:

- `invalid_url` for malformed, unsupported, credential-bearing, unresolvable, or
  non-public destinations;
- `site_blocked` for access-denied or rate-limited responses;
- `collection_timeout` for bounded connection/read timeouts;
- `collection_failed` for other safe retrieval failures;
- `malformed_json_ld` when review-like JSON-LD exists but is malformed and no
  HTML fallback succeeds;
- `no_reviews` when no sufficient review evidence is present.

Malformed unrelated JSON-LD does not prevent a valid HTML fallback. Sites that
need login, JavaScript rendering, browser automation, or anti-bot circumvention
remain unsupported and are excluded from the verified demo list.

## Presentation

The dashboard keeps a clear two-stage workflow and uses responsive Streamlit
containers plus small, escaped HTML components where color semantics are needed.

- Positive findings use green with a `✅ Positive` label.
- Negative findings use red with a `⚠️ Negative` label.
- Neutral findings use amber/gray with a `➖ Neutral` label.
- Mixed overall findings use a distinct blue/amber treatment and a `↔ Mixed`
  label.

The same labeled treatment applies to headline sentiment, themes, strengths,
weaknesses, and review-level sentiment. Color is always accompanied by text and
an icon. Ratings, source provenance, demo status, metrics, and history timestamps
remain readable without interpreting color.

The UI offers a current-analysis view and a history view. Selecting a stored run
renders the same report component used for a new analysis, preventing display
drift between current and historical results.

## Bundled data and external research

A checked-in JSON file contains ten fictional but realistic reviews for one
consumer product with positive, neutral, and negative ratings and narratives.
The file is deterministic, contains no scraped personal data, and is used only
after an explicit user action.

External research has two separate outputs:

1. A short verified live-demo list containing only exact public page URLs that
   the completed collector successfully processes. Each entry records whether
   it demonstrates JSON-LD, HTML fallback, ratings, descriptions, or full
   written reviews.
2. An open-dataset assessment covering Kaggle and free public hosts. Sources are
   evaluated for access requirements, licensing clarity, product identifiers,
   written review availability, and feasibility of retrieving reviews for one
   product. Kaggle web pages are not treated as live scraping targets when they
   require login, API credentials, downloads, or JavaScript. A dataset is not
   integrated into the URL flow unless it offers a stable anonymous public
   endpoint compatible with the static collector and the integration stays
   within the approved scope.

No website-specific extraction output is hardcoded.

## Testing and verification

Existing tests are updated rather than discarded where their behavior remains
relevant. Focused tests cover:

- the absence of Gemini/provider selection in schemas, calls, UI, dependencies,
  examples, and retained source;
- Groq key presence, safe validation, model construction, and sanitized errors;
- JSON-LD priority, HTML fallback, malformed JSON-LD, blocked responses,
  timeouts, missing reviews, and URL safety;
- staged collect-then-analyze behavior and exact evidence reuse;
- demo loading, explicit demo labels, and no automatic fallback;
- SQLite initialization, atomic insert, newest-first listing, retrieval,
  validation, and safe storage failures;
- sentiment labels/styles and safe HTML escaping;
- API contracts and dashboard client behavior;
- launcher supervision and documentation consistency.

The final verification sequence is:

1. run the complete unit suite;
2. compile retained Python files;
3. run live collection checks for candidate URLs and keep only successful ones;
4. start the supervised application;
5. open the local Streamlit URL in the machine's installed Google Chrome;
6. manually verify page load, URL extraction, pre-analysis review display, Groq
   analysis, colors and labels, summary, history reload, explicit demo flow, and
   representative error states;
7. fix observed issues and repeat affected checks.

No Selenium, Playwright, in-app browser, embedded browser, Docker, queue, worker,
authentication, or cloud deployment is introduced.

## Expected deliverables

The final handoff includes the implemented architecture; added, changed, and
removed files; exact Windows installation, test, and launch commands; the
`GROQ_API_KEY` variable name; verified live-demo URLs with demonstrated
extraction behavior; open-dataset findings; a three-to-five-minute presentation
script; the explicit bundled-data fallback procedure; and remaining
limitations.
