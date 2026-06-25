import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, call, patch

from scripts import run_app


class RunAppTests(unittest.TestCase):
    def test_main_preloads_models_before_starting_servers(self) -> None:
        events: list[str] = []
        backend = Mock()
        frontend = Mock()
        backend.wait.side_effect = KeyboardInterrupt

        def warm_models() -> None:
            events.append("warm")

        def popen(command: list[str]) -> Mock:
            events.append(f"start:{command[2]}")
            return backend if command[2] == "uvicorn" else frontend

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with patch("scripts.run_app.ensure_models_ready", side_effect=warm_models), patch(
                "scripts.run_app.subprocess.Popen",
                side_effect=popen,
            ):
                run_app.main()

        self.assertEqual(events, ["warm", "start:uvicorn", "start:streamlit"])
        backend.terminate.assert_called_once()
        frontend.terminate.assert_called_once()

    def test_main_exits_before_starting_servers_when_model_preload_fails(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with patch(
                "scripts.run_app.ensure_models_ready",
                side_effect=RuntimeError("model download failed"),
            ), patch("scripts.run_app.subprocess.Popen") as popen:
                with self.assertRaises(SystemExit) as raised:
                    run_app.main()

        self.assertEqual(raised.exception.code, 1)
        popen.assert_not_called()

    def test_ensure_models_ready_loads_summary_and_sentiment_models(self) -> None:
        with redirect_stdout(io.StringIO()):
            with patch("scripts.run_app.ensure_summary_model_ready") as summary, patch(
                "scripts.run_app.ensure_sentiment_model_ready"
            ) as sentiment:
                run_app.ensure_models_ready()

        self.assertEqual(
            [summary.call_args, sentiment.call_args],
            [call(), call()],
        )


if __name__ == "__main__":
    unittest.main()
