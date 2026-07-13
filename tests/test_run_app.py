import subprocess
import unittest

from run_app import build_commands, run, stop_process


class FakeProcess:
    def __init__(self, *, returncode=None, stubborn=False):
        self.returncode = returncode
        self.stubborn = stubborn
        self.terminated = False
        self.killed = False
        self.waited = False
        self._wait_calls = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True
        self._wait_calls += 1
        if self.stubborn and self._wait_calls == 1:
            raise subprocess.TimeoutExpired("fake-process", timeout)
        self.returncode = -9 if self.killed else 0
        return self.returncode

    def kill(self):
        self.killed = True


class FakePopen:
    def __init__(self, processes, *, fail_on_call=None):
        self.processes = processes
        self.fail_on_call = fail_on_call
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        call_number = len(self.calls)
        if call_number == self.fail_on_call:
            raise OSError("could not start child")
        return self.processes[call_number - 1]


class RunAppTests(unittest.TestCase):
    def test_commands_use_current_python_without_a_shell(self):
        backend, dashboard = build_commands(r"C:\Python\python.exe")
        self.assertEqual(
            backend[:3], [r"C:\Python\python.exe", "-m", "uvicorn"]
        )
        self.assertIn("backend.app.main:app", backend)
        self.assertEqual(
            dashboard[:4],
            [r"C:\Python\python.exe", "-m", "streamlit", "run"],
        )
        self.assertIn("dashboard/streamlit_app.py", dashboard)

    def test_ctrl_c_terminates_and_waits_for_both_children(self):
        fake_popen = FakePopen([FakeProcess(), FakeProcess()])

        def interrupting_sleep(_):
            raise KeyboardInterrupt

        self.assertEqual(run(popen=fake_popen, sleep=interrupting_sleep), 0)
        self.assertTrue(
            all(
                process.terminated and process.waited
                for process in fake_popen.processes
            )
        )

    def test_peer_exit_stops_survivor_and_returns_failure(self):
        backend = FakeProcess(returncode=2)
        streamlit = FakeProcess()
        fake_popen = FakePopen([backend, streamlit])

        self.assertEqual(run(popen=fake_popen, sleep=lambda _: None), 2)
        self.assertTrue(streamlit.terminated)

    def test_second_start_failure_stops_first_child(self):
        backend = FakeProcess()
        fake_popen = FakePopen([backend], fail_on_call=2)

        self.assertEqual(run(popen=fake_popen), 1)
        self.assertTrue(backend.terminated)

    def test_stubborn_child_is_killed_after_graceful_timeout(self):
        stubborn_process = FakeProcess(stubborn=True)

        stop_process(stubborn_process, timeout=0)

        self.assertTrue(stubborn_process.killed)


if __name__ == "__main__":
    unittest.main()
