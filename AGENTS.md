# Repository Guidelines

## Project Structure & Module Organization
This repository is an operations workspace, not a packaged application. Keep root-level content minimal and place material by purpose:

- `logs/`: local captured machine inventory and prerequisite checks. Keep real captures ignored and commit only sanitized examples when needed.
- `backups/`: local timestamped backup artifacts. Keep real backups ignored because they can contain host paths, topology, identifiers, or secrets.
- `scripts/`: automation helpers for repeatable checks or setup tasks.
- `config/`: active configuration files and templates.
- `docs/`: runbooks, architecture notes, and operator procedures.

Use dated filenames for snapshots (`name.YYYYMMDD-note.ext`) and avoid mixing generated outputs with maintained source files.

## Build, Test, and Development Commands
There is no formal build pipeline yet. Use focused validation commands against the files you change:

- `bash scripts/<name>.sh`: run an ops script locally.
- `python3 scripts/<name>.py`: run a Python helper.
- `docker compose -f <file> config -q`: validate Compose syntax before committing config changes.
- `shellcheck scripts/*.sh`: lint shell scripts when ShellCheck is available.
- `python3 -m py_compile scripts/*.py`: catch Python syntax errors without executing scripts.

Record noteworthy command output in `docs/` or `logs/` only when it is useful for future troubleshooting.

## Coding Style & Naming Conventions
Use 4 spaces for Python and 2 spaces for shell/Compose/YAML indentation. Prefer small, single-purpose scripts with descriptive lowercase names such as `scripts/check_ollama.sh` or `scripts/export_inventory.py`. Keep shell scripts POSIX-friendly unless Bash features are required, and add brief comments only where the intent is not obvious.

## Testing Guidelines
This repo does not currently include a test suite, so contributors should add lightweight validation with every change. For new automation, include a reproducible dry-run or verification command in the script header or related `docs/` note. Name future tests after the target behavior, for example `test_inventory_output.py`.

## Commit & Pull Request Guidelines
Use short imperative commit subjects such as `Add Ollama health check script`. Keep commits scoped to one operational change. Pull requests should include:

- a clear summary of the operational problem and fix;
- exact validation commands run;
- linked issue or incident context when applicable;
- screenshots only for UI or dashboard changes.

## Security & Configuration Tips
Do not commit secrets, tokens, `.env` files, or host-specific credentials. Sanitize logs before adding them to `logs/`, and prefer redacted examples in `docs/` when documenting local services or model endpoints.
