# Simple Review Insights MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current overbuilt review-intelligence implementation with a small FastAPI + Streamlit MVP that statically collects reviews, analyzes them with one structured LangChain agent call, and renders a one-page insights dashboard.

**Architecture:** FastAPI exposes only `GET /health` and `POST /api/analyze`; the analysis endpoint synchronously calls a bounded one-page collector, one Gemini/Groq LangChain agent, and deterministic metric calculation. Streamlit is a separate thin HTTP client and dashboard. Both processes are started explicitly, with no browser automation, child-process launcher, database, history, or background infrastructure.

**Tech Stack:** Python 3.12+, FastAPI, Uvicorn, Requests, Beautiful Soup, Pydantic, LangChain 1.x, `langchain-google-genai`, `langchain-groq`, Streamlit, unittest, and FastAPI TestClient.

## Global Constraints

- Preserve the FastAPI + Streamlit separation.
- Expose only `GET /health` and `POST /api/analyze` for the MVP.
- Use static HTTP only: no Playwright, Selenium, Chrome, JavaScript rendering, or anti-bot bypasses.
- Analyze at most 40 unique reviews from one page and require at least two.
- Use one `langchain.agents.create_agent` invocation with an empty tool list and structured output.
- Support `google` and `groq`; credentials come only from `GOOGLE_API_KEY` and `GROQ_API_KEY`.
- Keep model names configurable with `REVIEWINSIGHT_GOOGLE_MODEL` and `REVIEWINSIGHT_GROQ_MODEL`.
- Calculate review counts, rating metrics, and sentiment distributions in Python, not in the model.
- Do not persist reports or add history, authentication, queues, workers, containers, or cloud resources.
- Do not use `scripts/run_app.py` or any other subprocess launcher.
- Automated tests must not call a live website or model provider.
- Preserve the untracked `tmp/` diagnostic directory.

## Target File Map

### Active implementation after completion

- `backend/app/models.py`: all public and internal Pydantic contracts.
- `backend/app/collector.py`: safe static retrieval and review extraction.
- `backend/app/analyzer.py`: provider selection and one structured agent invocation.
- `backend/app/service.py`: orchestration and deterministic metrics.
- `backend/app/main.py`: two FastAPI endpoints and public error mapping.
- `dashboard/api_client.py`: health and analysis requests.
- `dashboard/streamlit_app.py`: one-page dashboard plus formatting helpers.
- `tests/fixtures/review_page.html`: deterministic JSON-LD collection fixture.
- `tests/test_collector_mvp.py`: URL, extraction, normalization, and bound tests.
- `tests/test_analyzer_mvp.py`: provider and structured-agent contract tests.
- `tests/test_service_mvp.py`: metric and pipeline tests.
- `tests/test_api_mvp.py`: endpoint and error tests.
- `tests/test_dashboard_mvp.py`: client and formatting tests.
- `README.md`, `.env.example`, `requirements.txt`: minimal setup, configuration, limits, and runbook.

### Removed after replacements pass

- `backend/app/errors.py`
- `backend/app/settings.py`
- `backend/app/routers/`
- `backend/app/schemas/`
- `backend/app/scrapers/`
- `backend/app/services/`
- `dashboard/pages/`
- `dashboard/ui.py`
- `scripts/run_app.py`
- Old `tests/test_*.py`, `tests/factories.py`, and `tests/fakes.py` not listed in the active test map.
- `data/review_history.json` and the active database/history documentation.

---

### Task 1: Replace the contracts and static collector

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/collector.py`
- Create: `tests/fixtures/review_page.html`
- Create: `tests/test_collector_mvp.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `Review`, `SourceInfo`, `CollectionResult`, `AnalysisRequest`, `ReviewSentiment`, `Theme`, `AgentInsights`, `Metrics`, `AnalysisResponse`, and `PublicError` Pydantic models.
- Produces: `CollectionError(code: str, public_message: str)`.
- Produces: `collect_reviews(url: str, *, session: requests.Session | None = None, resolver: Resolver = socket.getaddrinfo) -> CollectionResult`.
- Consumes: no application interfaces.

- [ ] **Step 1: Replace dependency declarations with the MVP set**

Use this complete `requirements.txt`:

```text
fastapi>=0.116,<1
uvicorn>=0.30,<1
requests>=2.32,<3
beautifulsoup4>=4.13,<5
langchain>=1.1,<2
langchain-google-genai>=4.2,<5
langchain-groq>=1.1,<2
streamlit>=1.50,<2
httpx>=0.28,<1
```

This also fixes the current invalid `httpx2` requirement.

- [ ] **Step 2: Add the fixture and failing collector tests**

Create a fixture containing a Product JSON-LD object with five reviews. Cover the public interface with these exact behaviors:

```python
class CollectorTests(unittest.TestCase):
    def test_extracts_json_ld_reviews_and_source_metadata(self):
        session = FixtureSession("tests/fixtures/review_page.html")
        result = collect_reviews(
            "https://example.com/product",
            session=session,
            resolver=public_resolver,
        )
        self.assertEqual(result.source.title, "Everyday Headphones")
        self.assertEqual(result.source.extractor, "json_ld")
        self.assertEqual(len(result.reviews), 5)
        self.assertEqual(result.reviews[0].id, "r1")
        self.assertEqual(result.reviews[0].rating, 5)

    def test_static_cards_are_a_conservative_fallback(self):
        html = cards(["Clear sound and a comfortable fit.", "Useful controls and dependable battery life."])
        result = collect_reviews(
            "https://example.com/reviews",
            session=TextSession(html),
            resolver=public_resolver,
        )
        self.assertEqual(result.source.extractor, "html_cards")
        self.assertEqual(len(result.reviews), 2)

    def test_rejects_private_urls_before_requesting(self):
        session = TextSession("")
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "http://internal.example/reviews",
                session=session,
                resolver=private_resolver,
            )
        self.assertEqual(raised.exception.code, "invalid_url")
        self.assertEqual(session.calls, 0)

    def test_deduplicates_caps_and_requires_two_reviews(self):
        duplicated = cards(["Same useful review", "same useful review"])
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "https://example.com/reviews",
                session=TextSession(duplicated),
                resolver=public_resolver,
            )
        self.assertEqual(raised.exception.code, "no_reviews")
```

The test fakes implement only `get(url, **kwargs)`, `status_code`, `headers`, `url`, `is_redirect`, `is_permanent_redirect`, `iter_content()`, and `close()` so the tests describe the actual collector boundary.

- [ ] **Step 3: Run the collector tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp -v
```

Expected: FAIL because `backend.app.models` and `backend.app.collector` do not exist.

- [ ] **Step 4: Add the minimal contracts**

Implement the following exact model shapes in `backend/app/models.py`:

```python
Sentiment = Literal["positive", "neutral", "negative"]
OverallSentiment = Literal["positive", "neutral", "negative", "mixed"]
Provider = Literal["google", "groq"]

class Review(BaseModel):
    id: str
    text: str
    rating: int | None = Field(default=None, ge=1, le=5)
    date: str | None = None

class SourceInfo(BaseModel):
    url: HttpUrl
    title: str
    extractor: Literal["json_ld", "html_cards"]

class CollectionResult(BaseModel):
    source: SourceInfo
    reviews: list[Review]

class AnalysisRequest(BaseModel):
    url: HttpUrl
    provider: Provider = "google"

class ReviewSentiment(BaseModel):
    review_id: str
    sentiment: Sentiment

class Theme(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=240)
    mentions: int = Field(ge=1)

class AgentInsights(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    overall_sentiment: OverallSentiment
    themes: list[Theme] = Field(min_length=1, max_length=6)
    strengths: list[str] = Field(max_length=5)
    weaknesses: list[str] = Field(max_length=5)
    actions: list[str] = Field(max_length=5)
    review_sentiments: list[ReviewSentiment]

class Metrics(BaseModel):
    review_count: int
    rated_count: int
    average_rating: float | None
    positive_percentage: float
    sentiment_counts: dict[Sentiment, int]
    rating_distribution: dict[str, int]

class AnalysisResponse(BaseModel):
    source: SourceInfo
    metrics: Metrics
    insights: AgentInsights
    reviews: list[Review]

class PublicError(BaseModel):
    code: Literal["invalid_url", "collection_failed", "no_reviews", "missing_api_key", "analysis_failed"]
    message: str
```

- [ ] **Step 5: Implement one bounded collector module**

Keep all collection helpers private in `backend/app/collector.py`. The public flow must be exactly:

```python
def collect_reviews(url: str, *, session=None, resolver=socket.getaddrinfo) -> CollectionResult:
    client = session or requests.Session()
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_public_url(current_url, resolver)
        response = _fetch_once(client, current_url)
        if response.is_redirect or response.is_permanent_redirect:
            target = response.headers.get("Location")
            response.close()
            if not target:
                raise CollectionError("collection_failed", COLLECTION_MESSAGE)
            current_url = urljoin(current_url, target)
            continue
        html = _read_html(response)
        break
    else:
        raise CollectionError("collection_failed", COLLECTION_MESSAGE)

    title, candidates = _extract_json_ld(html)
    extractor = "json_ld"
    if not candidates:
        title, candidates = _extract_html_cards(html)
        extractor = "html_cards"
    reviews = _normalize(candidates, limit=40)
    if len(reviews) < 2:
        raise CollectionError("no_reviews", "At least two public reviews are required.")
    return CollectionResult(
        source=SourceInfo(url=current_url, title=title or urlparse(current_url).hostname or "Review page", extractor=extractor),
        reviews=reviews,
    )
```

Use `(4, 10)` request timeouts, `allow_redirects=False`, `stream=True`, a 1 MiB byte counter over `iter_content(65536)`, and accepted content types containing `text/html` or `application/xhtml+xml`. `_validate_public_url` parses the URL, rejects credentials, resolves all addresses, and requires every parsed address to have `is_global is True`. `_extract_json_ld` walks dicts/lists recursively and accepts objects with a non-empty `reviewBody`; `_extract_html_cards` requires both a review container and a body selector. `_normalize` collapses whitespace, ignores bodies shorter than 10 characters, performs case-insensitive exact deduplication, assigns sequential `r1...r40` IDs, and parses only ratings between 1 and 5.

Map every `requests.RequestException`, malformed response, unsupported content type, oversized response, and parsing exception to `CollectionError("collection_failed", COLLECTION_MESSAGE)` without including raw exception text.

- [ ] **Step 6: Run the collector tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp -v
```

Expected: all collector tests PASS.

- [ ] **Step 7: Commit the collector slice**

```powershell
git add requirements.txt backend/app/models.py backend/app/collector.py tests/fixtures/review_page.html tests/test_collector_mvp.py
git commit -m "feat: add simple static review collection"
```

---

### Task 2: Add one structured LangChain analysis agent

**Files:**
- Create: `backend/app/analyzer.py`
- Create: `tests/test_analyzer_mvp.py`

**Interfaces:**
- Consumes: `Review`, `AgentInsights`, and `Provider` from `backend.app.models`.
- Produces: `AnalysisError(code: str, public_message: str)`.
- Produces: `build_model(provider: Provider) -> BaseChatModel`.
- Produces: `analyze_reviews(reviews: list[Review], provider: Provider, *, agent_factory=create_agent, model_factory=build_model) -> AgentInsights`.

- [ ] **Step 1: Write failing tests for provider selection and the agent contract**

```python
class AnalyzerTests(unittest.TestCase):
    def test_missing_provider_key_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AnalysisError) as raised:
                build_model("google")
        self.assertEqual(raised.exception.code, "missing_api_key")

    def test_one_agent_invocation_returns_validated_insights(self):
        fake_agent = FakeAgent(valid_insights())
        factory = Mock(return_value=fake_agent)
        result = analyze_reviews(
            sample_reviews(),
            "google",
            agent_factory=factory,
            model_factory=lambda provider: object(),
        )
        factory.assert_called_once()
        self.assertEqual(factory.call_args.kwargs["tools"], [])
        self.assertIs(factory.call_args.kwargs["response_format"], AgentInsights)
        self.assertEqual(fake_agent.invocations, 1)
        self.assertEqual(result.overall_sentiment, "positive")

    def test_missing_or_unknown_review_sentiment_ids_fail(self):
        invalid = valid_insights(review_ids=["r1", "unknown"])
        with self.assertRaises(AnalysisError) as raised:
            analyze_reviews(
                sample_reviews(),
                "groq",
                agent_factory=lambda **kwargs: FakeAgent(invalid),
                model_factory=lambda provider: object(),
            )
        self.assertEqual(raised.exception.code, "analysis_failed")
```

`FakeAgent.invoke()` returns `{"structured_response": AgentInsights(...)}`. The fake records the submitted state so the test also asserts the prompt contains review IDs, text, rating, and date but not an `author` field.

- [ ] **Step 2: Run analyzer tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_analyzer_mvp -v
```

Expected: FAIL because `backend.app.analyzer` does not exist.

- [ ] **Step 3: Implement the provider factory**

Use lazy imports so missing optional provider setup produces a public analysis error rather than breaking module import:

```python
def build_model(provider: Provider):
    if provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise AnalysisError("missing_api_key", "Set GOOGLE_API_KEY before using Gemini.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=os.getenv("REVIEWINSIGHT_GOOGLE_MODEL", "gemini-2.5-flash-lite"),
            temperature=0,
            timeout=30,
            max_retries=0,
        )
    if not os.getenv("GROQ_API_KEY"):
        raise AnalysisError("missing_api_key", "Set GROQ_API_KEY before using Groq.")
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("REVIEWINSIGHT_GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        timeout=30,
        max_retries=0,
    )
```

- [ ] **Step 4: Implement one agent call and exact-ID validation**

```python
def analyze_reviews(reviews, provider, *, agent_factory=create_agent, model_factory=build_model):
    model = model_factory(provider)
    agent = agent_factory(
        model=model,
        tools=[],
        response_format=AgentInsights,
        system_prompt=SYSTEM_PROMPT,
    )
    payload = [
        {"id": review.id, "text": review.text, "rating": review.rating, "date": review.date}
        for review in reviews
    ]
    try:
        state = agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload)}]})
        insights = AgentInsights.model_validate(state["structured_response"])
    except AnalysisError:
        raise
    except Exception:
        raise AnalysisError("analysis_failed", "The AI analysis could not be completed.") from None
    expected = {review.id for review in reviews}
    returned = [item.review_id for item in insights.review_sentiments]
    if len(returned) != len(set(returned)) or set(returned) != expected:
        raise AnalysisError("analysis_failed", "The AI analysis returned an incomplete result.")
    return insights
```

`SYSTEM_PROMPT` must explicitly require evidence-based synthesis, exact review-ID coverage, no invented facts, 3-6 concise themes, at most five items per list, and sentiment values from the schema. Do not add tools, memory, checkpointers, retries, or LangSmith requirements.

- [ ] **Step 5: Run analyzer tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_analyzer_mvp -v
```

Expected: all analyzer tests PASS.

- [ ] **Step 6: Commit the analysis slice**

```powershell
git add backend/app/analyzer.py tests/test_analyzer_mvp.py
git commit -m "feat: add structured LangChain review agent"
```

---

### Task 3: Add deterministic metrics and synchronous orchestration

**Files:**
- Create: `backend/app/service.py`
- Create: `tests/test_service_mvp.py`

**Interfaces:**
- Consumes: `collect_reviews(url) -> CollectionResult`.
- Consumes: `analyze_reviews(reviews, provider) -> AgentInsights`.
- Produces: `calculate_metrics(reviews: list[Review], sentiments: list[ReviewSentiment]) -> Metrics`.
- Produces: `run_analysis(url: str, provider: Provider, *, collector=collect_reviews, analyzer=analyze_reviews) -> AnalysisResponse`.

- [ ] **Step 1: Write failing metric and pipeline tests**

```python
class ServiceTests(unittest.TestCase):
    def test_metrics_are_derived_from_reviews_and_sentiments(self):
        metrics = calculate_metrics(sample_reviews(), sample_sentiments())
        self.assertEqual(metrics.review_count, 3)
        self.assertEqual(metrics.rated_count, 2)
        self.assertEqual(metrics.average_rating, 4.0)
        self.assertEqual(metrics.positive_percentage, 66.7)
        self.assertEqual(metrics.sentiment_counts, {"positive": 2, "neutral": 0, "negative": 1})
        self.assertEqual(metrics.rating_distribution, {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1})

    def test_pipeline_calls_each_stage_once_and_returns_contract(self):
        collector = Mock(return_value=sample_collection())
        analyzer = Mock(return_value=sample_insights())
        result = run_analysis("https://example.com/product", "google", collector=collector, analyzer=analyzer)
        collector.assert_called_once_with("https://example.com/product")
        analyzer.assert_called_once_with(sample_collection().reviews, "google")
        self.assertEqual(result.source.title, "Everyday Headphones")
        self.assertEqual(result.metrics.review_count, 3)
        self.assertEqual(result.reviews, sample_collection().reviews)
```

- [ ] **Step 2: Run service tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_service_mvp -v
```

Expected: FAIL because `backend.app.service` does not exist.

- [ ] **Step 3: Implement metrics and orchestration**

```python
def calculate_metrics(reviews, sentiments):
    ratings = [review.rating for review in reviews if review.rating is not None]
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for item in sentiments:
        counts[item.sentiment] += 1
    distribution = {str(star): 0 for star in range(1, 6)}
    for rating in ratings:
        distribution[str(rating)] += 1
    return Metrics(
        review_count=len(reviews),
        rated_count=len(ratings),
        average_rating=round(sum(ratings) / len(ratings), 1) if ratings else None,
        positive_percentage=round(100 * counts["positive"] / len(reviews), 1),
        sentiment_counts=counts,
        rating_distribution=distribution,
    )

def run_analysis(url, provider, *, collector=collect_reviews, analyzer=analyze_reviews):
    collection = collector(url)
    insights = analyzer(collection.reviews, provider)
    metrics = calculate_metrics(collection.reviews, insights.review_sentiments)
    return AnalysisResponse(
        source=collection.source,
        metrics=metrics,
        insights=insights,
        reviews=collection.reviews,
    )
```

- [ ] **Step 4: Run Tasks 1-3 tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp tests.test_analyzer_mvp tests.test_service_mvp -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the service slice**

```powershell
git add backend/app/service.py tests/test_service_mvp.py
git commit -m "feat: assemble review insight reports"
```

---

### Task 4: Replace FastAPI with the two-endpoint MVP surface

**Files:**
- Modify: `backend/app/main.py`
- Create: `tests/test_api_mvp.py`

**Interfaces:**
- Consumes: `AnalysisRequest`, `AnalysisResponse`, and `PublicError`.
- Consumes: `run_analysis(url, provider) -> AnalysisResponse`.
- Produces: `create_app(analysis_service=run_analysis) -> FastAPI`.
- Produces: `GET /health` and `POST /api/analyze`.

- [ ] **Step 1: Write failing endpoint tests**

```python
class ApiTests(unittest.TestCase):
    def test_only_health_and_analyze_are_active(self):
        client = TestClient(create_app(analysis_service=lambda url, provider: sample_response()))
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        paths = set(client.get("/openapi.json").json()["paths"])
        self.assertEqual(paths, {"/health", "/api/analyze"})

    def test_analyze_returns_the_validated_response(self):
        service = Mock(return_value=sample_response())
        client = TestClient(create_app(analysis_service=service))
        response = client.post("/api/analyze", json={"url": "https://example.com/product", "provider": "groq"})
        self.assertEqual(response.status_code, 200)
        service.assert_called_once_with("https://example.com/product", "groq")
        self.assertEqual(response.json()["metrics"]["review_count"], 3)

    def test_known_failures_have_small_safe_envelopes(self):
        def fail(url, provider):
            raise CollectionError("no_reviews", "At least two public reviews are required.")
        response = TestClient(create_app(analysis_service=fail)).post(
            "/api/analyze",
            json={"url": "https://example.com/product", "provider": "google"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": {"code": "no_reviews", "message": "At least two public reviews are required."}})
```

Also test malformed URLs return status 422 without calling the service and unexpected exceptions return a generic `analysis_failed` 500 envelope without raw exception text.

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp -v
```

Expected: FAIL because the current app exposes legacy routes and lacks the injected service signature.

- [ ] **Step 3: Replace `backend/app/main.py`**

Use a closure for the one dependency rather than retaining router/dependency modules:

```python
def create_app(analysis_service=run_analysis):
    app = FastAPI(title="ReviewInsight MVP")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(request: AnalysisRequest):
        try:
            return analysis_service(str(request.url), request.provider)
        except CollectionError as exc:
            status = 422 if exc.code in {"invalid_url", "no_reviews"} else 502
            raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.public_message}) from None
        except AnalysisError as exc:
            status = 400 if exc.code == "missing_api_key" else 502
            raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.public_message}) from None
        except Exception:
            raise HTTPException(status_code=500, detail={"code": "analysis_failed", "message": "The analysis could not be completed."}) from None

    return app

app = create_app()
```

- [ ] **Step 4: Run API and upstream tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp tests.test_analyzer_mvp tests.test_service_mvp tests.test_api_mvp -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the API slice**

```powershell
git add backend/app/main.py tests/test_api_mvp.py
git commit -m "feat: expose lightweight review analysis API"
```

---

### Task 5: Replace Streamlit with the one-page dashboard

**Files:**
- Modify: `dashboard/api_client.py`
- Modify: `dashboard/streamlit_app.py`
- Create: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Consumes: FastAPI JSON contracts only.
- Produces: `BackendUnavailable`, `ApiClientError`.
- Produces: `check_health(base_url: str, *, session=requests) -> bool`.
- Produces: `request_analysis(url: str, provider: str, base_url: str, *, session=requests) -> dict`.
- Produces: pure formatting helpers `metric_values(report: dict) -> tuple[str, str, str, str]`, `sentiment_rows(report: dict) -> list[dict]`, and `rating_rows(report: dict) -> list[dict]`.

- [ ] **Step 1: Write failing API-client and formatting tests**

```python
class DashboardClientTests(unittest.TestCase):
    def test_health_uses_a_short_timeout(self):
        session = FakeSession(get_response={"status": "ok"})
        self.assertTrue(check_health("http://127.0.0.1:8000", session=session))
        self.assertEqual(session.get_call, ("http://127.0.0.1:8000/health", 2))

    def test_connection_failure_is_backend_unavailable(self):
        session = FailingSession(requests.ConnectionError("OS detail"))
        with self.assertRaises(BackendUnavailable) as raised:
            request_analysis("https://example.com", "google", "http://127.0.0.1:8000", session=session)
        self.assertNotIn("OS detail", str(raised.exception))

    def test_structured_api_error_is_preserved(self):
        session = FakeSession(post_status=422, post_json={"detail": {"code": "no_reviews", "message": "At least two public reviews are required."}})
        with self.assertRaises(ApiClientError) as raised:
            request_analysis("https://example.com", "google", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "no_reviews")

class DashboardFormattingTests(unittest.TestCase):
    def test_metrics_and_charts_use_response_values(self):
        report = sample_report()
        self.assertEqual(metric_values(report), ("3", "4.0 / 5", "66.7%", "Positive"))
        self.assertEqual(sentiment_rows(report)[0], {"Sentiment": "Positive", "Reviews": 2})
        self.assertEqual(rating_rows(report)[4], {"Rating": "5 star", "Reviews": 1})
```

- [ ] **Step 2: Run dashboard tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: FAIL because the current client and page implement legacy API/history behavior.

- [ ] **Step 3: Replace the API client**

Implement exact timeouts and safe exception boundaries:

```python
def check_health(base_url, *, session=requests):
    try:
        response = session.get(f"{base_url.rstrip('/')}/health", timeout=2)
        return response.status_code == 200 and response.json() == {"status": "ok"}
    except (requests.RequestException, ValueError):
        return False

def request_analysis(url, provider, base_url, *, session=requests):
    endpoint = f"{base_url.rstrip('/')}/api/analyze"
    try:
        response = session.post(endpoint, json={"url": url, "provider": provider}, timeout=45)
    except (requests.ConnectionError, requests.Timeout):
        raise BackendUnavailable("The FastAPI backend is not reachable.") from None
    except requests.RequestException:
        raise ApiClientError("analysis_failed", "The request could not be completed.") from None
    if response.status_code >= 400:
        detail = response.json().get("detail", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
        raise ApiClientError(detail.get("code", "analysis_failed"), detail.get("message", "The request could not be completed."))
    return response.json()
```

- [ ] **Step 4: Replace the Streamlit page**

Build the page directly in `dashboard/streamlit_app.py` with this section order and exact visible labels:

```text
ReviewInsight
Turn public customer reviews into a clear product readout.

Review page URL
AI provider: Gemini | Groq
Analyze reviews

Reviews analyzed | Average rating | Positive share | Overall sentiment
What customers are saying
Sentiment mix | Rating distribution
Recurring themes
Strengths | Weaknesses
Recommended actions
Review sample
```

Use `st.form`, four `st.metric` columns, two `st.bar_chart` columns, a compact theme dataframe with `hide_index=True`, two insight columns, an ordered action list, and one expander for reviews. Store only the latest report in `st.session_state`. Before submission, call `check_health`; when false, show:

```text
The FastAPI backend is not reachable. Start it with:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Use `REVIEWINSIGHT_API_URL` with default `http://127.0.0.1:8000`; do not expose a backend URL input in the normal dashboard. Add a small CSS block with a white background, slate text, blue primary actions, subtle separators, 8px control radii, and no decorative gradients or nested card grid.

- [ ] **Step 5: Run dashboard tests and import smoke check**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
.\.venv\Scripts\python.exe -m compileall dashboard
```

Expected: all tests PASS and compileall exits 0.

- [ ] **Step 6: Commit the dashboard slice**

```powershell
git add dashboard/api_client.py dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: add simple review insights dashboard"
```

---

### Task 6: Remove inactive architecture, document startup, and verify end to end

**Files:**
- Delete: the inactive paths listed in the Target File Map.
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Test: all active tests.

**Interfaces:**
- Consumes: the completed MVP.
- Produces: one coherent active implementation, setup/run instructions, and verification evidence.

- [ ] **Step 1: Run all replacement tests before deletion**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collector_mvp tests.test_analyzer_mvp tests.test_service_mvp tests.test_api_mvp tests.test_dashboard_mvp -v
```

Expected: all replacement tests PASS.

- [ ] **Step 2: Remove legacy implementation and tests**

Delete only the paths listed in “Removed after replacements pass.” Keep `backend/app/__init__.py` if present, all five MVP test modules, `tests/__init__.py`, `tests/fixtures/review_page.html`, the new design/plan documents, and untracked `tmp/` diagnostics. Verify with:

```powershell
rg --files backend dashboard tests scripts data
```

Expected: only active MVP files, package markers, the fixture, and no subprocess launcher/history implementation remain.

- [ ] **Step 3: Rewrite configuration and README**

`.env.example` contains only:

```text
GOOGLE_API_KEY=
GROQ_API_KEY=
REVIEWINSIGHT_GOOGLE_MODEL=gemini-2.5-flash-lite
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
```

README sections are: purpose, architecture, supported sources/limitations, installation, provider configuration, two-terminal startup, sample URL, API example, tests, and connection-error resolution. The run commands are exactly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Document that free-tier eligibility and quotas belong to Google/Groq accounts. Document that static JSON-LD/HTML support is intentionally narrow and name `https://web-scraping.dev/product/1` as the demonstration page.

- [ ] **Step 4: Rewrite architecture and status docs**

`docs/architecture.md` contains the single flow from the design spec, file ownership, endpoint contracts, and explicit non-goals. `docs/project_status.md` states what is implemented and records exact verification results after the final run. Remove database/history/multi-batch diagrams and claims.

- [ ] **Step 5: Run complete automated verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall backend dashboard tests
```

Expected: all active tests PASS; compileall exits 0.

- [ ] **Step 6: Start FastAPI without a launcher and verify health**

Start FastAPI in a hidden Codex-managed process using the system PowerShell executable, wait until the port is listening, then run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected: `status` is `ok`. Do not use the WindowsApps PowerShell shim and do not start a browser from application code.

- [ ] **Step 7: Start Streamlit and verify the visible workflow**

Start Streamlit headlessly, then use Codex’s in-app browser to open `http://127.0.0.1:8501`. Verify:

- Desktop first viewport shows the title, URL field, provider selector, and primary button without clipping.
- Submitting with the backend stopped shows the explicit backend command rather than a raw connection exception.
- The seeded/fake end-to-end response renders all four metrics, both charts, summary, themes, strengths, weaknesses, actions, and review expander.
- A mobile-sized viewport has no horizontal overflow and keeps the submission flow usable.
- Browser console contains no application errors.

Capture the final desktop screenshot and inspect it with `view_image` before handoff.

- [ ] **Step 8: Perform optional live checks when external access and credentials are available**

Collection-only check:

```powershell
.\.venv\Scripts\python.exe -c "from backend.app.collector import collect_reviews; r=collect_reviews('https://web-scraping.dev/product/1'); print(r.source.title, len(r.reviews), r.source.extractor)"
```

Expected when the external page remains compatible: title `Box of Chocolate Candy`, at least two reviews, extractor `json_ld`. If network access is unavailable or markup changed, record the exact safe failure and rely on fixtures.

Run one real `/api/analyze` request only if `GOOGLE_API_KEY` or `GROQ_API_KEY` is already present. Never print key values. If neither is configured, record the credential check as skipped rather than weakening the automated tests.

- [ ] **Step 9: Commit cleanup and documentation**

```powershell
git add README.md .env.example docs/architecture.md docs/project_status.md backend dashboard tests requirements.txt
git commit -m "refactor: simplify review insights MVP"
```

- [ ] **Step 10: Final scope audit**

Run:

```powershell
git status --short
rg -n -i "playwright|selenium|subprocess|sqlite|history|background worker" backend dashboard scripts README.md requirements.txt
```

Expected: only the preserved untracked `tmp/` diagnostics remain in status; the scope scan finds no active browser automation, subprocess launcher, persistence, history, or worker implementation. References in README are allowed only where describing deliberate exclusions and the resolved prior failure.

## Plan Self-Review Results

- **Spec coverage:** Every success criterion and non-goal maps to Tasks 1-6.
- **Placeholder scan:** Every implementation action names the exact behavior, command, and expected result; no deferred decisions remain.
- **Type consistency:** `Review`, `CollectionResult`, `AgentInsights`, `Metrics`, and `AnalysisResponse` flow unchanged from collector through service, API, client, and dashboard.
- **Risk boundary:** Live sites and model providers are optional verification only; deterministic tests use fixtures and fakes.
- **Simplification check:** The final active architecture has five backend modules, two dashboard modules, five focused test modules, and two endpoints.
