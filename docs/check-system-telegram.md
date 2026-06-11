# Check System Through Telegram

## Purpose

Provide a direct Telegram workflow for asking Hermes about host GPU, VRAM, CPU, RAM, disk, and high-memory processes without allowing arbitrary shell execution.

## Plan

1. Keep the resource collection logic in [scripts/check_system_resources.sh](../scripts/check_system_resources.sh).
2. Keep the Hermes skill source in [config/hermes-skills/check-system/SKILL.md](../config/hermes-skills/check-system/SKILL.md).
3. Configure `/check-system` as a Hermes quick command. This is the operational path because quick commands bypass the LLM and return command output directly:

```yaml
quick_commands:
  check-system:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/check_system_resources.sh
  check_system:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

Equivalent CLI setup:

```bash
hermes config set quick_commands.check-system.type exec
hermes config set quick_commands.check-system.command 'bash ~/AI/hermes-ops/scripts/check_system_resources.sh'
hermes config set quick_commands.check_system.type exec
hermes config set quick_commands.check_system.command 'bash ~/AI/hermes-ops/scripts/check_system_resources.sh'
```

4. Install the skill into the host Hermes skills directory:

```bash
mkdir -p ~/.hermes/skills/devops/check-system
cp ~/AI/hermes-ops/config/hermes-skills/check-system/SKILL.md ~/.hermes/skills/devops/check-system/SKILL.md
```

5. Restart or reload the Hermes gateway after changing `quick_commands` or installed skills:

```bash
hermes gateway restart
```

6. Send a Telegram DM to the Hermes bot:

```text
/check-system
```

Telegram-native command names usually prefer underscores, so keep this fallback available:

```text
/check_system
```

Natural-language prompts may work through the agent, but they are less deterministic than the quick command:

```text
status da maquina
```

```text
verifica GPU, VRAM, CPU e RAM
```

## Expected Response

Hermes should run this through `quick_commands`:

```bash
bash ~/AI/hermes-ops/scripts/check_system_resources.sh
```

Then it should answer in Telegram with direct command output formatted as short sections and fenced `text` blocks. Telegram does not support HTML `<table>` rendering, and Markdown tables are not rendered as real tables, so monospaced text blocks are the most predictable tabular format:

````text
🧾 Status do Host

```text
Host       llm5060
Hora       2026-06-11 08:32:22 -03
```

⚙️ CPU / RAM / Disco

```text
CPU load   0.69, 1.29, 1.59
CPU cores  12
CPU uso    37.3%
RAM        6.0Gi / 29Gi usados, 24Gi livre
```
````

## Notes

- The script is read-only.
- GPU telemetry currently targets NVIDIA through `nvidia-smi`.
- If `nvidia-smi` is unavailable, the response should still include CPU, RAM, disk, and process data.
- The quick command treats `/check-system` as a request to run the fixed script, not as permission to execute arbitrary shell commands.
- The skill remains useful for natural-language prompts, but the quick command is the reliable Telegram entrypoint.
- HTML and Markdown tables are not used because Telegram does not render them as real tables.
- Fenced `text` blocks are used to preserve spacing in a monospaced font.
