import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class ErrorEnvelopeTests(unittest.TestCase):
    def test_invalid_url_uses_consistent_error_envelope(self) -> None:
        response = TestClient(app).post(
            "/analysis/website",
            json={"url": "file:///etc/passwd"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(set(response.json()), {"error"})
        error = response.json()["error"]
        self.assertEqual(error["code"], "invalid_url")
        self.assertEqual(error["stage"], "validation")
        self.assertFalse(error["retryable"])
        self.assertEqual(
            set(error),
            {"code", "message", "stage", "retryable", "details"},
        )
        self.assertNotIn("etc/passwd", error["message"])


if __name__ == "__main__":
    unittest.main()
