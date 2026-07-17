# Groq-Only Review Intelligence MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing FastAPI + Streamlit ReviewInsight application into a Groq-only, staged, presentation-ready MVP with explicit demo data and reliable SQLite history.

**Architecture:** Keep `run_app.py` supervising FastAPI and Streamlit. FastAPI exposes separate collection, demo, analysis, and history boundaries; Streamlit first displays normalized evidence and only then requests Groq analysis. Successful validated reports are stored atomically in a local standard-library SQLite database.

**Tech Stack:** Python 3.12+, FastAPI, Streamlit, Pydantic, Requests, BeautifulSoup, LangChain, `langchain-groq`, standard-library `sqlite3`, `unittest`.

## Global Constraints

- `GROQ_API_KEY` is the only credential variable; the UI never accepts or displays a key.
- The default model remains `llama-3.3-70b-versatile`, optionally overridden by `REVIEWINSIGHT_GROQ_MODEL`.
- Keep FastAPI + Streamlit under the existing local supervisor.
- Collection remains static HTTP only: no Selenium, Playwright, browser automation, JavaScript execution, anti-bot bypass, Docker, workers, queues, authentication, or deployment work.
- JSON-LD review extraction has priority; conservative static HTML review cards are the fallback.
- Demo data is used only after an explicit user action and is always labeled.
- Provider response bodies, raw model output, credentials, headers, exception internals, and stack traces never cross the backend boundary.
- Use test-driven changes, preserve working safety controls, and commit each independently testable task.

---

### Task 1: Groq-Only Contracts and Bundled Demo Data

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/demo.py`
- Create: `demo_data/product_reviews.json`
- Create: `tests/test_demo_data.py`
- Modify: `tests/test_api_mvp.py`

**Interfaces:**
- Produces: `CollectionRequest(url: HttpUrl)`, `AnalysisRequest(source: SourceInfo, reviews: list[Review])`, `AnalysisRequest.to_collection() -> CollectionResult`, `SourceInfo(url: HttpUrl | None, title: str, extractor: Literal["json_ld", "html_cards", "demo"], is_demo: bool)`, `HistoryItem(id: int, created_at: str, source_title: str, source_url: str | None, extractor: str, is_demo: bool, review_count: int, overall_sentiment: OverallSentiment)`, optional `AnalysisResponse.history_id: int | None`, and `load_demo_collection(path: Path | None = None) -> CollectionResult`.
- Removes: `Provider` and `AnalysisRequest.provider`.
- Consumes: existing `Review`, `CollectionResult`, `AnalysisResponse`, and Pydantic validation.

- [ ] **Step 1: Write failing contract and demo tests**

Add tests that assert `AnalysisRequest` accepts only `source` plus two-to-forty reviews, rejects a `provider` field with `extra="forbid"`, `SourceInfo` permits `url=None` only for `extractor="demo"`, and `load_demo_collection()` returns exactly ten mixed-rating reviews with `is_demo=True`.

```python
request = AnalysisRequest.model_validate(
    {"source": live_source.model_dump(mode="json"), "reviews": reviews}
)
self.assertEqual(len(request.reviews), 2)
with self.assertRaises(ValidationError):
    AnalysisRequest.model_validate(
        {"source": live_source.model_dump(mode="json"), "reviews": reviews, "provider": "groq"}
    )

demo = load_demo_collection()
self.assertEqual(len(demo.reviews), 10)
self.assertTrue(demo.source.is_demo)
self.assertEqual(demo.source.extractor, "demo")
self.assertEqual({review.rating for review in demo.reviews}, {1, 2, 3, 4, 5})
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_demo_data tests.test_api_mvp -v
```

Expected: failure because demo contracts and loader do not exist and provider fields are still accepted.

- [ ] **Step 3: Implement strict contracts and deterministic demo loading**

Set `ConfigDict(extra="forbid")` on inbound request models, constrain `Review.text` to a safe maximum, make `AnalysisRequest.reviews` use `Field(min_length=2, max_length=40)`, implement `to_collection()` as `CollectionResult(source=self.source, reviews=self.reviews)`, add theme-level sentiment, extend `SourceInfo`, and add:

```python
DEMO_PATH = Path(__file__).resolve().parents[2] / "demo_data" / "product_reviews.json"

def load_demo_collection(path: Path | None = None) -> CollectionResult:
    payload = json.loads((path or DEMO_PATH).read_text(encoding="utf-8"))
    reviews = [Review.model_validate(item) for item in payload["reviews"]]
    return CollectionResult(
        source=SourceInfo(url=None, title=payload["title"], extractor="demo", is_demo=True),
        reviews=reviews,
    )
```

The JSON file contains ten fictional reviews for one named consumer product, with full written comments, dates, and ratings spanning 1–5.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: all contract and demo tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models.py backend/app/demo.py demo_data/product_reviews.json tests/test_demo_data.py tests/test_api_mvp.py
git commit -m "feat: add strict staged contracts and demo reviews"
```

### Task 2: Remove Provider Abstractions and Make Groq the Only AI Boundary

**Files:**
- Modify: `backend/app/credentials.py`
- Modify: `backend/app/analyzer.py`
- Modify: `backend/app/errors.py`
- Modify: `tests/test_credentials.py`
- Modify: `tests/test_analyzer_mvp.py`
- Modify: `requirements.txt`
- Modify: `.env.example`

**Interfaces:**
- Produces: `get_groq_api_key() -> str`, `validate_groq_credentials(*, session=requests) -> None`, `build_model()`, and `analyze_reviews(reviews: list[Review], *, agent_factory=create_agent, model_factory=build_model) -> AgentInsights`.
- Removes: credential registry, provider arguments, Google imports/configuration, and `langchain-google-genai`.

- [ ] **Step 1: Replace provider tests with Groq-only failing tests**

Assert the credential module has no provider registry, `get_groq_api_key` trims `GROQ_API_KEY`, the preflight uses the Groq models endpoint and bearer header, missing/rejected/unavailable errors are sanitized, `build_model()` passes `llama-3.3-70b-versatile`, and invalid structured output maps to `model_output_invalid`.

```python
with patch.dict(os.environ, {"GROQ_API_KEY": "  groq-secret  "}, clear=True):
    validate_groq_credentials(session=session)
self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})

with self.assertRaises(AnalysisError) as raised:
    analyze_reviews(sample_reviews(), agent_factory=factory, model_factory=lambda: object())
self.assertEqual(raised.exception.code, "model_output_invalid")
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_credentials tests.test_analyzer_mvp -v
```

Expected: failures from old provider arguments, Google behaviors, and generic parse errors.

- [ ] **Step 3: Implement the Groq-only credential and analyzer APIs**

Replace the registry with constants:

```python
GROQ_API_KEY_VARIABLE = "GROQ_API_KEY"
GROQ_MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"

def get_groq_api_key() -> str:
    api_key = os.getenv(GROQ_API_KEY_VARIABLE, "").strip()
    if not api_key:
        raise AnalysisError("missing_api_key", "Set GROQ_API_KEY before analyzing reviews.")
    return api_key
```

Build only `ChatGroq`, call the model factory with no provider argument, require theme sentiment in the prompt, catch schema/key/type failures as `model_output_invalid`, catch invocation failures as `analysis_failed`, and retain exact review-ID validation.

- [ ] **Step 4: Remove obsolete dependency and environment settings**

Delete `langchain-google-genai`, `GOOGLE_API_KEY`, and `REVIEWINSIGHT_GOOGLE_MODEL`; retain `GROQ_API_KEY` and `REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile`.

- [ ] **Step 5: Run focused tests**

Run the command from Step 2.

Expected: all Groq credential and analyzer tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/credentials.py backend/app/analyzer.py backend/app/errors.py tests/test_credentials.py tests/test_analyzer_mvp.py requirements.txt .env.example
git commit -m "refactor: make analysis Groq only"
```

### Task 3: Add Specific Static Collection Failures

**Files:**
- Modify: `backend/app/collector.py`
- Modify: `tests/test_collector_mvp.py`

**Interfaces:**
- Produces: existing `collect_reviews(url, ...) -> CollectionResult` with stable `site_blocked`, `collection_timeout`, `malformed_json_ld`, `collection_failed`, `invalid_url`, and `no_reviews` codes.
- Retains: public-address validation, manual redirect validation, 1 MiB limit, JSON-LD priority, HTML fallback, deduplication, 2-review minimum, and 40-review cap.

- [ ] **Step 1: Write failing error-classification tests**

Cover status `401`, `403`, and `429` as `site_blocked`; `requests.Timeout` as `collection_timeout`; malformed review-like JSON-LD without usable HTML as `malformed_json_ld`; malformed unrelated JSON-LD plus valid HTML cards as successful fallback; and ordinary empty pages as `no_reviews`.

```python
with self.assertRaises(CollectionError) as raised:
    collect_reviews("https://example.com/product", session=FakeSession(requests.Timeout()))
self.assertEqual(raised.exception.code, "collection_timeout")
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp -v
```

Expected: old generic `collection_failed` or `no_reviews` codes fail the new assertions.

- [ ] **Step 3: Implement safe classifications**

Have `_fetch_once` map timeouts separately and denied/rate-limit statuses to `site_blocked`. Change `_extract_json_ld` to return a malformed-review-data flag in addition to title/candidates. Detect review-like raw keys such as `"review"` or `"reviewBody"` without exposing the raw script. After HTML fallback, raise `malformed_json_ld` only when that flag is true and no valid fallback reviews exist.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: all collector tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/collector.py tests/test_collector_mvp.py
git commit -m "feat: classify static collection failures"
```

### Task 4: Implement Atomic SQLite History

**Files:**
- Create: `backend/app/history.py`
- Create: `tests/test_history.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `HistoryStore(db_path: Path = DEFAULT_HISTORY_PATH)`, `save(report: AnalysisResponse) -> int`, `list_runs(limit: int = 50) -> list[HistoryItem]`, and `get(run_id: int) -> AnalysisResponse | None`.
- Consumes: `AnalysisResponse`, `HistoryItem`, and `AnalysisError`.

- [ ] **Step 1: Write failing SQLite repository tests**

Use `TemporaryDirectory` to assert first-use schema creation, successful report round-trip, newest-first summaries, explicit demo metadata, missing ID returning `None`, malformed stored JSON mapping to `history_failed`, parameterized integer lookup, and failed insert rollback.

```python
store = HistoryStore(Path(directory) / "history.db")
first_id = store.save(sample_response(title="First"))
second_id = store.save(sample_response(title="Second"))
self.assertEqual([item.id for item in store.list_runs()], [second_id, first_id])
self.assertEqual(store.get(first_id).source.title, "First")
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_history -v
```

Expected: import failure because `backend.app.history` does not exist.

- [ ] **Step 3: Implement the repository**

Create the parent directory lazily, connect with a context manager, create one `analysis_history` table, store `report.model_dump_json()` with summary columns using parameterized SQL, commit writes atomically, and validate reads with `AnalysisResponse.model_validate_json`. Convert `sqlite3.Error`, JSON validation failures, and filesystem errors to:

```python
raise AnalysisError(
    "history_failed",
    "Local analysis history could not be updated.",
) from None
```

- [ ] **Step 4: Ignore only generated history**

Keep `/data/` ignored and add an explanatory comment if necessary; do not place bundled demo data under the ignored directory.

- [ ] **Step 5: Run focused tests**

Run the command from Step 2.

Expected: all history tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/history.py tests/test_history.py .gitignore
git commit -m "feat: persist analysis history in SQLite"
```

### Task 5: Split Collection and Analysis Services

**Files:**
- Modify: `backend/app/service.py`
- Modify: `tests/test_service_mvp.py`

**Interfaces:**
- Produces: `run_analysis(collection: CollectionResult, *, credential_validator=validate_groq_credentials, analyzer=analyze_reviews) -> AnalysisResponse`.
- Consumes: a previously displayed and validated `CollectionResult`; no URL or provider.

- [ ] **Step 1: Write failing staged-service tests**

Assert analysis validates Groq before model construction, never calls the collector, analyzes the exact supplied reviews once, preserves source/demo metadata, and computes metrics deterministically.

```python
result = run_analysis(
    sample_collection(),
    credential_validator=lambda: events.append("validate"),
    analyzer=lambda reviews: (events.append(("analyze", reviews)), sample_insights())[1],
)
self.assertEqual(events[0], "validate")
self.assertIs(events[1][1], sample_collection_reviews_reference)
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_service_mvp -v
```

Expected: old URL/provider orchestration signatures fail.

- [ ] **Step 3: Implement staged analysis**

Remove collector imports and provider arguments from `run_analysis`, call `credential_validator()` first, call `analyzer(collection.reviews)`, compute metrics, and return `AnalysisResponse` with the collection source/reviews.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: all service tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/service.py tests/test_service_mvp.py
git commit -m "refactor: separate collection from Groq analysis"
```

### Task 6: Expose Collection, Demo, Analysis, and History APIs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `tests/test_api_mvp.py`

**Interfaces:**
- Produces: `POST /api/collect`, `GET /api/demo`, `POST /api/analyze`, `GET /api/history`, and `GET /api/history/{run_id}` plus retained `GET /health`.
- Consumes: `collect_reviews`, `load_demo_collection`, `run_analysis`, and `HistoryStore`.

- [ ] **Step 1: Write failing endpoint tests**

Inject fakes into `create_app` and assert:

```python
self.assertEqual(
    set(client.get("/openapi.json").json()["paths"]),
    {"/health", "/api/collect", "/api/demo", "/api/analyze", "/api/history", "/api/history/{run_id}"},
)
```

Also assert collection has no Groq call, analysis has no provider field, successful analysis is saved once and returns `history_id`, demo is explicitly labeled, history lists/retrieves reports, missing history is `404`, and every known safe error code maps to the documented status without raw internals.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp -v
```

Expected: missing routes and old analyze request signature.

- [ ] **Step 3: Implement injectable FastAPI boundaries**

Use a `create_app(collector=..., analysis_service=..., demo_loader=..., history_store=None)` factory. After `analysis_service(request.to_collection())`, call `history_store.save(report)`, set the returned `history_id` on a model copy, and return it. Use the same model-copy update when retrieving history so its row ID is present. Map collection codes, Groq codes, `model_output_invalid`, and `history_failed` explicitly. Keep unknown exceptions generic.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: all API tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/main.py tests/test_api_mvp.py
git commit -m "feat: add staged analysis and history APIs"
```

### Task 7: Update the Dashboard HTTP Client

**Files:**
- Modify: `dashboard/api_client.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Produces: `request_collection(url, base_url, *, session=requests)`, `request_demo(base_url, *, session=requests)`, `request_analysis(collection, base_url, *, session=requests)`, `request_history(base_url, *, session=requests)`, and `request_history_report(run_id, base_url, *, session=requests)`.
- Removes: provider argument and provider JSON field.

- [ ] **Step 1: Write failing client boundary tests**

Assert exact methods, URLs, JSON payloads, two-second health/history timeout, fifteen-second collection timeout, forty-five-second analysis timeout, and safe decoding for invalid JSON or backend errors.

```python
request_analysis(sample_collection(), base_url, session=session)
self.assertEqual(
    session.post_call[1],
    {"source": sample_collection()["source"], "reviews": sample_collection()["reviews"]},
)
self.assertNotIn("provider", session.post_call[1])
```

- [ ] **Step 2: Run focused client tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardClientTests -v
```

Expected: missing functions and old provider payload.

- [ ] **Step 3: Implement a shared safe request decoder**

Keep curated `BackendUnavailable` and `ApiClientError`. Factor response decoding without exposing response bodies, then implement the five endpoint functions with stage-appropriate timeouts and strict dict/list shape checks.

- [ ] **Step 4: Run focused client tests**

Run the command from Step 2.

Expected: all dashboard client tests pass.

- [ ] **Step 5: Commit**

```powershell
git add dashboard/api_client.py tests/test_dashboard_mvp.py
git commit -m "refactor: support staged dashboard API calls"
```

### Task 8: Build the Presentation-Ready Streamlit Flow

**Files:**
- Modify: `dashboard/streamlit_app.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Produces: pure `sentiment_visual(sentiment)`, `review_rows(collection, report=None)`, `history_option(item)`, and shared report rendering helpers plus the staged Streamlit `main()`.
- Consumes: the Task 7 client functions.

- [ ] **Step 1: Write failing presentation-helper tests**

Assert known sentiments map to icon, label, foreground, background, and border tokens; positive is green, negative red, neutral amber/gray, mixed distinct; all include text labels/icons; themes carry sentiment; and rendered HTML escapes untrusted title/theme/review text.

```python
positive = sentiment_visual("positive")
self.assertEqual(positive.label, "Positive")
self.assertEqual(positive.icon, "✅")
self.assertIn("green", positive.semantic_name)
self.assertNotEqual(sentiment_visual("neutral").background, positive.background)
```

Add a retained-source test confirming the Streamlit file contains no radio/selectbox labeled provider and no Gemini/Google provider text.

- [ ] **Step 2: Run focused formatting tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardFormattingTests -v
```

Expected: missing helpers and old provider radio.

- [ ] **Step 3: Implement staged session-state flow**

Use separate actions for **Extract reviews**, **Use bundled demo data**, and **Analyze with Groq**. Clear stale results on a new collection attempt. Store the collected payload under `st.session_state["collection"]`, display it immediately, and show the analyze button only when a valid collection exists. Never call demo loading from an exception path.

- [ ] **Step 4: Implement accessible visual report components**

Use escaped HTML for badges/cards and Streamlit containers for content. Render:

- source/extractor badge and persistent `🧪 DEMO DATA` warning;
- extracted reviews before analysis;
- metric cards and labeled overall sentiment;
- green `✅ Strengths`, red `⚠️ Complaints`, sentiment-colored theme cards, neutral/mixed styles, and blue action cards;
- review-level sentiment labels after analysis;
- current report and history-selected report through the same renderer.

- [ ] **Step 5: Add history navigation**

Load recent history into the sidebar or a dedicated tab, format each option with timestamp/title/sentiment, fetch only the selected report, and render a clear empty state or safe API error.

- [ ] **Step 6: Run dashboard tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: all dashboard tests pass.

- [ ] **Step 7: Commit**

```powershell
git add dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: add staged accessible Streamlit experience"
```

### Task 9: Update Documentation and Enforce Groq-Only Source

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Modify: `tests/test_documentation.py`
- Modify: `tests/test_run_app.py` only if launcher copy or route expectations changed
- Delete: `docs/superpowers/plans/2026-07-13-single-command-credential-preflight.md`
- Delete: `docs/superpowers/specs/2026-07-13-single-command-credential-preflight-design.md`
- Delete: `docs/superpowers/plans/2026-07-13-env-browser-launch.md`
- Delete: `docs/superpowers/specs/2026-07-13-env-browser-launch-design.md`

**Interfaces:**
- Documents: architecture, commands, `GROQ_API_KEY`, model override, endpoints, history path, demo procedure, errors, and limits.
- Enforces: no retained Gemini/Google provider configuration or provider-selection language.

- [ ] **Step 1: Write failing documentation/source audit tests**

Search retained runtime, dependency, example, and current documentation files for `Gemini`, `GOOGLE_API_KEY`, `REVIEWINSIGHT_GOOGLE_MODEL`, `langchain_google_genai`, `langchain-google-genai`, and provider-selection UI phrases. Exclude historical approved specs/plans from the assertion.

- [ ] **Step 2: Run documentation tests and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation tests.test_run_app -v
```

Expected: failures from current README, architecture, status, dependencies, and provider source.

- [ ] **Step 3: Rewrite current documentation**

Document the retained two-process topology, staged endpoints, SQLite history, explicit demo behavior, safe errors, exact install/test/launch commands, Groq-only environment, and static-only limitations. Preserve `.env` precedence and automatic browser-open launcher behavior. Remove the four superseded 2026-07-13 design/plan files so current repository documentation does not present Gemini/provider selection as an active design.

- [ ] **Step 4: Run documentation and launcher tests**

Run the command from Step 2.

Expected: all documentation and launcher tests pass.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/architecture.md docs/project_status.md tests/test_documentation.py tests/test_run_app.py docs/superpowers
git commit -m "docs: document Groq-only review intelligence MVP"
```

### Task 10: Research and Verify Live Sources and Open Datasets

**Files:**
- Create: `docs/demo_sources.md`
- Optionally create: `scripts/verify_demo_urls.py`
- Create or modify: `tests/test_live_source_documentation.py`

**Interfaces:**
- Produces: a verified exact-URL list with extractor/result notes and an open-dataset assessment.
- Consumes: completed `collect_reviews`; does not hardcode extraction output into runtime code.

- [ ] **Step 1: Record candidate-source verification requirements**

Add a documentation test requiring each verified entry to include an exact HTTPS URL, access date, extractor (`json_ld` or `html_cards`), review count, rating/full-text notes, and no login/automation warning. Require dataset entries to state access method, authentication, licensing link, product identifier support, and suitability as live target versus demo-corpus source.

- [ ] **Step 2: Run the documentation test and verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_live_source_documentation -v
```

Expected: failure because `docs/demo_sources.md` does not exist.

- [ ] **Step 3: Test candidate URLs with the completed collector**

Run each exact candidate through the completed collector. For the current known
practice-site candidate, use:

```powershell
.\.venv\Scripts\python.exe -c "from backend.app.collector import collect_reviews; r=collect_reviews('https://web-scraping.dev/product/1'); print(r.source.extractor, len(r.reviews), r.source.title)"
```

Repeat with each exact URL returned by the candidate research, changing only the
quoted URL. Exclude every URL that times out, is blocked, requires
login/JavaScript, returns fewer than two full reviews, changes unpredictably, or
needs circumvention. Never paste extracted review bodies into source code.

- [ ] **Step 4: Complete dataset research**

Use official Kaggle, dataset publisher, Hugging Face, or academic-host documentation to determine whether product-specific review retrieval is anonymous and stable. Clearly separate:

- sources appropriate for downloading/curating a local demo corpus;
- sources with anonymous product-level APIs;
- sources unsuitable for the live URL scraper because they require credentials, archives, JavaScript, or a separate API adapter.

- [ ] **Step 5: Write only verified findings**

Create `docs/demo_sources.md` with successful exact live URLs and evidence from the actual collector run, followed by the dataset assessment and direct source/license links.

- [ ] **Step 6: Run the documentation test**

Run the command from Step 2.

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add docs/demo_sources.md scripts/verify_demo_urls.py tests/test_live_source_documentation.py
git commit -m "docs: add verified review sources and dataset options"
```

If the optional script is not needed, omit it from both `git add` and the repository.

### Task 11: Full Automated Verification and Chrome Smoke Test

**Files:**
- Modify: only files implicated by failures found during verification
- Update: `docs/project_status.md` with final verification facts

**Interfaces:**
- Verifies: complete test suite, syntax compilation, live source behavior, local runtime, Groq call, UI visuals, history, explicit demo, and error states.

- [ ] **Step 1: Run the full automated suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: all tests pass and compilation exits zero.

- [ ] **Step 2: Check configuration without exposing it**

Load the existing project environment and report only whether `GROQ_API_KEY` is nonblank. Never print the value.

- [ ] **Step 3: Start the supervised application**

```powershell
.\.venv\Scripts\python.exe run_app.py
```

Expected: FastAPI on `127.0.0.1:8000`, Streamlit on `127.0.0.1:8501`, both healthy.

- [ ] **Step 4: Open the local app in installed Google Chrome**

Use the existing Chrome executable and the machine's normal Chrome profile/session. Do not use Codex's in-app browser or introduce Selenium/Playwright.

- [ ] **Step 5: Manually verify the full Chrome flow**

Verify page loading, URL extraction, visible reviews before analysis, Groq analysis, positive/negative/neutral labels and colors, summaries/themes/strengths/complaints, history persistence after reload, opening a historical run, explicit demo labeling, and the fact that failed live scraping never loads demo data.

- [ ] **Step 6: Verify representative errors**

Check malformed URL, a page with no reviews, missing-key behavior using a safe isolated process/test override, and one blocked/timeout case when reproducible. Confirm messages are actionable and contain no raw provider response, credential, header, exception, or traceback.

- [ ] **Step 7: Fix and retest every observed issue**

For each issue, add or tighten a focused regression test first, make the smallest correction, rerun that test, then repeat the affected Chrome path.

- [ ] **Step 8: Record final status and commit**

Update `docs/project_status.md` with test count, live URLs, Chrome smoke-test date, Groq model, history behavior, and remaining limitations.

```powershell
git add docs/project_status.md
git commit -m "chore: record presentation-ready MVP verification"
```

- [ ] **Step 9: Inspect final repository state**

```powershell
git status --short
git log -8 --oneline --decorate
git diff HEAD~1 --check
```

Expected: clean worktree, intentional commit history, and no whitespace errors.
