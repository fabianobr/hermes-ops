"""Behavior tests for the bounded ComfyUI start script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "start_comfyui.sh"

# Minimal docker stub. The state file holds one "status<TAB>health" line per
# inspect call, so a test can describe how the container evolves while the
# script waits. The last line is kept and repeated once consumed, so a test
# only has to describe the transitions it cares about.
FAKE_DOCKER = """\
#!/usr/bin/env bash
state_file="${FAKE_DOCKER_STATE_FILE}"
log_file="${FAKE_DOCKER_LOG_FILE}"
printf '%s\\n' "$*" >>"${log_file}"

case "$1" in
  info)
    [ "${FAKE_DOCKER_INFO_FAILS:-0}" = "1" ] && exit 1
    exit 0
    ;;
  inspect)
    line="$(head -n 1 "${state_file}")"
    if [ "$(wc -l <"${state_file}")" -gt 1 ]; then
      sed -i '1d' "${state_file}"
    fi
    [ -z "${line}" ] && exit 1
    [ "${line}" = "absent" ] && exit 1
    printf '%s\\n' "${line}"
    exit 0
    ;;
  start|compose)
    [ "${FAKE_DOCKER_START_FAILS:-0}" = "1" ] && { echo "start refused"; exit 1; }
    exit 0
    ;;
  logs)
    echo "linha de log de exemplo"
    exit 0
    ;;
esac
exit 0
"""


# Records the budget the script asked for, then runs the real command, so a
# test can assert that docker calls are bounded rather than trusting the shape
# of the source.
FAKE_TIMEOUT = """\
#!/usr/bin/env bash
printf 'TIMEOUT %s\\n' "$1" >>"${FAKE_DOCKER_LOG_FILE}"
shift
exec "$@"
"""


class StartComfyuiTests(unittest.TestCase):
    def run_script(
        self,
        states: list[str],
        **environment_overrides: str,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            fake_docker = directory / "docker"
            fake_docker.write_text(FAKE_DOCKER, encoding="utf-8")
            fake_docker.chmod(0o700)

            fake_timeout = directory / "timeout"
            fake_timeout.write_text(FAKE_TIMEOUT, encoding="utf-8")
            fake_timeout.chmod(0o700)

            state_file = directory / "states"
            state_file.write_text(
                "".join(f"{state}\n" for state in states), encoding="utf-8"
            )
            log_file = directory / "calls"
            log_file.write_text("", encoding="utf-8")

            environment = os.environ.copy()
            environment["PATH"] = f"{directory}:{environment.get('PATH', '')}"
            environment["FAKE_DOCKER_STATE_FILE"] = str(state_file)
            environment["FAKE_DOCKER_LOG_FILE"] = str(log_file)
            environment["COMFYUI_START_TIMEOUT"] = "0"
            environment["COMFYUI_POLL_INTERVAL"] = "1"
            # Port 1 refuses immediately, so the readiness probe fails fast and
            # container health stays the only evidence in these tests.
            environment["COMFYUI_URL"] = "http://127.0.0.1:1"
            environment.update(environment_overrides)

            result = subprocess.run(
                ["bash", str(SCRIPT_PATH)],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            result.stderr += log_file.read_text(encoding="utf-8")
            return result

    def test_reports_already_running_without_starting(self) -> None:
        result = self.run_script(["running\thealthy"])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Ja Estava no Ar", result.stdout)
        self.assertNotIn("start comfyui", result.stderr)

    def test_running_but_unhealthy_is_not_reported_as_success(self) -> None:
        result = self.run_script(["running\tunhealthy"])
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Em Execucao Sem Responder", result.stdout)
        self.assertNotIn("ComfyUI Disponivel", result.stdout)
        self.assertIn("linha de log de exemplo", result.stdout)
        # A container that is already up must never be restarted by this path.
        self.assertNotIn("start comfyui", result.stderr)

    def test_starts_existing_stopped_container(self) -> None:
        result = self.run_script(["exited\tunhealthy", "running\thealthy"])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("start comfyui", result.stderr)
        self.assertIn("ComfyUI Disponivel", result.stdout)

    def test_uses_compose_when_container_is_absent(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yml") as compose_file:
            result = self.run_script(
                ["absent", "running\thealthy"],
                COMFYUI_COMPOSE_FILE=compose_file.name,
            )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("compose", result.stderr)
        self.assertIn("--no-build", result.stderr)

    def test_fails_when_container_is_absent_and_compose_file_is_missing(self) -> None:
        result = self.run_script(
            ["absent"],
            COMFYUI_COMPOSE_FILE="/nonexistent/docker-compose.yml",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("nao encontrado", result.stdout)

    def test_waits_across_polls_before_reporting_success(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\tstarting", "running\thealthy"],
            COMFYUI_START_TIMEOUT="6",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        # The first poll is not ready, so readiness must be reported after at
        # least one sleep rather than at zero seconds.
        self.assertNotIn("Pronto      0s", result.stdout)
        self.assertIn("ComfyUI Disponivel", result.stdout)

    def test_stops_waiting_when_the_container_dies(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\tstarting", "exited\tunhealthy"],
            COMFYUI_START_TIMEOUT="9",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Parou", result.stdout)
        self.assertIn("linha de log de exemplo", result.stdout)

    def test_reports_logs_when_container_never_becomes_healthy(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\tstarting"],
            COMFYUI_START_TIMEOUT="2",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Timeout", result.stdout)
        self.assertIn("linha de log de exemplo", result.stdout)

    def test_final_state_matches_the_failing_exit(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\tstarting"],
            COMFYUI_START_TIMEOUT="2",
        )
        self.assertEqual(result.returncode, 1)
        # The reported state must be the one the exit decision used, never a
        # fresher inspect that contradicts the log dump next to it.
        self.assertIn("Saude      starting", result.stdout)

    def test_bounds_docker_calls_with_timeout(self) -> None:
        result = self.run_script(["running\thealthy"])
        self.assertEqual(result.returncode, 0, result.stdout)
        budgets = [
            line for line in result.stderr.splitlines() if line.startswith("TIMEOUT ")
        ]
        # A wedged daemon can accept the socket and never answer, so both the
        # info probe and every inspect must carry a budget.
        self.assertGreaterEqual(len(budgets), 2, result.stderr)
        for budget in budgets:
            self.assertRegex(budget, r"^TIMEOUT \d+s$")

    def test_fails_when_docker_daemon_is_unreachable(self) -> None:
        result = self.run_script([], FAKE_DOCKER_INFO_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daemon inacessivel", result.stdout)

    def test_rejects_arguments(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH), "rm", "-rf", "/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not accept arguments", result.stderr)

    def test_rejects_non_numeric_settings(self) -> None:
        for variable in ("COMFYUI_START_TIMEOUT", "COMFYUI_POLL_INTERVAL"):
            with self.subTest(variable=variable):
                result = subprocess.run(
                    ["bash", str(SCRIPT_PATH)],
                    cwd=REPO_ROOT,
                    env={**os.environ, variable: "abc"},
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(variable, result.stderr)


if __name__ == "__main__":
    unittest.main()
