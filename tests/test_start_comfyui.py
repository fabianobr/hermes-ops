"""Behavior tests for the bounded ComfyUI start script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "start_comfyui.sh"

# Minimal docker stub. STATES holds one "status<TAB>health" line per inspect
# call, so a test can describe how the container evolves while the script waits.
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
    sed -i '1d' "${state_file}"
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

            state_file = directory / "states"
            state_file.write_text("".join(f"{state}\n" for state in states), encoding="utf-8")
            log_file = directory / "calls"
            log_file.write_text("", encoding="utf-8")

            environment = os.environ.copy()
            environment["PATH"] = f"{directory}:{environment.get('PATH', '')}"
            environment["FAKE_DOCKER_STATE_FILE"] = str(state_file)
            environment["FAKE_DOCKER_LOG_FILE"] = str(log_file)
            environment["COMFYUI_START_TIMEOUT"] = "0"
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
        result = self.run_script(["running\thealthy", "running\thealthy"])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Ja Estava no Ar", result.stdout)
        self.assertNotIn("start comfyui", result.stderr)

    def test_starts_existing_stopped_container(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\thealthy", "running\thealthy"]
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("start comfyui", result.stderr)
        self.assertIn("ComfyUI Disponivel", result.stdout)

    def test_uses_compose_when_container_is_absent(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yml") as compose_file:
            result = self.run_script(
                ["absent", "running\thealthy", "running\thealthy"],
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

    def test_reports_logs_when_container_never_becomes_healthy(self) -> None:
        result = self.run_script(
            ["exited\tunhealthy", "running\tstarting", "running\tstarting"]
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Timeout", result.stdout)
        self.assertIn("linha de log de exemplo", result.stdout)

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

    def test_rejects_non_numeric_timeout(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            cwd=REPO_ROOT,
            env={**os.environ, "COMFYUI_START_TIMEOUT": "abc"},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("integer number of seconds", result.stderr)


if __name__ == "__main__":
    unittest.main()
