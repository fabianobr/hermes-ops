import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts" / "check_system_resources.sh"


class CheckSystemResourcesTests(unittest.TestCase):
    def run_script(self, commands=None, **environment):
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory)
            for name, body in (commands or {}).items():
                command = binary_directory / name
                command.write_text("#!/bin/sh\n" + body, encoding="utf-8")
                command.chmod(command.stat().st_mode | stat.S_IXUSR)

            process_environment = os.environ.copy()
            process_environment.update(environment)
            process_environment["PATH"] = f"{binary_directory}:{process_environment['PATH']}"
            return subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=REPOSITORY,
                env=process_environment,
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )

    def test_formats_running_models_from_api(self):
        payload = json.dumps(
            {
                "models": [
                    {
                        "name": "qwen-test:latest",
                        "size": 4 * 1024**3,
                        "size_vram": 3 * 1024**3,
                    }
                ]
            }
        )
        result = self.run_script(
            {"curl": f"printf '%s' '{payload}'\n"},
            OLLAMA_HOST="http://ollama.test:11434/",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("qwen-test:latest", result.stdout)
        self.assertIn("4.0 GiB", result.stdout)
        self.assertIn("75% GPU", result.stdout)

    def test_invalid_api_json_falls_back_to_cli(self):
        result = self.run_script(
            {
                "curl": "printf 'not-json'\n",
                "ollama": "printf 'NAME ID SIZE PROCESSOR UNTIL\\nmodel:latest id 1GB 100%%GPU 1m\\n'\n",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("model:latest", result.stdout)

    def test_rejects_non_http_ollama_host(self):
        result = self.run_script(OLLAMA_HOST="file:///etc/passwd")

        self.assertEqual(result.returncode, 2)
        self.assertIn("must use an http:// or https:// URL", result.stderr)

    def test_rejects_invalid_disk_threshold(self):
        result = self.run_script(CHECK_SYSTEM_DISK_ALERT_THRESHOLD="101")

        self.assertEqual(result.returncode, 2)
        self.assertIn("integer from 0 to 100", result.stderr)


if __name__ == "__main__":
    unittest.main()
