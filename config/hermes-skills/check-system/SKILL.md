---
name: check-system
description: Use when the user asks /check-system, status da maquina, GPU, VRAM, CPU, RAM, memoria, carga, temperatura, or host resource monitoring through Hermes or Telegram. Run the fixed read-only system resources script and return a concise operational summary.
license: MIT
metadata:
  hermes:
    tags: [devops, monitoring, gpu, vram, cpu, ram, telegram]
    related_skills: []
---

# Check System

## Overview

Use this skill to answer quick host resource checks from Hermes, especially through Telegram. Prefer configuring `/check-system` as a `quick_commands` entry so the gateway runs the fixed script directly without involving the LLM.

The canonical script is:

```bash
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

## Workflow

1. Run only the canonical script above for the check.
2. Do not run arbitrary user-provided shell commands as part of this skill.
3. Summarize the output in Portuguese by default when the user writes in Portuguese.
4. Keep the Telegram response compact: GPU/VRAM first, then CPU/RAM, then any notable top process.
5. If `nvidia-smi` is missing or no GPU is available, say that GPU telemetry is unavailable and still report CPU/RAM.
6. Prefer fenced `text` blocks with aligned columns over HTML or Markdown tables; Telegram does not render either table format as real tables.

For deterministic Telegram use, configure:

```yaml
quick_commands:
  check-system:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/check_system_resources.sh
  check_system:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

## Expected Triggers

- `/check-system`
- `check-system`
- `status da maquina`
- `como esta a GPU?`
- `verifica VRAM, CPU e RAM`
- `uso de recursos do host`

## Response Shape

Prefer short headings plus fenced `text` blocks for Telegram:

````text
🧾 Status do Host

```text
Host       <hostname>
Hora       <timestamp>
```

🎮 GPU / VRAM

```text
<index>: <name>
Uso        <percent>
VRAM       <used> / <total>
Temp       <temp>
Power      <draw> / <limit>
```
````

If the script reports multiple GPUs, include one compact block per GPU.

## Safety Rules

- Keep this skill read-only.
- Do not edit config, restart services, kill processes, or install packages.
- Do not expose secrets or environment variables.
- If the user asks for remediation after seeing resource pressure, ask for explicit confirmation before taking action.

## Verification

The script can be validated manually with:

```bash
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```
