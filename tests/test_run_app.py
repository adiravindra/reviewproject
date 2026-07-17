"""Test environment loading, browser launch, and process supervision."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

from run_app import (
    BACKEND_HEALTH_URL,
    DASHBOARD_HEALTH_URL,
    DASHBOARD_URL,
    PROJECT_ROOT,
    READINESS_REQUEST_TIMEOUT_SECONDS,
    STARTUP_TIMEOUT_SECONDS,
    backend_is_ready,
    build_commands,
    dashboard_is_ready,
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


class FakeHealthResponse:
    """Provide the response context and status used by readiness tests."""

    def __init__(self, status, body=b''):
        """Store the HTTP status returned by the fake context manager."""

        self.status = status
        self.body = body

    def __enter__(self):
        """Return this fake as the opened response context."""

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Leave the fake response context without suppressing errors."""

        return False

    def read(self, *_):
        """Return the configured response content for JSON decoding."""

        return self.body


class SequenceResult:
    """Return deterministic values across consecutive readiness checks."""

    def __init__(self, values):
        """Create an iterator over deterministic readiness results."""

        self.values = iter(values)

    def __call__(self):
        """Return the next configured readiness value."""

        return next(self.values)


class FakeProcess:
    """Simulate a child process across running, exited, and stubborn states."""

    def __init__(
        self,
        *,
        returncode=None,
        returncodes=None,
        stubborn=False,
        events=None,
    ):
        """Configure initial exit state and graceful-shutdown behavior."""

        self.returncode = returncode
        self.returncodes = iter(returncodes) if returncodes is not None else None
        self.stubborn = stubborn
        self.terminated = False
        self.killed = False
        self.waited = False
        self._wait_calls = 0
        self.events = events if events is not None else []

    def poll(self):
        """Return the simulated child exit code without blocking."""

        self.events.append("poll")
        if self.returncodes is not None:
            try:
                self.returncode = next(self.returncodes)
            except StopIteration:
                pass
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

    def test_dashboard_readiness_uses_local_health_endpoint_and_timeout(self):
        """Probe Streamlit's fixed local health URL with a bounded timeout."""

        calls = []

        def urlopen(url, *, timeout):
            """Record the readiness request and return a healthy response."""

            calls.append((url, timeout))
            return FakeHealthResponse(200)

        self.assertTrue(dashboard_is_ready(urlopen=urlopen))
        self.assertEqual(
            calls,
            [(DASHBOARD_HEALTH_URL, READINESS_REQUEST_TIMEOUT_SECONDS)],
        )

    def test_backend_readiness_requires_the_expected_health_response(self):
        """Probe the backend health contract with the bounded local request."""

        calls = []

        def urlopen(url, *, timeout):
            """Record the readiness request and return the healthy payload."""

            calls.append((url, timeout))
            return FakeHealthResponse(200, b'{"status": "ok"}')

        self.assertTrue(backend_is_ready(urlopen=urlopen))
        self.assertEqual(
            calls,
            [(BACKEND_HEALTH_URL, READINESS_REQUEST_TIMEOUT_SECONDS)],
        )

    def test_dashboard_readiness_treats_transient_failures_as_not_ready(self):
        """Convert local connection failures into a retryable not-ready result."""

        cases = [URLError("not listening"), OSError("socket unavailable")]
        for error in cases:
            with self.subTest(error=error):

                def urlopen(url, *, timeout, error=error):
                    """Raise one configured transient readiness error."""

                    raise error

                self.assertFalse(dashboard_is_ready(urlopen=urlopen))

    def test_browser_opens_once_only_after_dashboard_is_ready(self):
        """Open the dashboard once after readiness and never before it."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        readiness = SequenceResult([False, True])
        opened = []
        sleep_calls = 0

        def sleep(_):
            """Stop the simulated supervisor after three polling passes."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 3:
                raise KeyboardInterrupt

        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=sleep,
                load_environment=lambda: None,
                backend_ready=lambda: True,
                dashboard_ready=readiness,
                open_browser=lambda url: opened.append(url) or True,
            ),
            0,
        )

        self.assertEqual(opened, [DASHBOARD_URL])

    def test_browser_waits_until_backend_and_dashboard_are_ready(self):
        """Open only after both local application peers report healthy."""

        backend_ready = SequenceResult([False, True])
        dashboard_ready = SequenceResult([True, True])
        opened = []
        sleep_calls = 0

        def sleep(_):
            """Stop the simulated supervisor after the readiness transition."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 3:
                raise KeyboardInterrupt

        result = run(
            popen=FakePopen([FakeProcess(), FakeProcess()]),
            sleep=sleep,
            load_environment=lambda: None,
            backend_ready=backend_ready,
            dashboard_ready=dashboard_ready,
            open_browser=lambda url: opened.append(url) or True,
        )

        self.assertEqual(result, 0)
        self.assertEqual(opened, [DASHBOARD_URL])

    def test_dashboard_launch_waits_for_backend_readiness(self):
        """Start Streamlit only after the backend health gate succeeds."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        launch_counts_at_backend_probe = []
        backend_results = iter([False, True])
        sleep_calls = 0

        def backend_ready():
            """Record how many children exist at each backend health probe."""

            launch_counts_at_backend_probe.append(len(fake_popen.calls))
            return next(backend_results)

        def sleep(_):
            """Stop after backend readiness allows dashboard supervision."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 2:
                raise KeyboardInterrupt

        result = run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            backend_ready=backend_ready,
            dashboard_ready=lambda: True,
            open_browser=lambda _: True,
        )

        self.assertEqual(result, 0)
        self.assertEqual(launch_counts_at_backend_probe, [1, 1])
        self.assertEqual(len(fake_popen.calls), 2)

    def test_backend_timeout_never_starts_dashboard_and_cleans_backend(self):
        """Stop a timed-out backend without launching the dashboard."""

        backend = FakeProcess()
        unused_dashboard = FakeProcess()
        fake_popen = FakePopen([backend, unused_dashboard])
        messages = []

        result = run(
            popen=fake_popen,
            sleep=lambda _: None,
            load_environment=lambda: None,
            backend_ready=lambda: False,
            monotonic=SequenceResult([0.0, STARTUP_TIMEOUT_SECONDS]),
            report=messages.append,
        )

        self.assertEqual(result, 1)
        self.assertEqual(len(fake_popen.calls), 1)
        self.assertTrue(backend.terminated)
        self.assertFalse(unused_dashboard.terminated)
        self.assertEqual(
            messages,
            ["The application did not become ready within 30 seconds."],
        )

    def test_backend_exit_before_readiness_never_starts_dashboard(self):
        """Return an early backend failure before starting Streamlit."""

        backend = FakeProcess(returncode=7)
        unused_dashboard = FakeProcess()
        fake_popen = FakePopen([backend, unused_dashboard])

        result = run(
            popen=fake_popen,
            sleep=lambda _: None,
            load_environment=lambda: None,
            backend_ready=lambda: False,
        )

        self.assertEqual(result, 7)
        self.assertEqual(len(fake_popen.calls), 1)
        self.assertFalse(unused_dashboard.terminated)

    def test_dashboard_exit_after_backend_readiness_cleans_backend(self):
        """Clean the ready backend when the dashboard exits during startup."""

        backend = FakeProcess()
        dashboard = FakeProcess(returncode=4)
        fake_popen = FakePopen([backend, dashboard])
        backend_readiness_calls = 0

        def backend_ready():
            """Record the backend gate before allowing dashboard startup."""

            nonlocal backend_readiness_calls
            backend_readiness_calls += 1
            return True

        result = run(
            popen=fake_popen,
            sleep=lambda _: None,
            load_environment=lambda: None,
            backend_ready=backend_ready,
            dashboard_ready=lambda: False,
        )

        self.assertEqual(result, 4)
        self.assertEqual(backend_readiness_calls, 1)
        self.assertTrue(backend.terminated)

    def test_browser_requires_staged_backend_and_dashboard_health(self):
        """Open only after ordered backend and dashboard health gates."""

        events = []
        processes = iter([FakeProcess(), FakeProcess()])
        backend_results = iter([False, True, True])
        dashboard_results = iter([False, True])
        sleep_calls = 0

        def popen(command, **kwargs):
            """Record each child launch while returning its fake process."""

            label = "launch_backend" if "uvicorn" in command else "launch_dashboard"
            events.append(label)
            return next(processes)

        def backend_ready():
            """Record each backend health result."""

            result = next(backend_results)
            events.append(f"backend:{result}")
            return result

        def dashboard_ready():
            """Record each dashboard health result."""

            result = next(dashboard_results)
            events.append(f"dashboard:{result}")
            return result

        def open_browser(_):
            """Record the browser action after both gates."""

            events.append("open_browser")
            return True

        def sleep(_):
            """Stop after both staged readiness transitions complete."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 3:
                raise KeyboardInterrupt

        result = run(
            popen=popen,
            sleep=sleep,
            load_environment=lambda: None,
            backend_ready=backend_ready,
            dashboard_ready=dashboard_ready,
            open_browser=open_browser,
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            events,
            [
                "launch_backend",
                "backend:False",
                "backend:True",
                "launch_dashboard",
                "dashboard:False",
                "dashboard:True",
                "open_browser",
            ],
        )

    def test_startup_timeout_stops_children_without_opening_browser(self):
        """Bound a never-ready startup and report the safe timeout guidance."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        messages = []
        opened = []

        result = run(
            popen=fake_popen,
            sleep=lambda _: None,
            load_environment=lambda: None,
            backend_ready=lambda: True,
            dashboard_ready=lambda: False,
            monotonic=SequenceResult([0.0, STARTUP_TIMEOUT_SECONDS]),
            open_browser=lambda url: opened.append(url) or True,
            report=messages.append,
        )

        self.assertEqual(result, 1)
        self.assertTrue(all(process.terminated for process in fake_popen.processes))
        self.assertEqual(opened, [])
        self.assertEqual(
            messages,
            ["The application did not become ready within 30 seconds."],
        )

    def test_ready_application_continues_past_startup_timeout(self):
        """Keep supervising healthy peers after the startup deadline passes."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        messages = []
        opened = []
        sleep_calls = 0
        clock_calls = 0

        def sleep(_):
            """End sustained healthy supervision with an explicit Ctrl+C."""

            nonlocal sleep_calls
            sleep_calls += 1
            raise KeyboardInterrupt

        def monotonic():
            """Advance the startup clock beyond the readiness deadline."""

            nonlocal clock_calls
            clock_calls += 1
            return [0.0, STARTUP_TIMEOUT_SECONDS + 1.0][clock_calls - 1]

        result = run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            backend_ready=lambda: True,
            dashboard_ready=lambda: True,
            monotonic=monotonic,
            open_browser=lambda url: opened.append(url) or True,
            report=messages.append,
        )

        self.assertEqual(result, 0)
        self.assertEqual(clock_calls, 2)
        self.assertEqual(sleep_calls, 1)
        self.assertEqual(opened, [DASHBOARD_URL])
        self.assertEqual(messages, [])

    def test_full_readiness_disables_shared_startup_timeout(self):
        """Keep supervising after both staged gates beat the shared deadline."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        backend_probe_launch_counts = []
        messages = []
        opened = []
        clock_calls = 0

        def backend_ready():
            """Record that only the backend exists at its successful probe."""

            backend_probe_launch_counts.append(len(fake_popen.calls))
            return True

        def monotonic():
            """Advance past the shared startup deadline after full readiness."""

            nonlocal clock_calls
            clock_calls += 1
            return [0.0, STARTUP_TIMEOUT_SECONDS + 1.0][clock_calls - 1]

        def sleep(_):
            """End healthy supervision explicitly after the deadline."""

            raise KeyboardInterrupt

        result = run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            backend_ready=backend_ready,
            dashboard_ready=lambda: True,
            monotonic=monotonic,
            open_browser=lambda url: opened.append(url) or True,
            report=messages.append,
        )

        self.assertEqual(result, 0)
        self.assertEqual(backend_probe_launch_counts, [1])
        self.assertEqual(clock_calls, 2)
        self.assertEqual(opened, [DASHBOARD_URL])
        self.assertEqual(messages, [])

    def test_browser_failure_reports_manual_url_and_keeps_supervising(self):
        """Report a manual URL while preserving supervision on a false result."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        messages = []
        sleep_calls = 0

        def sleep(_):
            """Stop the simulated supervisor after browser failure is observed."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 2:
                raise KeyboardInterrupt

        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=sleep,
                load_environment=lambda: None,
                backend_ready=lambda: True,
                dashboard_ready=lambda: True,
                open_browser=lambda _: False,
                report=messages.append,
            ),
            0,
        )

        self.assertEqual(
            messages,
            [
                f"Open {DASHBOARD_URL} manually; "
                "the default browser could not be started."
            ],
        )
        self.assertTrue(all(process.terminated for process in fake_popen.processes))

    def test_browser_exception_is_safe_and_not_retried(self):
        """Sanitize a browser exception and keep the launch attempt one-shot."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])
        messages = []
        attempts = 0
        sleep_calls = 0

        def open_browser(_):
            """Raise a browser error containing details that must stay private."""

            nonlocal attempts
            attempts += 1
            raise OSError("browser internals")

        def sleep(_):
            """Stop after enough polls to expose any incorrect browser retry."""

            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 2:
                raise KeyboardInterrupt

        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=sleep,
                load_environment=lambda: None,
                backend_ready=lambda: True,
                dashboard_ready=lambda: True,
                open_browser=open_browser,
                report=messages.append,
            ),
            0,
        )

        self.assertEqual(attempts, 1)
        self.assertEqual(len(messages), 1)
        self.assertNotIn("browser internals", messages[0])

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

        fake_popen = FakePopen([FakeProcess(), FakeProcess(returncode=0)])
        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=lambda _: None,
                python_executable=r"C:\Python\python.exe",
                backend_ready=lambda: True,
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

    def test_ctrl_c_during_backend_startup_terminates_and_waits_for_backend(self):
        """Treat Ctrl+C as success and reap whichever child has started."""

        fake_popen = FakePopen([FakeProcess(), FakeProcess()])

        def interrupting_sleep(_):
            """Simulate the user's Ctrl+C during the supervision poll loop."""

            raise KeyboardInterrupt

        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=interrupting_sleep,
                backend_ready=lambda: False,
                dashboard_ready=lambda: False,
            ),
            0,
        )
        self.assertEqual(len(fake_popen.calls), 1)
        self.assertTrue(fake_popen.processes[0].terminated)
        self.assertTrue(fake_popen.processes[0].waited)
        self.assertFalse(fake_popen.processes[1].terminated)

    def test_peer_exit_stops_survivor_and_returns_failure(self):
        """Propagate peer failure and terminate the still-running counterpart."""

        backend = FakeProcess(returncodes=[None, 2])
        streamlit = FakeProcess()
        fake_popen = FakePopen([backend, streamlit])

        self.assertEqual(
            run(
                popen=fake_popen,
                sleep=lambda _: None,
                backend_ready=lambda: True,
            ),
            2,
        )
        self.assertTrue(streamlit.terminated)

    def test_second_start_failure_stops_first_child(self):
        """Clean up the backend when dashboard startup raises an OS error."""

        backend = FakeProcess()
        fake_popen = FakePopen([backend], fail_on_call=2)

        self.assertEqual(run(popen=fake_popen, backend_ready=lambda: True), 1)
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
