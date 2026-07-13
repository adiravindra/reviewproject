# ReviewInsight Architecture

## Runtime topology and ownership

```text
run_app.py supervisor
  +-- load PROJECT_ROOT/.env without overriding parent environment
  +-- Uvicorn child: FastAPI 127.0.0.1:8000
  +-- Streamlit child: dashboard 127.0.0.1:8501
  +-- wait for Streamlit /_stcore/health
  +-- open dashboard once in the OS default browser

Browser
  -> Streamlit form
  -> GET FastAPI /health
  -> POST FastAPI /api/analyze
       1. validate_provider_credentials(provider)
       2. collect_reviews(url)
       3. analyze_reviews(reviews, provider)
       4. calculate_metrics(reviews, sentiments)
       5. validate and return AnalysisResponse
```

`run_app.py` owns local startup and process lifecycle. Before starting either child, it loads `PROJECT_ROOT/.env` without replacing values already present in the parent environment. Both children inherit the resulting environment. It builds argument-list commands around `sys.executable`, launches both children from the project root without a shell, polls them, and stays alive while both remain active. `Ctrl+C` triggers graceful termination and a bounded wait for both children. If a child exits or cannot start, the supervisor stops its peer and returns a nonzero status; a child that does not terminate within five seconds is killed and reaped.

The supervisor probes Streamlit's local health endpoint with a short timeout. On the first successful response it requests one operating-system default-browser open for `http://127.0.0.1:8501`. A browser failure prints the manual URL and does not stop supervision. The supervisor does not install dependencies, change credential values, or suppress child output. FastAPI owns validation, collection, model interaction, calculations, response validation, and public error mapping. Streamlit owns form state, backend health checks, API calls, charts, and presentation. The applications share JSON contracts rather than importing backend services into the dashboard.

## Analysis flow

Credential preflight is deliberately the first service stage. A failure stops the request before any destination resolution, page request, review extraction, model construction, or generative invocation.

```text
POST /api/analyze
  -> selected key exists and is nonblank?
  -> provider model-list GET succeeds?
  -> public destination validation
  -> bounded static HTML collection
  -> JSON-LD reviews, then recognized static review cards
  -> normalize, deduplicate, require two, cap at 40
  -> one structured LangChain agent invocation
  -> exact review-sentiment ID validation
  -> deterministic Python metrics
  -> validated JSON response
```

Model construction repeats the selected-key presence check as defense in depth for direct callers, but orchestration preflight is the authoritative gate.

## Credential boundary

| Provider | Variable | Request | Header |
|---|---|---|---|
| Gemini | `GOOGLE_API_KEY` | `GET https://generativelanguage.googleapis.com/v1beta/models` | `x-goog-api-key: <key>` |
| Groq | `GROQ_API_KEY` | `GET https://api.groq.com/openai/v1/models` | `Authorization: Bearer <key>` |

These model-list requests are non-generative. Only the selected provider's environment variable is read. Requests separate a three-second connection timeout from a five-second read timeout.

Validation decisions use only the HTTP status: `2xx` succeeds; `400`, `401`, and `403` map to `invalid_api_key`; other non-success statuses map to `provider_unavailable`. Missing selected credentials map to `missing_api_key` without an HTTP request. Request exceptions also map to `provider_unavailable`.

Provider bodies are not inspected or used in decisions. Key values, headers, bodies, endpoint diagnostics, transport exceptions, stack traces, and chained provider errors do not cross the FastAPI boundary.

## Collection boundary

The collector accepts only public `http` and `https` destinations. It rejects embedded credentials and any resolved address that is not globally routable. Redirects are disabled in the HTTP client, followed manually at most three times, and every target is revalidated before a request is sent.

Responses use explicit connection/read timeouts, a descriptive user agent, HTML content-type enforcement, streaming reads, and a 1 MiB ceiling. JSON-LD review bodies are attempted first. Static markup extraction requires both a semantic review container and a review-body element; arbitrary paragraphs are never promoted to reviews. Exact case-insensitive duplicates are removed, IDs are assigned sequentially, at least two reviews are required, and at most 40 reviews are returned.

## Analysis and metrics boundary

`analyze_reviews` constructs the selected Gemini or Groq chat model and one `langchain.agents.create_agent` with `tools=[]` and `response_format=AgentInsights`. The agent is invoked once with compact records containing only ID, text, rating, and date. Returned review-sentiment IDs must cover every submitted review exactly once.

Counts, rated counts, average rating, positive percentage, sentiment counts, and the one-through-five rating distribution are calculated in Python from collected reviews and validated review-level sentiments.

## Endpoint contracts

### `GET /health`

Returns without credential validation, collection, or model access:

```json
{"status":"ok"}
```

### `POST /api/analyze`

Request:

```json
{"url":"https://web-scraping.dev/product/1","provider":"google"}
```

The validated response contains source metadata, deterministic metrics, structured insights, and normalized reviews. Supported provider values are `google` and `groq`.

| Public code | Status |
|---|---:|
| `invalid_url`, `no_reviews` | 422 |
| `collection_failed` | 502 |
| `missing_api_key` | 400 |
| `invalid_api_key` | 401 |
| `provider_unavailable` | 503 |
| `analysis_failed` | 502 |

FastAPI request-schema failures also use `422`. Unknown exceptions are reduced to the generic `analysis_failed` message with status `500`.

## File ownership

- `run_app.py`: project environment loading, dashboard readiness and browser opening, peer process commands, supervision, shutdown escalation, and exit semantics.
- `backend/app/errors.py`: stable application-owned analysis error.
- `backend/app/credentials.py`: provider configuration and safe non-generative preflight.
- `backend/app/collector.py`: destination safety, bounded retrieval, extraction, normalization, deduplication, and limits.
- `backend/app/analyzer.py`: provider factory, evidence-based prompt, one agent invocation, and sentiment-ID validation.
- `backend/app/service.py`: ordered orchestration and deterministic metrics.
- `backend/app/models.py`: shared request, response, insight, metric, and public-error schemas.
- `backend/app/main.py`: FastAPI construction and HTTP error mapping.
- `dashboard/api_client.py`: backend health and analysis HTTP boundaries.
- `dashboard/streamlit_app.py`: dashboard state, safe error rendering, and report presentation.
- `tests/`: fixture-based and fake-backed boundary, behavior, lifecycle, and documentation checks.

## Explicit non-goals and limits

- JavaScript rendering, browser control, anti-bot bypasses, pagination, authenticated pages, and universal source compatibility.
- Persistent reports, user accounts, authentication, queues, workers, and background processing.
- Dependency installation, credential mutation, or output suppression by the supervisor.
- Custom model retries, batching, memory, checkpointers, heuristic model substitutes, or tracing services.
