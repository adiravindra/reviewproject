import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.errors import AppError
from backend.app.services.history import save_website_analysis
from backend.app.services.orchestration import AnalysisDependencies
from backend.app.settings import Settings
from tests.test_orchestration import SequenceClock, analysis_result, scrape_result


def dependencies_for(
    path: Path,
    *,
    scrape=None,
    analyze=None,
    clock=None,
) -> AnalysisDependencies:
    return AnalysisDependencies(
        settings=Settings(db_path=path),
        scrape=scrape or (lambda url, deadline: scrape_result()),
        analyze=analyze or (lambda review_items: analysis_result()),
        save=lambda response: save_website_analysis(response, path),
        clock=clock or (lambda: 0.0),
        id_factory=lambda: "run_api",
        now=lambda: datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc),
    )


class WebsiteApiTests(unittest.TestCase):
    def test_post_returns_complete_contract_and_history_reloads_without_analysis(self) -> None:
        from backend.app.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            calls = {"scrape": 0, "analyze": 0}

            def scrape(url: str, deadline: float):
                calls["scrape"] += 1
                return scrape_result()

            def analyze(review_items):
                calls["analyze"] += 1
                return analysis_result()

            client = TestClient(
                create_app(dependencies_for(path, scrape=scrape, analyze=analyze))
            )
            response = client.post(
                "/analysis/website",
                json={"url": "https://public.example/reviews"},
            )
            history = client.get("/analysis/history")
            stored = client.get("/analysis/history/run_api")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["collection"]["found"], 3)
        self.assertEqual(payload["collection"]["analyzed"], 2)
        self.assertEqual(payload["metrics"]["average_rating"], 3.5)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["items"][0]["id"], "run_api")
        self.assertEqual(stored.json(), payload)
        self.assertEqual(calls, {"scrape": 1, "analyze": 1})

    def test_supported_analysis_failures_use_consistent_envelopes_and_do_not_save(self) -> None:
        from backend.app.main import create_app

        failure_cases = {
            "unsupported_source": (422, "scraping"),
            "blocked_source": (403, "scraping"),
            "no_reviews_found": (422, "scraping"),
            "insufficient_reviews": (422, "scraping"),
            "scrape_failed": (502, "scraping"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for code, (status_code, stage) in failure_cases.items():
                path = Path(directory) / f"{code}.db"

                def fail_scrape(url: str, deadline: float, error_code: str = code, http_status: int = status_code):
                    raise AppError(error_code, "Safe scraping failure.", stage, http_status)

                client = TestClient(create_app(dependencies_for(path, scrape=fail_scrape)))
                with self.subTest(code=code):
                    response = client.post(
                        "/analysis/website",
                        json={"url": "https://public.example/reviews"},
                    )
                    self._assert_error(response, code, status_code, stage)
                    self.assertEqual(client.get("/analysis/history").json(), {"items": []})

            llm_path = Path(directory) / "llm.db"

            def fail_analysis(review_items):
                raise AppError("llm_failed", "Safe provider failure.", "analysis", 502)

            llm_client = TestClient(create_app(dependencies_for(llm_path, analyze=fail_analysis)))
            llm_response = llm_client.post(
                "/analysis/website",
                json={"url": "https://public.example/reviews"},
            )
            self._assert_error(llm_response, "llm_failed", 502, "analysis")
            self.assertEqual(llm_client.get("/analysis/history").json(), {"items": []})

            timeout_path = Path(directory) / "timeout.db"
            timeout_client = TestClient(
                create_app(
                    dependencies_for(timeout_path, clock=SequenceClock([0.0, 121.0]))
                )
            )
            timeout_response = timeout_client.post(
                "/analysis/website",
                json={"url": "https://public.example/reviews"},
            )
            self._assert_error(timeout_response, "request_timeout", 504, "request")
            self.assertEqual(timeout_client.get("/analysis/history").json(), {"items": []})

    def test_invalid_requests_and_missing_history_use_error_envelope(self) -> None:
        from backend.app.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(dependencies_for(Path(directory) / "history.db")))

            invalid = client.post("/analysis/website", json={"url": "file:///etc/passwd"})
            missing_url = client.post("/analysis/website", json={})
            missing_history = client.get("/analysis/history/not-present")

        self._assert_error(invalid, "invalid_url", 422, "validation")
        self._assert_error(missing_url, "invalid_url", 422, "validation")
        self._assert_error(missing_history, "analysis_not_found", 404, "history")

    def test_openapi_exposes_only_active_website_workflow(self) -> None:
        from backend.app.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(dependencies_for(Path(directory) / "history.db")))
            paths = set(client.get("/openapi.json").json()["paths"])

        self.assertEqual(
            paths,
            {
                "/analysis/website",
                "/analysis/history",
                "/analysis/history/{run_id}",
            },
        )

    def test_unexpected_exception_is_sanitized_by_api_boundary(self) -> None:
        from backend.app.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"

            def unexpected_scrape(url: str, deadline: float):
                raise RuntimeError("secret internal stack detail")

            client = TestClient(
                create_app(dependencies_for(path, scrape=unexpected_scrape)),
                raise_server_exceptions=False,
            )
            response = client.post(
                "/analysis/website",
                json={"url": "https://public.example/reviews"},
            )

        self._assert_error(response, "scrape_failed", 500, "request")
        self.assertNotIn("secret", response.json()["error"]["message"])

    def _assert_error(
        self,
        response,
        code: str,
        status_code: int,
        stage: str,
    ) -> None:
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(set(response.json()), {"error"})
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        self.assertEqual(error["stage"], stage)
        self.assertEqual(
            set(error),
            {"code", "message", "stage", "retryable", "details"},
        )


if __name__ == "__main__":
    unittest.main()
