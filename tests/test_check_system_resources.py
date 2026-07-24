"""Behavior tests for the deterministic system resource report."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_system_resources.sh"


class CheckSystemResourcesTests(unittest.TestCase):
    def run_report_with_ollama_output(self, output: str) -> str:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake_ollama = Path(temporary_directory) / "ollama"
            fake_ollama.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env sh
                    [ "$1" = "ps" ] || exit 64
                    printf '%s\\n' {shlex.quote(output)}
                    """
                ),
                encoding="utf-8",
            )
            fake_ollama.chmod(0o700)

            environment = os.environ.copy()
            environment["PATH"] = (
                f"{temporary_directory}:{environment.get('PATH', '')}"
            )
            result = subprocess.run(
                ["bash", str(SCRIPT_PATH)],
                cwd=REPO_ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout

    def test_describes_each_running_ollama_model(self) -> None:
        output = "\n".join(
            [
                "NAME          ID              SIZE     PROCESSOR          CONTEXT    UNTIL",
                "gemma4:31b    6316f0629137    32 GB    59%/41% CPU/GPU    65536      4 minutes from now",
                "qwen3:8b      abcdef012345    6 GB     100% GPU           32768      2 minutes from now",
            ]
        )

        report = self.run_report_with_ollama_output(output)

        self.assertIn("Modelos    2", report)
        self.assertIn("Modelo     gemma4:31b", report)
        self.assertIn("Memoria    32 GB", report)
        self.assertIn("CPU/GPU    59%/41% CPU/GPU", report)
        self.assertIn("Contexto   65536 tokens", report)
        self.assertIn("Modelo     qwen3:8b", report)

    def test_reports_when_no_ollama_model_is_loaded(self) -> None:
        output = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL"

        report = self.run_report_with_ollama_output(output)

        self.assertIn("Modelos    0", report)
        self.assertIn("Estado     nenhum modelo carregado", report)


if __name__ == "__main__":
    unittest.main()
