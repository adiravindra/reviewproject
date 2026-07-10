# Website Review Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-review Hugging Face application with one synchronous, bounded public-URL-to-website-review-intelligence workflow.

**Architecture:** FastAPI accepts a website URL, validates every network destination, performs bounded static HTTP retrieval, and passes fetched pages through a registry that prefers JSON-LD over conservative HTML review cards. Normalized reviews feed deterministic metrics and a provider-neutral LangChain batch/synthesis service; only a fully validated response is atomically stored in a website-level SQLite history table and rendered by Streamlit.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, requests, Beautiful Soup 4, LangChain Core, langchain-google-genai, langchain-groq, SQLite, Streamlit, unittest.

**Test convention:** Test snippets below are methods placed inside focused `unittest.TestCase` classes; repeated class shells and standard-library imports are omitted only to keep the plan readable.

## Global Constraints

- The only active analysis workflow is synchronous `POST /analysis/website`; remove `/analysis/single`, `/analysis/batch`, and all local/Hugging Face fallbacks.
- Accept only public `http` and `https` URLs without credentials; reject loopback, private, link-local, reserved, multicast, unspecified, or otherwise non-global resolved addresses, and revalidate every redirect target.
- Fetch static HTML only. Do not add Playwright, Selenium, browser rendering, anti-bot bypasses, or fabricated review extraction.
- Default limits are 2 MiB per page, three same-origin pages, 25 seconds scraping, 60 analyzed reviews, batches of 15, four batch calls, one synthesis call, five total LLM calls, 20 seconds per provider call, 120 seconds overall, and two minimum reviews.
- Keep safe hard ceilings in code; environment overrides may only make demo limits stricter than or equal to the documented hard ceiling.
- Apply cleaning and case-insensitive exact deduplication before the 60-review cap; preserve original wording and author metadata, but never include authors in prompts.
- Run JSON-LD/Schema.org extraction first and static HTML review-card extraction second through a scraper registry.
- Continue after later-page failure only when at least two valid unique reviews have already been collected; surface explicit partial-success warnings and found-versus-analyzed counts.
- Compute counts, average rating, 1–5 star distribution, sentiment counts, and overall sentiment in application code, never in the LLM.
- Default to Google Gemini model `gemini-2.5-flash-lite`; support Groq by environment configuration; isolate provider imports and construction behind one factory.
- Validate structured batch and synthesis outputs, enforce the five-call ceiling, and resolve representative IDs to stored normalized review text.
- Persist once, after complete response validation; failed scraping, analysis, or validation must create no website history row.
- API failures use `{\"error\": {\"code\", \"message\", \"stage\", \"retryable\", \"details\"}}` and never expose raw internal/provider errors or secrets.
- Tests use fixtures, fake fetchers, fake structured models, and temporary SQLite databases; they do not call live sites or real model providers.
- Work in the current checkout, commit each meaningful stage, and do not push.

## File Structure

- Delete `backend/app/services/model_runtime.py`, `model_sentiment.py`, `model_summarizer.py`, `sentiment.py`, `summarization.py`, and `processing.py`: obsolete local single-review/model code.
- Replace `backend/app/schemas/reviews.py` with `backend/app/schemas/website.py`: public request, response, history, normalized review, batch, and synthesis contracts.
- Create `backend/app/settings.py`: environment parsing, defaults, and hard ceilings.
- Create `backend/app/errors.py`: typed application errors, code/status mapping, and FastAPI handler.
- Create `backend/app/services/normalization.py`: cleaning, rating normalization, stable IDs, invalid filtering, deduplication, and caps.
- Create `backend/app/services/metrics.py`: deterministic rating/sentiment metrics.
- Create `backend/app/services/url_safety.py`: URL parsing, DNS resolution, public-address checks, and same-origin comparison.
- Create `backend/app/services/fetching.py`: redirect-safe streamed static HTTP fetches with size/time/content/block checks.
- Create `backend/app/scrapers/base.py`, `jsonld.py`, `static_html.py`, and `registry.py`: provider-neutral extraction extension point and ordered extractors.
- Create `backend/app/services/scraping.py`: bounded pagination orchestration, partial-success rules, and collection metadata.
- Create `backend/app/services/providers.py`: LangChain Gemini/Groq factory only.
- Replace `backend/app/services/analysis.py`: provider-neutral batch prompts, structured validation, call budget, synthesis, and representative-ID resolution.
- Create `backend/app/services/orchestration.py`: deadline-aware end-to-end workflow and save-after-validation boundary.
- Replace `backend/app/services/db.py` and `history.py`: website-only table for fresh databases and complete-payload history.
- Replace `backend/app/routers/reviews.py` with `backend/app/routers/website.py`; update `backend/app/main.py` with error handlers and only website routes.
- Replace `dashboard/api_client.py`, `ui.py`, `streamlit_app.py`, and `pages/1_History.py`: URL submission, structured errors, dashboard, and stored report history.
- Replace `tests/test_model_wrappers.py` with focused modules and add deterministic HTML fixtures under `tests/fixtures/`.
- Update `requirements.txt`, add `.env.example`, and rewrite `README.md`, `docs/architecture.md`, and `docs/project_status.md` for the only active workflow.

---

### Task 1: Remove the obsolete workflow and establish the new module boundary

**Files:**
- Delete: `backend/app/services/model_runtime.py`
- Delete: `backend/app/services/model_sentiment.py`
- Delete: `backend/app/services/model_summarizer.py`
- Delete: `backend/app/services/sentiment.py`
- Delete: `backend/app/services/summarization.py`
- Delete: `backend/app/services/processing.py`
- Delete: `backend/app/schemas/reviews.py`
- Delete: `backend/app/routers/reviews.py`
- Delete: `tests/test_model_wrappers.py`
- Delete: `reviews/real_reviews/extract_amazon_reviews23_sample.py`
- Delete: `reviews/real_reviews/generated/real_review_samples.jsonl`
- Delete: `reviews/real_reviews/README.md`
- Delete: `reviews/real_reviews/real_review_sources.md`
- Delete: `reviews/real_reviews/synthetic_style_review_examples.md`
- Delete: `reviews/manual_test_cases/custom_review_evaluation_cases.md`
- Modify: `scripts/run_app.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/routers/website.py`
- Create: `backend/app/schemas/website.py`
- Test: `tests/test_active_routes.py`

**Interfaces:**
- Consumes: current FastAPI app and combined runner.
- Produces: `WebsiteAnalysisRequest(url: str)` and a temporary `POST /analysis/website` route returning HTTP 501; runner starts services without model warmup.

- [ ] **Step 1: Write the failing active-route test**

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_only_website_analysis_workflow_is_routed() -> None:
    paths = {route.path for route in app.routes}
    assert "/analysis/website" in paths
    assert "/analysis/single" not in paths
    assert "/analysis/batch" not in paths
```

- [ ] **Step 2: Run the test and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_active_routes -v`

Expected: FAIL because `/analysis/website` does not exist and the old routes do.

- [ ] **Step 3: Remove obsolete files and create the smallest new boundary**

```python
# backend/app/routers/website.py
from fastapi import APIRouter, HTTPException
from backend.app.schemas.website import WebsiteAnalysisRequest

router = APIRouter(prefix="/analysis", tags=["website analysis"])

@router.post("/website")
def analyze_website(_: WebsiteAnalysisRequest) -> None:
    raise HTTPException(status_code=501, detail="Website analysis is not implemented yet.")
```

Update `main.py` to include only this router. Remove `ensure_models_ready()` and all model imports/calls from `scripts/run_app.py` while retaining backend/frontend process startup and shutdown.

- [ ] **Step 4: Run the route test and repository reference check**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_active_routes -v`

Expected: PASS.

Run: `rg -n "analysis/(single|batch)|transformers|torch|Hugging Face|model warm|rule_based_fallback" backend dashboard scripts tests requirements.txt`

Expected: no active-code/dependency matches.

- [ ] **Step 5: Commit the obsolete-flow removal**

```powershell
git add -A
git commit -m "refactor: remove obsolete single-review workflow"
```

### Task 2: Add settings, public schemas, error contracts, normalization, and deterministic metrics

**Files:**
- Create: `backend/app/settings.py`
- Create: `backend/app/errors.py`
- Modify: `backend/app/schemas/website.py`
- Create: `backend/app/services/normalization.py`
- Create: `backend/app/services/metrics.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_settings.py`
- Test: `tests/test_normalization.py`
- Test: `tests/test_metrics.py`
- Test: `tests/test_errors.py`

**Interfaces:**
- Consumes: `WebsiteAnalysisRequest` from Task 1.
- Produces: `Settings.from_env()`, `AppError`, all website response schemas, `normalize_reviews(candidates, max_reviews) -> NormalizationResult`, and `calculate_metrics(found_count, normalization, sentiments) -> ReviewMetrics`.

- [ ] **Step 1: Write failing settings and error-envelope tests**

```python
def test_settings_use_documented_defaults_and_clamp_hard_ceilings() -> None:
    with patch.dict(os.environ, {"REVIEWINSIGHT_MAX_REVIEWS": "999"}, clear=True):
        settings = Settings.from_env()
    assert settings.max_reviews == 60
    assert settings.max_pages == 3
    assert settings.max_response_bytes == 2 * 1024 * 1024
    assert settings.max_llm_calls == 5

def test_app_error_uses_consistent_safe_envelope() -> None:
    response = TestClient(app).post("/analysis/website", json={"url": "file:///etc/passwd"})
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["code"] == "invalid_url"
    assert set(response.json()["error"]) == {"code", "message", "stage", "retryable", "details"}
```

- [ ] **Step 2: Run settings/error tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_settings tests.test_errors -v`

Expected: FAIL because settings and typed error handling do not exist.

- [ ] **Step 3: Implement bounded settings and typed errors**

Define frozen `Settings` fields for every documented limit, provider/model/database configuration, request user agent, and frontend-adjacent timeout. `from_env()` parses positive numeric overrides and clamps them to constants such as `HARD_MAX_REVIEWS = 60`, `HARD_MAX_PAGES = 3`, `HARD_MAX_LLM_CALLS = 5`, and `HARD_MAX_RESPONSE_BYTES = 2 * 1024 * 1024`. Define `AppError(code, message, stage, status_code, retryable=False, details=None)` and one FastAPI exception handler returning the approved envelope.

- [ ] **Step 4: Write failing normalization and metric tests**

```python
def test_normalization_cleans_deduplicates_scales_ratings_and_caps() -> None:
    result = normalize_reviews([
        ExtractionCandidate(text="  Great   stay. ", rating=8, rating_scale=10, author="Ada"),
        ExtractionCandidate(text="great stay.", rating=4, rating_scale=5),
        ExtractionCandidate(text=" "),
        ExtractionCandidate(text="Quiet room", rating=3, rating_scale=5),
    ], max_reviews=1)
    assert result.found_count == 4
    assert result.valid_count == 2
    assert result.duplicates_removed == 1
    assert result.invalid_removed == 1
    assert result.omitted_by_cap == 1
    assert result.reviews[0].rating == 4.0
    assert result.reviews[0].author == "Ada"

def test_metrics_are_deterministic_and_bucket_half_up() -> None:
    metrics = calculate_metrics(
        found_count=4,
        valid_count=3,
        reviews=[review(1.49), review(2.50), review(None)],
        sentiments={"r1": "positive", "r2": "negative", "r3": "neutral"},
    )
    assert metrics.average_rating == 2.0
    assert metrics.rating_distribution == {"1": 1, "2": 0, "3": 1, "4": 0, "5": 0}
    assert metrics.sentiment_counts.model_dump() == {"positive": 1, "neutral": 1, "negative": 1}
    assert metrics.overall_sentiment == "mixed"
```

- [ ] **Step 5: Run normalization/metric tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_normalization tests.test_metrics -v`

Expected: FAIL because cleaning, stable IDs, rating scaling, and deterministic metrics do not exist.

- [ ] **Step 6: Implement schemas, normalization, and metrics**

Use SHA-256-derived internal IDs from normalized text/rating/date/source fields; retain cleaned author metadata; discard blank or implausibly short/non-text reviews; scale valid positive ratings to 1–5; deduplicate by `cleaned_text.casefold()`; cap only after filtering. Bucket ratings with `Decimal(...).quantize(Decimal("1"), ROUND_HALF_UP)` and derive overall sentiment as the sole leading class, `mixed` for any top-count tie.

- [ ] **Step 7: Run all Task 2 tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_settings tests.test_errors tests.test_normalization tests.test_metrics -v`

Expected: PASS.

```powershell
git add backend tests
git commit -m "feat: add website analysis contracts and normalization"
```

### Task 3: Add SSRF-safe fetching, scraper registry, extraction, and bounded pagination

**Files:**
- Create: `backend/app/services/url_safety.py`
- Create: `backend/app/services/fetching.py`
- Create: `backend/app/scrapers/__init__.py`
- Create: `backend/app/scrapers/base.py`
- Create: `backend/app/scrapers/jsonld.py`
- Create: `backend/app/scrapers/static_html.py`
- Create: `backend/app/scrapers/registry.py`
- Create: `backend/app/services/scraping.py`
- Create: `tests/fixtures/jsonld_direct.html`
- Create: `tests/fixtures/jsonld_nested.html`
- Create: `tests/fixtures/static_cards_page_1.html`
- Create: `tests/fixtures/static_cards_page_2.html`
- Create: `tests/fixtures/unsupported.html`
- Test: `tests/test_url_safety.py`
- Test: `tests/test_fetching.py`
- Test: `tests/test_scrapers.py`
- Test: `tests/test_scraping.py`

**Interfaces:**
- Consumes: `Settings`, `AppError`, `ExtractionCandidate`, and normalization from Task 2.
- Produces: `validate_public_url(url, resolver=socket.getaddrinfo) -> ValidatedURL`, `StaticHttpFetcher.fetch(url, deadline) -> FetchedPage`, `ScraperRegistry.extract(page) -> ExtractionResult`, and `collect_reviews(url, fetcher, registry, settings, clock) -> ScrapeResult`.

- [ ] **Step 1: Write failing URL-safety tests**

```python
def test_rejects_credentials_loopback_private_and_non_http_urls() -> None:
    resolver = fake_resolver({"public.example": "203.0.113.10", "private.example": "10.0.0.2"})
    for url in ["ftp://public.example/x", "http://u:p@public.example/x", "http://127.0.0.1", "http://private.example"]:
        with self.assertRaises(AppError) as raised:
            validate_public_url(url, resolver=resolver)
        assert raised.value.code == "invalid_url"

def test_redirect_targets_are_revalidated_before_following() -> None:
    session = FakeSession([redirect("http://127.0.0.1/admin")])
    with self.assertRaises(AppError) as raised:
        StaticHttpFetcher(settings, session=session, resolver=public_resolver).fetch("https://public.example/reviews")
    assert raised.value.code == "invalid_url"
```

- [ ] **Step 2: Run URL/fetch tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_url_safety tests.test_fetching -v`

Expected: FAIL because public destination validation and bounded fetching do not exist.

- [ ] **Step 3: Implement public URL validation and streamed fetching**

Validate syntax and all DNS answers with `ipaddress.ip_address(address).is_global`; compare normalized `(scheme, hostname, effective_port)` origins. Fetch with `allow_redirects=False`, a tuple connection/read timeout, `stream=True`, explicit user agent and accepted HTML headers, a small redirect ceiling, and byte counting over `iter_content`. Reject non-HTML content, oversized bodies, 401/403/407/429 denials, 5xx errors, and recognizable challenge/anti-bot markup with safe `AppError` codes.

- [ ] **Step 4: Write failing extraction and priority tests**

```python
def test_jsonld_handles_direct_list_and_nested_entities() -> None:
    direct = JsonLdScraper().extract(page_from_fixture("jsonld_direct.html"))
    nested = JsonLdScraper().extract(page_from_fixture("jsonld_nested.html"))
    assert [item.text for item in direct.candidates] == ["Excellent grinder.", "Hard to clean."]
    assert nested.entity_name == "Harbor Hotel"
    assert nested.candidates[0].rating == 8
    assert nested.candidates[0].rating_scale == 10

def test_registry_prefers_jsonld_and_static_html_is_conservative() -> None:
    result = default_registry().extract(page_with_jsonld_and_review_cards())
    assert result.scraper_name == "json_ld"
    unsupported = default_registry().extract(page_from_fixture("unsupported.html"))
    assert unsupported.candidates == []
```

- [ ] **Step 5: Run scraper tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_scrapers -v`

Expected: FAIL because registry and extractors do not exist.

- [ ] **Step 6: Implement ordered extractors and trustworthy pagination links**

Parse all `application/ld+json` blocks, recursively traverse dict/list nodes, recognize `Review` plus review-bearing schema entities, and capture body/rating/bestRating/author/date/url/name/type. The static extractor may use `itemprop=review`, `itemtype*=Review`, review-specific class/data-testid patterns, and nested body/rating/author/date fields, but never arbitrary paragraphs. Extract `rel=next` or review-pagination links only when same-origin validation succeeds.

- [ ] **Step 7: Write failing pagination, bounds, and partial-success tests**

```python
def test_same_origin_pagination_stops_at_page_and_review_caps() -> None:
    result = collect_reviews("https://public.example/p1", fixture_fetcher, default_registry(), settings(max_pages=2, max_reviews=3))
    assert result.pages_attempted == 2
    assert result.pages_succeeded == 2
    assert result.normalization.analyzed_count == 3
    assert result.normalization.omitted_by_cap > 0

def test_later_page_failure_is_partial_only_after_minimum_reviews() -> None:
    result = collect_reviews("https://public.example/p1", fetcher_failing_on_page_2_after_two_reviews, registry, settings())
    assert result.partial_success is True
    assert "Some later review pages could not be collected." in result.warnings
    with self.assertRaises(AppError) as raised:
        collect_reviews("https://public.example/one-review", fetcher_failing_on_page_2, registry, settings())
    assert raised.value.code == "scrape_failed"
```

- [ ] **Step 8: Run pagination tests and verify RED, then implement orchestration**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_scraping -v`

Expected before implementation: FAIL because pagination orchestration does not exist.

Implement one global scrape deadline, same-origin next-page following, visited-URL loop detection, page attempt/success counters, first-page hard failure, partial later-page behavior only after normalization proves at least two valid unique reviews, low-sample warnings below five, and explicit `unsupported_source`, `no_reviews_found`, and `insufficient_reviews` distinctions.

- [ ] **Step 9: Run Task 3 tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_url_safety tests.test_fetching tests.test_scrapers tests.test_scraping -v`

Expected: PASS.

```powershell
git add backend tests
git commit -m "feat: add bounded public website scraping"
```

### Task 4: Add deterministic LangChain provider and bounded structured analysis

**Files:**
- Create: `backend/app/services/providers.py`
- Replace: `backend/app/services/analysis.py`
- Test: `tests/test_providers.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Consumes: normalized reviews, settings, batch/synthesis Pydantic schemas, and `AppError`.
- Produces: `create_chat_model(settings) -> BaseChatModel`, `analyze_collection(reviews, model, settings) -> AnalysisResult`, and a prompt builder that serializes only review ID, text, rating, and publication date.

- [ ] **Step 1: Write failing provider-factory tests**

```python
def test_factory_defaults_to_gemini_and_supports_groq() -> None:
    with patch("backend.app.services.providers.ChatGoogleGenerativeAI") as gemini:
        create_chat_model(settings(provider="google", model="gemini-2.5-flash-lite"))
        gemini.assert_called_once_with(model="gemini-2.5-flash-lite", timeout=20, max_retries=0)
    with patch("backend.app.services.providers.ChatGroq") as groq:
        create_chat_model(settings(provider="groq", model="llama-3.3-70b-versatile"))
        groq.assert_called_once_with(model="llama-3.3-70b-versatile", timeout=20, max_retries=0)

def test_factory_reports_missing_credentials_without_import_leakage() -> None:
    with patch.dict(os.environ, {}, clear=True), self.assertRaises(AppError) as raised:
        create_chat_model(settings(provider="google"))
    assert raised.value.code == "llm_failed"
    assert "GOOGLE_API_KEY" in raised.value.message
```

- [ ] **Step 2: Run provider tests and verify RED, then implement the isolated factory**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_providers -v`

Expected before implementation: FAIL because provider construction does not exist.

Import provider classes only in `providers.py`, validate `GOOGLE_API_KEY` or `GROQ_API_KEY`, select `REVIEWINSIGHT_LLM_PROVIDER` and `REVIEWINSIGHT_LLM_MODEL`, disable provider retries, and convert construction failures to safe `llm_failed` errors.

- [ ] **Step 3: Write failing batch, prompt, validation, and synthesis tests**

```python
def test_batches_are_bounded_authors_are_excluded_and_ids_are_complete() -> None:
    model = FakeStructuredModel(valid_batch_outputs(31), valid_synthesis())
    result = analyze_collection(reviews(31, author="Secret Author"), model, settings(batch_size=15))
    assert model.batch_sizes == [15, 15, 1]
    assert all("Secret Author" not in prompt for prompt in model.prompts)
    assert result.batch_count == 3
    assert result.call_count == 4

def test_invalid_structured_output_retries_only_within_five_call_budget() -> None:
    model = FakeStructuredModel([invalid_missing_sentiment(), valid_batch()], valid_synthesis())
    assert analyze_collection(reviews(15), model, settings()).call_count == 3
    four_batch_model = FakeStructuredModel([invalid_missing_sentiment()], valid_synthesis())
    with self.assertRaises(AppError) as raised:
        analyze_collection(reviews(60), four_batch_model, settings())
    assert raised.value.code == "llm_failed"
    assert four_batch_model.call_count <= 5

def test_representative_ids_resolve_to_original_text_and_unknown_ids_fail() -> None:
    result = analyze_collection(reviews_with_known_text(), model_selecting_ids(["r-positive"]), settings())
    assert result.insights.representative_reviews[0].text == "Original customer wording."
    with self.assertRaises(AppError):
        analyze_collection(reviews_with_known_text(), model_selecting_ids(["invented"]), settings())
```

- [ ] **Step 4: Run analysis tests and verify RED, then implement map/synthesis**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_analysis -v`

Expected before implementation: FAIL because structured collection analysis does not exist.

Use `model.with_structured_output(BatchAnalysisOutput)` and `model.with_structured_output(SynthesisOutput)` behind a small injectable protocol. Validate exact one-to-one sentiment coverage per batch, all supporting IDs, all synthesis representative IDs, and all call/time ceilings. Synthesis receives only validated batch structures; application code resolves representative IDs and calculates sentiment counts/overall sentiment.

- [ ] **Step 5: Run Task 4 tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_providers tests.test_analysis tests.test_metrics -v`

Expected: PASS.

```powershell
git add backend tests
git commit -m "feat: add bounded LangChain review intelligence"
```

### Task 5: Add the synchronous website endpoint and atomic website history

**Files:**
- Replace: `backend/app/services/db.py`
- Replace: `backend/app/services/history.py`
- Create: `backend/app/services/orchestration.py`
- Modify: `backend/app/routers/website.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_history.py`
- Test: `tests/test_orchestration.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: scraping, structured analysis, metrics, provider factory, website schemas, and settings.
- Produces: `run_website_analysis(url, dependencies) -> WebsiteAnalysisResponse`, `save_website_analysis(response)`, `list_website_analyses(limit)`, `get_website_analysis(run_id)`, `POST /analysis/website`, `GET /analysis/history`, and `GET /analysis/history/{run_id}`.

- [ ] **Step 1: Write failing database and atomicity tests**

```python
def test_fresh_database_creates_only_active_website_table(tmp_path) -> None:
    with database_at(tmp_path / "history.db"):
        with connect() as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "website_analysis_runs" in tables
    assert "analysis_runs" not in tables

def test_only_complete_validated_response_is_saved(tmp_path) -> None:
    response = complete_response()
    save_website_analysis(response)
    assert get_website_analysis(response.id) == response
    with self.assertRaises(AppError):
        run_website_analysis("https://public.example", dependencies(llm=failed_llm()))
    assert len(list_website_analyses().items) == 1
```

- [ ] **Step 2: Run history/orchestration tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_history tests.test_orchestration -v`

Expected: FAIL because the website table and save-after-validation orchestrator do not exist.

- [ ] **Step 3: Implement one-transaction persistence and deadline-aware orchestration**

Create `website_analysis_runs(id, completed_at, source_url, entity_name, review_count, average_rating, overall_sentiment, executive_summary, provider, model, payload_json)`. Preserve a pre-existing legacy `analysis_runs` table by never dropping or reading it. Validate a complete `WebsiteAnalysisResponse` before one transaction/commit. The orchestrator checks a monotonic 120-second deadline between scrape, batch, synthesis, metrics, validation, and save stages; timeout maps to `request_timeout` and never saves.

- [ ] **Step 4: Write failing API success/history/error tests**

```python
def test_post_website_returns_complete_contract_and_history_can_reload_it(client, fake_dependencies) -> None:
    response = client.post("/analysis/website", json={"url": "https://public.example/reviews"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["collection"]["found"] >= payload["collection"]["analyzed"]
    assert client.get("/analysis/history").json()["items"][0]["id"] == payload["id"]
    assert client.get(f"/analysis/history/{payload['id']}").json() == payload

def test_all_supported_failures_use_error_envelope(client, failing_dependencies) -> None:
    for code in ["invalid_url", "unsupported_source", "blocked_source", "no_reviews_found", "insufficient_reviews", "scrape_failed", "llm_failed", "request_timeout"]:
        response = client.post("/analysis/website", json={"url": failing_dependencies.url_for(code)})
        assert response.json()["error"]["code"] == code
```

- [ ] **Step 5: Run API tests and verify RED, then implement routes/dependency wiring**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api -v`

Expected before implementation: FAIL because route orchestration and website history routes are incomplete.

Wire production dependencies in a replaceable factory so tests inject fake fetching and fake structured models. Map Pydantic request validation failures into the same `invalid_url` envelope, cap history limits to 1–200, return 404 structured errors for unknown history IDs, and leave internal error text out of responses.

- [ ] **Step 6: Run Task 5 tests and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_history tests.test_orchestration tests.test_api -v`

Expected: PASS.

```powershell
git add backend tests
git commit -m "feat: add website analysis API and history"
```

### Task 6: Replace Streamlit with the URL dashboard and website history

**Files:**
- Replace: `dashboard/api_client.py`
- Replace: `dashboard/ui.py`
- Replace: `dashboard/streamlit_app.py`
- Replace: `dashboard/pages/1_History.py`
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: website API success/error and history contracts.
- Produces: `analyze_website(url, api_base_url)`, `fetch_history`, `fetch_history_item`, `ApiClientError` preserving code/stage/retryable/details, `dashboard_metrics`, `history_rows`, and `render_website_report`.

- [ ] **Step 1: Write failing API-client and formatting tests**

```python
def test_client_posts_url_and_preserves_structured_backend_error() -> None:
    response = FakeResponse(403, {"error": {"code": "blocked_source", "message": "The website blocked automated access.", "stage": "scraping", "retryable": False, "details": {}}})
    with patch("dashboard.api_client.requests.post", return_value=response) as post, self.assertRaises(ApiClientError) as raised:
        analyze_website("https://public.example/reviews")
    post.assert_called_once_with(ANY, json={"url": "https://public.example/reviews"}, timeout=130)
    assert raised.value.code == "blocked_source"
    assert raised.value.stage == "scraping"

def test_dashboard_helpers_format_counts_warnings_and_history() -> None:
    metrics = dashboard_metrics(complete_payload())
    assert metrics["Reviews"] == "12 analyzed / 18 found"
    assert history_rows({"items": [history_summary()]})[0]["Source"] == "Harbor Hotel"
```

- [ ] **Step 2: Run dashboard tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard -v`

Expected: FAIL because the client and UI still implement single-review behavior.

- [ ] **Step 3: Implement URL-first client, dashboard, and history UI**

Use a URL text input, one `Analyze Reviews` action, a single honest spinner stating that page access/collection/analysis may take up to two minutes, success only after the complete response arrives, and warning rendering from `collection.warnings`. Render deterministic metrics and charts separately from LLM insights; render representative stored text, expandable normalized reviews, and optional raw JSON. History lists website summaries and lazily loads the complete stored report when an entry is expanded, without rerunning analysis.

- [ ] **Step 4: Run dashboard tests, import checks, and commit**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard -v`

Expected: PASS.

Run: `.\.venv\Scripts\python.exe -c "import dashboard.api_client, dashboard.ui; print('dashboard imports ok')"`

Expected: `dashboard imports ok`.

```powershell
git add dashboard tests
git commit -m "feat: build website review intelligence dashboard"
```

### Task 7: Complete integration coverage, dependencies, environment example, and documentation

**Files:**
- Create: `tests/test_end_to_end.py`
- Modify: `requirements.txt`
- Create: `.env.example`
- Replace: `README.md`
- Replace: `docs/architecture.md`
- Replace: `docs/project_status.md`
- Delete: `docs/model_research.md`

**Interfaces:**
- Consumes: complete backend/frontend implementation.
- Produces: fixture-driven end-to-end proof, reproducible setup/configuration, current architecture/run documentation, and honest demonstration-source status.

- [ ] **Step 1: Write and run the failing fixture-driven end-to-end test**

```python
def test_public_url_to_saved_dashboard_payload_end_to_end(tmp_path) -> None:
    dependencies = fixture_dependencies(
        pages=["static_cards_page_1.html", "static_cards_page_2.html"],
        batch_outputs=valid_batch_outputs(),
        synthesis=valid_synthesis_output(),
        database=tmp_path / "reviewinsight.db",
    )
    response = TestClient(create_app(dependencies)).post(
        "/analysis/website", json={"url": "https://public.example/reviews"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["collection"]["found"] == 6
    assert payload["metrics"]["sentiment_counts"] == {"positive": 3, "neutral": 1, "negative": 2}
    assert payload["insights"]["representative_reviews"][0]["text"] in {item["text"] for item in payload["reviews"]}
    assert TestClient(create_app(dependencies)).get(f"/analysis/history/{payload['id']}").json() == payload
```

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_end_to_end -v`

Expected before any integration corrections: FAIL at the first contract mismatch revealed across the full stack.

- [ ] **Step 2: Make only the integration corrections proven by the failing test and rerun**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_end_to_end -v`

Expected: PASS with fixture HTTP and fake structured model only.

- [ ] **Step 3: Replace dependencies and add environment example**

`requirements.txt` must contain FastAPI/Uvicorn, requests, Beautiful Soup 4, Streamlit, `langchain-core`, `langchain-google-genai`, `langchain-groq`, and test-client support, and must not contain transformers, torch, accelerate, or bitsandbytes. `.env.example` documents `GOOGLE_API_KEY`, `GROQ_API_KEY`, provider/model selection, database path, and safe tunable limits with blank secrets.

- [ ] **Step 4: Rewrite current documentation and verify a demonstration source honestly**

Document endpoint examples, the consistent error envelope, settings, exact setup/run commands, provider selection, no-browser/static-only limitations, SSRF/redirect behavior, partial success, deterministic versus LLM output, history semantics, and Mermaid architecture. Attempt one end-to-end public static source only through the production safety/fetch/extraction path; list it only if at least two valid reviews are reproducibly extracted. Otherwise state that no stable public source was verified on 2026-07-10 and that deterministic fixtures are the supported demo.

- [ ] **Step 5: Run the complete suite and commit docs/integration stage**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: all tests PASS, zero failures/errors.

```powershell
git add -A
git commit -m "docs: document website review intelligence workflow"
```

### Task 8: Final verification and corrective commit only if evidence requires it

**Files:**
- Modify: only files implicated by a newly failing verification or stale-reference check.
- Test: matching regression test must be added and observed failing before any corrective production change.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified, internally consistent checkout with ordered commits and no push.

- [ ] **Step 1: Install the final dependency set if imports are missing**

Run: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

Expected: exit 0. If sandbox network access blocks installation, request approval and rerun the same command.

- [ ] **Step 2: Run fresh full verification**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Run: `.\.venv\Scripts\python.exe -m compileall backend dashboard scripts tests`

Run: `.\.venv\Scripts\python.exe -c "import fastapi, streamlit, requests, bs4, langchain_core, langchain_google_genai, langchain_groq; from backend.app.main import app; print('imports ok', app.title)"`

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api tests.test_end_to_end tests.test_dashboard -v`

Expected: every command exits 0; tests report zero failures/errors; import command prints `imports ok ReviewInsight API`.

- [ ] **Step 3: Perform safe frontend smoke checks**

Start the backend and Streamlit locally on unused loopback ports with hidden processes, verify FastAPI OpenAPI exposes only the active website analysis/history routes, request Streamlit health, and terminate both processes. Do not submit a real provider call or persist a demo analysis during smoke testing.

- [ ] **Step 4: Inspect final diff and obsolete-reference scan**

Run: `git diff 58460b6 --stat`

Run: `git diff --check 58460b6`

Run: `rg -n -i "hugging[ -]?face|transformers|torch|bitsandbytes|analysis/single|analysis/batch|paste (one|a) review|model warmup|rule.?based fallback" -g '!docs/superpowers/specs/**' -g '!docs/superpowers/plans/**' .`

Run: `git status --short --branch`

Expected: intentional redesign files only; no whitespace errors; no obsolete active-code, dependency, test, or current-documentation references; clean worktree on the current branch and no push.

- [ ] **Step 5: If verification exposes a bug, reproduce RED, correct it, rerun all checks, and commit**

```powershell
git add -A
git commit -m "fix: address final website analysis verification"
```

Create this commit only when verification required a real correction. Otherwise leave the documentation/integration commit as the last implementation commit.

- [ ] **Step 6: Record delivery evidence**

Run: `git log --reverse --format="%h %s" 58460b6..HEAD`

Report the change summary, architectural decisions, important files, environment variables, setup/run instructions, scraping limitations, exact verification commands/results, and every created commit in order. Do not push.
