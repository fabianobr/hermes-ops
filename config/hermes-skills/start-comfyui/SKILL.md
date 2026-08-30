---
name: start-comfyui
description: Use when the user asks /start-comfyui, start comfyui, acione/execute/rode/utilize a habilidade start comfyui, inicie/inicia/sobe/suba/liga/ligue/levante o comfyui, start/subir o container do comfyui, ative o comfyui, o comfyui esta fora do ar, or otherwise asks to bring the local ComfyUI container up through Hermes or Telegram. Run the fixed start script and return its status report.
license: MIT
metadata:
  hermes:
    version: 1.0.0
    author: hermes-ops
    tags: [devops, docker, comfyui, gpu, vram, telegram]
    related_skills: [check-system]
---

# Start ComfyUI

## Overview

Bring the local ComfyUI container up and report its final state through the fixed script:

```bash
bash ~/AI/hermes-ops/scripts/start_comfyui.sh
```

The script is idempotent: if the container is already running it reports that and starts nothing. It starts an existing stopped container with `docker start`, and falls back to `docker compose up -d --no-build` only when the container does not exist yet. It never builds images, never stops or removes containers, and accepts no arguments.

Exact `/start-comfyui` and `/start_comfyui` Telegram commands are configured as Hermes quick commands and return the script output without involving the LLM. Use this skill for natural-language requests that trigger the agent.

For a natural-language request, execute the canonical `bash` command above through the terminal tool. Never run bare `start_comfyui`, `start-comfyui`, `/start_comfyui`, or `/start-comfyui` as a shell command; those names are Telegram quick-command triggers, not executables.

## Workflow

1. For natural-language requests, run only `bash ~/AI/hermes-ops/scripts/start_comfyui.sh` once. Do not run it again while the previous run is still waiting for the health check.
2. Return the script output without inventing state the script did not report. Use Portuguese when the user writes in Portuguese.
3. Keep the result compact and preserve fenced `text` blocks so columns remain aligned in Telegram.
4. When the script exits successfully, include the service address it printed so the user can open the interface.
5. When the script fails, return the log lines it printed and stop. Diagnosis and remediation are a separate task requiring explicit user authorization.
6. The GPU is shared with Ollama on this host. If the script reports low free VRAM, relay that warning instead of retrying the start.

## Safety Rules

- Run only the canonical command, with no arguments appended.
- Starting the container is the only write action allowed by this skill.
- Do not stop, restart, remove, or rebuild containers, and do not run `docker compose down`, `docker build`, or any prune command.
- Do not edit Compose files, `.env` files, or Hermes configuration.
- Do not expose secrets or environment variables.
- Do not free VRAM by killing processes or unloading Ollama models; ask the user first.

## Verification

Validate the canonical script with:

```bash
bash -n ~/AI/hermes-ops/scripts/start_comfyui.sh
python3 -m unittest tests.test_start_comfyui
bash ~/AI/hermes-ops/scripts/start_comfyui.sh
```

The check is complete when the command prints the header, the start action taken, the final container status and health, and either the service address on success or the recent log lines on failure. When Docker is unavailable or its daemon is unreachable, it must print that limitation and exit non-zero instead.
