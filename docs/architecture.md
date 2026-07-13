# ReviewInsight MVP Architecture

## System flow

```text
Browser
  -> Streamlit :8501
  -> POST FastAPI :8000/api/analyze
       -> collect_reviews(url)
            -> validate a public destination
            -> bounded static HTTP request
            -> JSON-LD extraction
            -> conservative HTML review-card fallback
            -> normalize, deduplicate, cap at 40
       -> analyze_reviews(reviews, provider)
            -> Gemini or Groq chat model
            -> one LangChain create_agent invocation
            -> validated AgentInsights
       -> calculate_metrics(reviews, review_sentiments)
       -> AnalysisResponse
```

FastAPI owns URL validation, collection, model interaction, deterministic calculations, response validation, and public error mapping. Streamlit owns form state, health checks, API calls, charts, and presentation. The applications share JSON contracts rather than Python service imports.

## File ownership

- `backend/app/models.py`: request, review, insight, metric, response, and public-error schemas.
- `backend/app/collector.py`: destination safety, bounded retrieval, extraction, normalization, deduplication, and limits.
- `backend/app/analyzer.py`: provider factory, evidence-based prompt, single agent invocation, and exact sentiment-ID validation.
- `backend/app/service.py`: synchronous orchestration and deterministic metrics.
- `backend/app/main.py`: FastAPI construction and public HTTP error mapping.
- `dashboard/api_client.py`: backend health and analysis HTTP boundaries.
- `dashboard/streamlit_app.py`: one-page dashboard and pure response-formatting helpers.
- `tests/`: fixture-based collection, fake-agent analysis, service, API, and dashboard tests.

## Endpoint contracts

### `GET /health`

Returns immediately without collection or model access:

```json
{"status":"ok"}
```

### `POST /api/analyze`

Request:

```json
{"url":"https://web-scraping.dev/product/1","provider":"google"}
```

The validated response contains source metadata, deterministic metrics, structured insights, and normalized reviews. Supported providers are `google` and `groq`.

Public error codes are `invalid_url`, `collection_failed`, `no_reviews`, `missing_api_key`, and `analysis_failed`. Provider payloads, credentials, stack traces, resolved network details, and raw internal exceptions do not cross the API boundary.

## Collection boundary

The collector accepts only public `http` and `https` destinations. It rejects embedded credentials and any resolved address that is not globally routable. Redirects are disabled at the HTTP client, followed manually up to three times, and every target is revalidated.

Responses use explicit connection/read timeouts, a descriptive user agent, HTML content-type enforcement, streaming reads, and a 1 MiB ceiling. JSON-LD review bodies are attempted first. HTML fallback requires a semantic review container and a review-body element; arbitrary paragraphs are never promoted to reviews. Exact case-insensitive duplicates are removed, IDs are assigned sequentially, and at most 40 reviews are returned.

## Analysis and metrics boundary

`analyze_reviews` constructs one Gemini or Groq model and one `langchain.agents.create_agent` with `tools=[]` and `response_format=AgentInsights`. It invokes the agent once with compact records containing only ID, text, rating, and date. Returned sentiment IDs must cover every submitted review exactly once.

Counts, rated counts, average rating, positive percentage, sentiment counts, and one-through-five rating distribution are always calculated in Python from collected reviews and validated review-level sentiments.

## Explicit non-goals

- JavaScript rendering, Playwright, Selenium, Chrome control, and anti-bot bypasses.
- Pagination, authenticated pages, marketplace API discovery, and universal source compatibility.
- Databases, report history, user accounts, authentication, queues, workers, and background processing.
- Application subprocess launchers or browser launch/control code.
- Custom model retries, batching, memory, checkpointers, heuristic fallbacks, or tracing services.
