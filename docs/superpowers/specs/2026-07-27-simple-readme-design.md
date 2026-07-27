# Simple README Design

**Date:** July 27, 2026  
**Status:** Approved

## Goal

Replace the current reference-heavy README with a concise onboarding guide that
helps a new developer understand Review Intelligence, configure its external
services, install it, and run it without reading the implementation first.

## Audience

The primary audience is a developer evaluating or running the project locally
on Windows, macOS, or Linux. The README should assume basic command-line and
Python familiarity but no prior knowledge of Groq, Apify, FastAPI, or Streamlit.

## README Structure

The README will use this order:

1. A plain-language project explanation and short workflow.
2. A compact technology stack.
3. Account creation and API-key instructions for Groq and Apify.
4. Project setup with separate Windows/PowerShell and macOS/Linux commands.
5. Configuration through a repository-root `.env` file.
6. Commands for running the complete application.
7. Commands for running FastAPI and Streamlit individually.
8. A short project-structure reference.
9. A realistic future-work list.
10. A compact automated-test section and links to detailed documentation.

## Content Requirements

- Explain that Apify imports public Amazon and Google Maps reviews and that Groq
  analyzes the collected evidence.
- Explain the evidence-first flow: import reviews, inspect them, analyze them,
  and revisit saved local reports.
- Identify `APIFY_API_TOKEN` and `GROQ_API_KEY` without exposing or encouraging
  credentials in source code or the interface.
- Keep `REVIEWINSIGHT_GROQ_MODEL` optional and retain its current default.
- Link to the official account/key pages for Groq and Apify.
- State that live imports may use Apify quota and that bundled demo data can be
  loaded without an Apify request.
- Use `python` in Windows commands and `python3` in Unix commands, with their
  platform-specific virtual-environment paths.
- Document `run_app.py` as the recommended launcher.
- Document the exact individual FastAPI and Streamlit commands and explain that
  the backend must be running for the dashboard.
- Include the local URLs for the dashboard and API documentation.
- Keep detailed architecture, API boundaries, provider caveats, and status
  records in the existing `docs/` files rather than duplicating them.

## Project Structure

The structure section will describe only the directories and files a new
contributor needs first:

- `backend/app/` for the FastAPI API, collection, imports, analysis, and storage.
- `dashboard/` for the Streamlit interface and API client.
- `demo_data/` for bundled example reviews.
- `tests/` for fixture-backed automated coverage.
- `docs/` for detailed architecture and project status.
- `run_app.py` for supervised local startup.

## Future Work

The future-work section will describe potential directions rather than
commitments:

- Docker and cloud deployment.
- Authentication and multi-user support.
- Additional review sources.
- Background imports and job progress.
- History search, export, deletion, and retention controls.
- Provider observability, quota visibility, and automated live smoke checks.

## Verification

Before completion:

1. Check every environment variable against `.env.example` and source usage.
2. Check every command against `run_app.py` and the installed module paths.
3. Run the README-focused documentation tests.
4. Review the README diff for clarity, broken local links, obsolete provider
   language, and accidental changes outside `README.md`.
