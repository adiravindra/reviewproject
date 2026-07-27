# Simple README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dense project README with a clear cross-platform onboarding guide while keeping detailed operational requirements in the existing architecture and status documents.

**Architecture:** `README.md` becomes the newcomer entry point and documents the product, credentials, installation, launch paths, project map, and future direction. Detailed provider pricing, Actor request configuration, legal caveats, and retention behavior remain in `docs/architecture.md` and `docs/project_status.md`; documentation tests will enforce this separation.

**Tech Stack:** Markdown, Python 3, FastAPI/Uvicorn, Streamlit, Groq, Apify, SQLite, `unittest`

## Global Constraints

- The README must support Windows/PowerShell and macOS/Linux with separate command blocks.
- Use `python` on Windows and `python3` on macOS/Linux.
- Use `.venv\Scripts\python.exe` on Windows and `.venv/bin/python` on macOS/Linux.
- Keep `run_app.py` as the recommended complete-application launcher.
- Keep `GROQ_API_KEY`, `APIFY_API_TOKEN`, and optional `REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile` accurate.
- State that inherited shell or system variables take precedence over repository-root `.env` values.
- Preserve the existing user changes in `backend/app/imports/apify_amazon.py`, `tests/fixtures/apify_automation_lab_amazon_reviews.json`, and `tests/test_import_adapters.py`.

---

## File Structure

- Modify `README.md`: concise project introduction and cross-platform onboarding.
- Modify `docs/project_status.md`: retain detailed Apify pricing, Actor, legal,
  and retention guidance removed from the README.
- Modify `tests/test_documentation.py`: enforce essential README setup, launch, configuration, and behavior.
- Modify `tests/test_import_documentation.py`: enforce concise README prerequisites while checking detailed provider operations in `docs/architecture.md`, `docs/project_status.md`, or both.
- Reference without modifying `.env.example`: source of active environment variables.
- Reference without modifying `run_app.py`: source of combined and individual process commands.

### Task 1: Define and Implement the Simplified README Contract

**Files:**

- Modify: `tests/test_documentation.py`
- Modify: `tests/test_import_documentation.py`
- Modify: `docs/project_status.md`
- Modify: `README.md`
- Test: `tests/test_documentation.py`
- Test: `tests/test_import_documentation.py`

**Interfaces:**

- Consumes: `.env.example`, `run_app.py`, `docs/architecture.md`, and `docs/project_status.md`.
- Produces: a README containing accurate onboarding commands and documentation tests that keep detailed provider requirements in the detailed documentation.

- [ ] **Step 1: Update the README documentation test with the new cross-platform contract**

In `tests/test_documentation.py`, replace
`test_readme_documents_staged_mvp_commands_and_demo_behavior` with a test that
requires the following exact values:

```python
def test_readme_documents_cross_platform_setup_and_runtime_behavior(self) -> None:
    """Keep the concise public setup guide aligned with the supported MVP."""

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    for expected in (
        "Windows / PowerShell",
        "macOS / Linux",
        r".\.venv\Scripts\python.exe -m pip install -r requirements.txt",
        r".\.venv\Scripts\python.exe run_app.py",
        ".venv/bin/python -m pip install -r requirements.txt",
        ".venv/bin/python run_app.py",
        "python -m uvicorn backend.app.main:app",
        "python -m streamlit run dashboard/streamlit_app.py",
        "GROQ_API_KEY",
        "APIFY_API_TOKEN",
        "REVIEWINSIGHT_GROQ_MODEL",
        "llama-3.3-70b-versatile",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8000/docs",
        "data/review_history.db",
        "bundled demo data",
    ):
        with self.subTest(expected=expected):
            self.assertIn(expected, readme)
```

Retain
`test_readme_documents_dotenv_precedence_and_automatic_browser_open` so the
shorter copy still documents environment precedence and browser behavior.

- [ ] **Step 2: Retain the detailed provider guidance outside the README**

Add a `## Provider operations and responsible use` section to
`docs/project_status.md`. Move the detailed content from the current README's
**External setup for live imports**, **Import cache and usage controls**, and
**Unofficial providers, terms, privacy, and retention** sections into it.
Preserve these exact operational facts:

- Amazon uses `automation-lab/amazon-reviews-scraper` with
  `sort: "helpful"` and no star-rating filter.
- Google Maps uses `compass/google-maps-reviews-scraper` with
  `reviewsSort: "mostRelevant"` and no rating filter.
- The selectable limits are 10, 20, 50, or 100; Groq analyzes the first 40.
- Cache entries last 30 days and **Refresh from source** is the only intentional
  provider refresh.
- The observed Automation Lab estimates are `$0.01` per run plus
  `$2.00 per 1,000` reviews, with approximate maxima of `$0.03`, `$0.05`,
  `$0.11`, and `$0.21` for the four supported limits.
- Pricing and availability can change.
- The Actors are unofficial scraping services, require no Amazon/Google
  cookies or session tokens, and can have provider-side retention.
- Historic `Apify (Axesso)` and `Outscraper` report provenance remains
  readable although neither is an active setup provider.
- Operators remain responsible for source rights and should review the linked
  Amazon Conditions of Use and Google Maps Additional Terms.

- [ ] **Step 3: Move detailed provider assertions to the detailed documentation**

In `tests/test_import_documentation.py`, make the README test require only
newcomer-facing setup and usage language:

```python
def test_readme_documents_provider_prerequisites_and_usage_controls(self):
    """Keep essential provider setup visible in the concise README."""

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "Apify account",
        "Apify API token",
        "APIFY_API_TOKEN",
        "10, 20, 50, or 100",
        "first 40",
        "30 days",
        "Refresh from source",
        "quota",
    ):
        with self.subTest(required=required):
            self.assertIn(required, readme)
    self.assertNotIn("OUTSCRAPER_API_KEY", readme)
    self.assertNotIn("Outscraper account", readme)
```

Extend `test_architecture_and_status_preserve_staged_boundaries` so its
`required` tuple also owns the detailed operational facts removed from the
README:

```python
"$0.01",
"$2.00 per 1,000",
"$0.03",
"$0.05",
"$0.11",
"$0.21",
"no star-rating filter",
"40 of",
"Refresh from source",
"unofficial scraping services",
"cookies or session tokens",
"pricing and availability can change",
"Amazon Conditions of Use",
"Google Maps Additional Terms",
```

- [ ] **Step 4: Run the focused tests and confirm the new contract initially fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation tests.test_import_documentation -v
```

Expected: the new README contract test fails because the current README does
not yet contain the Unix installation and launch commands. The detailed
architecture/status assertions should pass.

- [ ] **Step 5: Replace `README.md` with the approved concise structure**

Write the README in this exact section order:

```markdown
# Review Intelligence
## How it works
## Tech stack
## 1. Create the required accounts
### Groq
### Apify
## 2. Set up the project
### Windows / PowerShell
### macOS / Linux
## 3. Configure the environment
## 4. Run the application
### Recommended: run everything together
### Run the services individually
## Project structure
## Future work
## Tests
## More documentation
```

The copy must:

- Describe Review Intelligence as a local app that imports public Amazon or
  Google Maps reviews, lets the user inspect evidence, analyzes up to the first
  40 reviews through Groq, and saves successful reports in local SQLite.
- Link to official Groq and Apify account/key pages.
- Explain that Apify is needed for live imports and Groq is needed when
  analysis starts.
- Mention that imports offer 10, 20, 50, or 100 reviews, are cached for 30
  days, and only **Refresh from source** intentionally spends provider quota
  again.
- Explain that bundled demo data avoids an Apify import but Groq analysis still
  needs a valid Groq key.
- Show `python -m venv .venv` and Windows virtual-environment commands.
- Show `python3 -m venv .venv` and Unix virtual-environment commands.
- Show copying `.env.example` to `.env` using `Copy-Item` on Windows and `cp`
  on Unix.
- Show the three active settings in a dotenv block, keeping the model override
  optional.
- Explain that shell/system environment values take precedence over `.env`.
- Show the recommended `run_app.py` command for each platform and state that it
  automatically opens the dashboard after both services are healthy.
- Show individual Uvicorn and Streamlit commands for both platforms, with the
  backend started first in one terminal and the dashboard second in another.
- Link the dashboard at `http://127.0.0.1:8501` and FastAPI docs at
  `http://127.0.0.1:8000/docs`.
- Map `backend/app/`, `dashboard/`, `demo_data/`, `tests/`, `docs/`, and
  `run_app.py`.
- Present future work as possible directions: Docker/cloud deployment,
  authentication and multi-user support, additional review sources,
  background imports with progress, stronger history/export/retention tools,
  and provider quota/observability improvements.
- Preserve the Windows unittest command required by the existing tests and add
  the corresponding Unix command.
- Link to `docs/architecture.md`, `docs/project_status.md`, and
  `docs/demo_sources.md`.

- [ ] **Step 6: Run focused documentation tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation tests.test_import_documentation tests.test_live_source_documentation -v
```

Expected: all focused documentation tests pass.

- [ ] **Step 7: Run source compilation and inspect the final diff**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
git diff --check
git diff -- README.md docs/project_status.md tests/test_documentation.py tests/test_import_documentation.py
git status --short
```

Expected: compilation and `git diff --check` exit successfully. The relevant
diff contains only the README, project-status document, and two
documentation-contract tests; the pre-existing user changes remain unstaged
and unchanged.

- [ ] **Step 8: Commit the README implementation**

```powershell
git add -- README.md docs/project_status.md tests/test_documentation.py tests/test_import_documentation.py
git commit -m "docs: simplify project onboarding"
```
