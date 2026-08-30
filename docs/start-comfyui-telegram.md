# Start ComfyUI Through Telegram

## Purpose

Let the operator bring the local ComfyUI container up from Telegram without granting Hermes arbitrary Docker or shell execution.

## Plan

1. Keep the start logic in [scripts/start_comfyui.sh](../scripts/start_comfyui.sh).
2. Keep the Hermes skill source in [config/hermes-skills/start-comfyui/SKILL.md](../config/hermes-skills/start-comfyui/SKILL.md).
3. Configure `/start-comfyui` as a Hermes quick command. This is the operational path because quick commands bypass the LLM and return command output directly:

```yaml
quick_commands:
  start-comfyui:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/start_comfyui.sh
  start_comfyui:
    type: exec
    command: bash ~/AI/hermes-ops/scripts/start_comfyui.sh
```

Equivalent CLI setup:

```bash
hermes config set quick_commands.start-comfyui.type exec
hermes config set quick_commands.start-comfyui.command 'bash ~/AI/hermes-ops/scripts/start_comfyui.sh'
hermes config set quick_commands.start_comfyui.type exec
hermes config set quick_commands.start_comfyui.command 'bash ~/AI/hermes-ops/scripts/start_comfyui.sh'
```

4. Install the canonical skill file into the host Hermes skills directory:

```bash
mkdir -p ~/.hermes/skills/devops/start-comfyui
install -m 600 ~/AI/hermes-ops/config/hermes-skills/start-comfyui/SKILL.md ~/.hermes/skills/devops/start-comfyui/SKILL.md
```

5. Install the router plugin so the command appears in the Telegram menu and natural phrasing is routed deterministically:

```bash
mkdir -p ~/.hermes/plugins/start-comfyui-router
install -m 600 ~/AI/hermes-ops/config/hermes-plugins/start-comfyui-router/plugin.yaml ~/.hermes/plugins/start-comfyui-router/plugin.yaml
install -m 600 ~/AI/hermes-ops/config/hermes-plugins/start-comfyui-router/__init__.py ~/.hermes/plugins/start-comfyui-router/__init__.py
```

Copying the files is not enough: a user plugin is installed as `not enabled`.
Enable it explicitly, and decline the tool-override prompt. This plugin only
registers a hook and a menu command, so it must not be allowed to replace
built-in tools such as `shell_exec`:

```bash
hermes plugins enable start-comfyui-router
hermes plugins list | rg -n 'start-comfyui-router'
```

6. Restart or reload the Hermes gateway after changing `quick_commands`, installed skills, or plugins:

```bash
hermes gateway restart
```

7. Send a Telegram DM to the Hermes bot:

```text
/start-comfyui
```

O menu nativo do Telegram aceita apenas letras minúsculas, números e `_` nos
nomes dos comandos, então ele publica a forma:

```text
/start_comfyui
```

O plugin `start-comfyui-router` registra o nome canônico `start-comfyui` para
garantir a entrada no menu. Na execução, o quick command configurado acima
mantém precedência.

Frases naturais também são roteadas pelo plugin, sem passar pelo LLM:

```text
sobe o comfyui
```

```text
Inicie o ComfyUI, por favor.
```

## Expected Response

Hermes should run this through `quick_commands`:

```bash
bash ~/AI/hermes-ops/scripts/start_comfyui.sh
```

Then it should answer in Telegram with direct command output in fenced `text`
blocks, which are the most predictable tabular format there:

````text
🎨 Iniciar ComfyUI

```text
Host       llm5060
Hora       2026-08-30 15:58:10 -03
Container  comfyui
```

🎮 VRAM Antes do Start

```text
0: NVIDIA GeForce RTX 5060 Ti
VRAM       1154 / 16311 MiB
Livre      15157 MiB
```

🚀 Start

```text
Acao       docker start comfyui
Resultado  comando aceito
```

⏳ Aguardando Resposta

```text
Limite     120s
Pronto     6s
```

📡 Estado Final

```text
Status     running
Saude      healthy
Endereco   http://127.0.0.1:8188
```

✅ ComfyUI Disponivel

```text
Endereco   http://127.0.0.1:8188
```
````

## Behavior

- The script is idempotent. If the container is already running and answering, it reports that and starts nothing.
- A container that is `running` but not answering is never restarted. The script waits for it and, if it stays that way, reports a failure instead of handing the operator a URL the service cannot back.
- An existing stopped container is started with `docker start`.
- A missing container falls back to `docker compose up -d --no-build` against `~/homelab-ai/infra/docker/docker-compose.yml` with the `media-pipeline` profile. `--no-build` keeps image builds an explicit operator decision instead of a long unattended build triggered from Telegram.
- Readiness is `healthy` from Docker **or** a direct HTTP probe of `/system_stats`. The compose healthcheck only runs every 30s after a 60s start period, so polling the service directly is what keeps a normal cold start from being reported as a timeout.
- Every Docker call is wrapped in `timeout`. A wedged daemon can accept the socket connection and never answer, which would otherwise hang the Telegram quick command with no output at all.
- On failure it prints the final state plus the last 20 log lines and exits non-zero. The state it prints is the one the exit decision used, so the report cannot contradict itself.
- It accepts no arguments, and rejects them with exit code 2.

## Configuration

All overrides are environment variables, so the Telegram command itself stays fixed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `COMFYUI_CONTAINER` | `comfyui` | Container name to start and inspect. |
| `COMFYUI_COMPOSE_FILE` | `~/homelab-ai/infra/docker/docker-compose.yml` | Compose file used only when the container does not exist. |
| `COMFYUI_COMPOSE_PROFILE` | `media-pipeline` | Compose profile that contains the service. |
| `COMFYUI_COMPOSE_SERVICE` | `comfyui` | Compose service name. |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | Address probed for readiness and reported back to the operator. |
| `COMFYUI_PROBE_PATH` | `/system_stats` | Path appended to `COMFYUI_URL` for the readiness probe. |
| `COMFYUI_START_TIMEOUT` | `120` | Seconds to wait for the service to answer. |
| `COMFYUI_POLL_INTERVAL` | `3` | Seconds between readiness polls. |

## Notes

- Starting the container is the only write action. The script never stops, removes, rebuilds, or prunes anything.
- The Hermes runtime user needs access to the Docker socket. When the daemon is unreachable the script says so and exits non-zero instead of failing silently.
- The GPU is shared with Ollama on this host, and the ComfyUI service is capped at 27g of memory with a 29g `memswap_limit` in Compose. The script prints free VRAM before starting and warns below 4096 MiB so the operator can free memory first.
- The container previously died with exit code 137 under heavy workflows, so a start that never reaches `healthy` returns the recent log lines rather than a bare failure.
- Voice messages are not routed to this command. Unlike the read-only check-system report, this one changes host state, so a transcription error must not be enough to start a GPU container.
- Requests to stop, restart, or rebuild ComfyUI are deliberately not routed. They reach the agent, which requires explicit authorization.
- Hermes also ships a bundled `comfyui` skill under `creative`, which drives ComfyUI through `comfy-cli`. Because a rewrite bypasses the LLM entirely, the router has to stay out of that skill's territory: it ignores any message mentioning workflows, nodes, prompts, images, video, or generation, and it only accepts generic verbs such as "rode" when the message also names the skill, the command, or the container. "Quero rodar um workflow no ComfyUI" therefore reaches the agent intact.
- Every router guard fails towards the agent, never towards the container. Negations (`não inicie o comfyui`), questions, stop/restart phrasings, and messages naming another service are all left for the LLM, which can still start ComfyUI after asking.
- The gateway loads plugins, skills, and `quick_commands` at startup, so every change above needs a `systemctl --user restart hermes-gateway` (or `hermes gateway restart`) to take effect.
