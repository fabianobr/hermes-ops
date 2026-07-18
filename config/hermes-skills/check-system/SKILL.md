---
name: check-system
description: Use when the user asks /check-system, check-system, status da maquina, status do host, uso da GPU, uso da VRAM, CPU, RAM, memoria, carga, disco, temperatura da GPU, or host resource monitoring through Hermes or Telegram. Run the fixed read-only system resources script and return its concise operational report.
version: 1.2.0
author: hermes-ops
license: MIT
metadata:
  hermes:
    tags: [devops, monitoring, gpu, vram, cpu, ram, disk, telegram]
    related_skills: []
---

# Check System

## Overview

Report host GPU utilization, VRAM used/total and utilization, CPU, RAM, swap, disk, and high-memory processes through the fixed read-only script:

```bash
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

Exact `/check-system` and `/check_system` Telegram commands are configured as Hermes quick commands and return the script output without involving the LLM. Use this skill for natural-language requests that trigger the agent.

## Workflow

1. Run only the canonical script once. Complete this step only after it exits successfully and reports every available resource section, including GPU and VRAM utilization when NVIDIA telemetry is available.
2. Return the script output without inventing unavailable telemetry. Use Portuguese when the user writes in Portuguese.
3. Keep the result compact and preserve fenced `text` blocks so columns remain aligned in Telegram.
4. If GPU telemetry is unavailable, state that limitation and still return CPU, RAM, swap, disk, and process data.
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

The check is complete when the command exits zero and prints the host header, GPU utilization, VRAM used/total and utilization, CPU/RAM/disk data, and top processes. When NVIDIA telemetry is unavailable, it must print that limitation instead.
