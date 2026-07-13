"""Test environment loading, browser launch, and process supervision."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_app import (
    PROJECT_ROOT,
    build_commands,
    load_project_environment,
    run,
    stop_process,
)


class RecordingEnvironmentLoader:
    """Record dotenv loader calls and optionally simulate a loading failure."""

    def __init__(self, *, error=None):
        """Configure optional failure and initialize recorded calls."""

        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        """Record a dotenv call or raise the configured safe-test error."""

        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error


class FakeProcess:
    """Simulate a child process across running, exited, and stubborn states."""

    def __init__(self, *, returncode=None, stubborn=False, events=None):
        """Configure initial exit state and graceful-shutdown behavior."""

        self.returncode = returncode
        self.stubborn = stubborn
        self.terminated = False
        self.killed = False
        self.waited = False
        self._wait_calls = 0
        self.events = events if events is not None else []

    def poll(self):
        """Return the simulated child exit code without blocking."""

        self.events.append("poll")
        return self.returncode

    def terminate(self):
        """Record a graceful termination request."""

        self.events.append("terminate")
        self.terminated = True

    def wait(self, timeout=None):
        """Complete shutdown or simulate one graceful-timeout failure."""

        self.events.append(("wait", timeout))
        self.waited = True
        self._wait_calls += 1
        if self.stubborn and self._wait_calls == 1:
            raise subprocess.TimeoutExpired("fake-process", timeout)
        self.returncode = -9 if self.killed else 0
        return self.returncode

    def kill(self):
        """Record forced termination of a stubborn child."""

        self.events.append("kill")
        self.killed = True


class FakePopen:
    """Simulate ordered process startup and optional launch failure."""

    def __init__(self, processes, *, fail_on_call=None):
        """Configure child results and which launch, if any, raises."""

        self.processes = processes
        self.fail_on_call = fail_on_call
        self.calls = []

    def __call__(self, command, **kwargs):
        """Record an argument-list launch and return its configured process."""

        self.calls.append((command, kwargs))
        call_number = len(self.calls)
        if call_number == self.fail_on_call:
            raise OSError("could not start child")
        return self.processes[call_number - 1]


class RunAppTests(unittest.TestCase):
    """Group launcher command, lifecycle, and exit-code regression contracts."""

    def test_project_environment_loads_root_dotenv_without_override(self):
        """Anchor dotenv loading to the project root and preserve parent values."""

        loader = RecordingEnvironmentLoader()

        load_project_environment(loader=loader)

        self.assertEqual(
            loader.calls,
            [((PROJECT_ROOT / ".env",), {"override": False})],
        )

    def test_existing_environment_value_takes_precedence_over_dotenv(self):
        """Keep a process value when the project dotenv defines the same name."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "GROQ_API_KEY=dotenv-value\n",
                encoding="utf-8",
            )
            with (
                patch("run_app.PROJECT_ROOT", root),
                patch.dict(
                    os.environ,
                    {"GROQ_API_KEY": "process-value"},
                    clear=True,
                ),
            ):
                load_project_environment()
                self.assertEqual(os.environ["GROQ_API_KEY"], "process-value")

    def test_environment_load_failure_stops_before_child_start(self):
        """Return safely before starting children when dotenv loading raises."""

        loader = RecordingEnvironmentLoader(error=OSError("secret file details"))
        fake_popen = FakePopen([])
        messages = []

        self.assertEqual(
            run(
                popen=fake_popen,
                load_environment=lambda: load_project_environment(loader=loader),
                report=messages.append,
            ),
            1,
        )

        self.assertEqual(fake_popen.calls, [])
        self.assertEqual(
            messages,
            [f"Could not load configuration from {PROJECT_ROOT / '.env'}."],
        )
        self.assertNotIn("secret file details", messages[0])

    def test_commands_use_current_python_without_a_shell(self):
        """Build argument lists around the supplied current interpreter."""

        backend, dashboard = build_commands(r"C:\Python\python.exe")
        self.assertEqual(
            backend,
            [
                r"C:\Python\python.exe",
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
        )
        self.assertEqual(
            dashboard,
            [
                r"C:\Python\python.exe",
                "-m",
                "streamlit",
                "run",
                "dashboard/streamlit_app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                "8501",
                "--server.headless",
                "true",
            ],
        )

    def test_both_children_launch_from_project_root_without_shell(self):
        """Launch exact argument arrays from the project root without a shell."""

        fake_popen = FakePopen([FakeProcess(returncode=0), FakeProcess()])
        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=lambda _: None,
                python_executable=r"C:\Python\python.exe",
            ),
            1,
        )
        backend, dashboard = build_commands(r"C:\Python\python.exe")
        self.assertEqual(
            fake_popen.calls,
            [
                (backend, {"cwd": PROJECT_ROOT}),
                (dashboard, {"cwd": PROJECT_ROOT}),
            ],
        )
        self.assertTrue(all("shell" not in kwargs for _, kwargs in fake_popen.calls))

    def test_ctrl_c_terminates_and_waits_for_both_children(self):
        """Treat Ctrl+C as success after gracefully reaping both peers."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])

        def interrupting_sleep(_):
            """Simulate the user's Ctrl+C during the supervision poll loop."""

            raise KeyboardInterrupt

        self.assertEqual(run(popen=fake_popen, sleep=interrupting_sleep), 0)
        self.assertTrue(
            all(
                process.terminated and process.waited
                for process in fake_popen.processes
            )
        )

    def test_peer_exit_stops_survivor_and_returns_failure(self):
        """Propagate peer failure and terminate the still-running counterpart."""

        backend = FakeProcess(returncode=2)
        streamlit = FakeProcess()
        fake_popen = FakePopen([backend, streamlit])

        self.assertEqual(run(popen=fake_popen, sleep=lambda _: None), 2)
        self.assertTrue(streamlit.terminated)

    def test_second_start_failure_stops_first_child(self):
        """Clean up the backend when dashboard startup raises an OS error."""

        backend = FakeProcess()
        fake_popen = FakePopen([backend], fail_on_call=2)

        self.assertEqual(run(popen=fake_popen), 1)
        self.assertTrue(backend.terminated)

    def test_stubborn_child_is_killed_after_graceful_timeout(self):
        """Escalate from terminate to kill after the shutdown grace period."""

        events = []
        stubborn_process = FakeProcess(stubborn=True, events=events)

        stop_process(stubborn_process, timeout=2.5)

        self.assertTrue(stubborn_process.killed)
        self.assertEqual(
            events,
            ["poll", "terminate", ("wait", 2.5), "kill", ("wait", None)],
        )

    def test_already_exited_child_skips_shutdown_actions(self):
        """Leave an already-reaped child untouched after the initial status check."""

        events = []
        process = FakeProcess(returncode=0, events=events)

        stop_process(process)

        self.assertEqual(events, ["poll"])
        self.assertFalse(process.terminated)
        self.assertFalse(process.killed)
        self.assertFalse(process.waited)


if __name__ == "__main__":
    unittest.main()
