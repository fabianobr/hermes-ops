---
name: check-system
description: Use when the user asks /check-system, check-system, acione/execute/rode a habilidade check system, faca um check do sistema, status da maquina, status do host, resuma os gargalos do host, modelos Ollama em execucao, ollama ps, uso da GPU, uso da VRAM, CPU, RAM, memoria, carga, disco, temperatura da GPU, or host resource monitoring through Hermes or Telegram. Run the fixed read-only system resources script and return its concise operational report.
license: MIT
metadata:
  hermes:
    version: 1.3.0
    author: hermes-ops
    tags: [devops, monitoring, gpu, vram, cpu, ram, disk, ollama, telegram]
    related_skills: []
---

# Check System

## Overview

Report host GPU utilization, VRAM used/total and utilization, CPU, RAM, swap, disk, `ollama ps`, and high-memory processes through the fixed read-only script:

```bash
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

Exact `/check-system` and `/check_system` Telegram commands are configured as Hermes quick commands and return the script output without involving the LLM. Use this skill for natural-language requests that trigger the agent.

For a natural-language request, execute the canonical `bash` command above through the terminal tool. Never run bare `check_system`, `check-system`, `/check_system`, or `/check-system` as a shell command; those names are Telegram quick-command triggers, not executables.

## Workflow

1. For natural-language requests, run only `bash ~/AI/hermes-ops/scripts/check_system_resources.sh` once. Complete this step only after it exits successfully and reports every available resource section, including GPU/VRAM utilization and `ollama ps` when those commands are available.
2. Return the script output without inventing unavailable telemetry. Use Portuguese when the user writes in Portuguese.
3. Keep the result compact and preserve fenced `text` blocks so columns remain aligned in Telegram.
4. If GPU telemetry or `ollama ps` is unavailable, state that limitation and still return the remaining resource data.
5. If the script emits a disk-pressure alert, offer a separate read-only investigation. Do not diagnose or delete files as part of this skill.

## Safety Rules

- Keep the workflow read-only.
- Do not accept or append arbitrary shell arguments to the canonical command.
- Do not edit configuration, restart services, kill processes, install packages, or remove files.
- Do not expose secrets or environment variables.
- Treat remediation as a separate task requiring explicit user authorization.

## Verification

Validate the canonical script with:

```bash
bash -n ~/AI/hermes-ops/scripts/check_system_resources.sh
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

The check is complete when the command exits zero and prints the host header, GPU utilization, VRAM used/total and utilization, CPU/RAM/disk data, `ollama ps`, and top processes. When NVIDIA or Ollama telemetry is unavailable, it must print that limitation instead.
