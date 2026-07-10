# ReviewInsight Project Status

Status: website review intelligence proof of concept implemented on July 10, 2026.

## Active product surface

- `POST /analysis/website`: synchronous public URL analysis.
- `GET /analysis/history`: website-level saved-run summaries.
- `GET /analysis/history/{run_id}`: exact stored report retrieval.
- Streamlit Analysis page: public URL input and complete website dashboard.
- Streamlit History page: saved website summaries and stored report loading.

No other analysis workflow is active.

## Implemented boundaries

- SSRF-aware public URL/DNS checks and redirect revalidation.
- Bounded streamed static HTML fetching with page, byte, redirect, timeout, review, and deadline limits.
- Ordered scraper registry with JSON-LD first and conservative static HTML second.
- Cleaning, 1–5 rating normalization, stable internal IDs, case-insensitive exact deduplication, and post-cleaning review caps.
- LangChain-only structured batch/synthesis analysis with Google Gemini default and Groq configuration.
- Exact sentiment-ID coverage, supporting-ID validation, one budget-aware invalid-output retry, and representative-ID text resolution.
- Code-derived ratings, distributions, review counts, sentiment counts, and overall sentiment.
- Save-after-validation SQLite persistence and website-level history.
- Structured loading, success, warning, failure, and stored-history UI states.

## Verified scope

- Deterministic automated fixtures cover direct, list, nested JSON-LD, semantic review cards, pagination, failures, partial success, LLM contracts, API contracts, persistence, frontend helpers, and end-to-end assembly.
- The static collection path reproduced five reviews from `https://web-scraping.dev/product/1` on July 10, 2026.
- No broad compatibility is claimed. JavaScript-only and protected sources remain outside the proof-of-concept scope.

See [the README](../README.md) for setup and [the architecture guide](architecture.md) for system diagrams.
