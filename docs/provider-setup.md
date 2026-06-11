# Hermes Local Provider Setup

## Date
2026-06-07

## Purpose
Continue the project after host installation by wiring Hermes to local model backends and validating the endpoints without relying on `curl`.

## Host Validation
Run these commands in a normal shell as user `<operator>`:

```bash
export PATH="$HOME/.local/bin:$PATH"
command -v hermes
hermes --version
python3 ~/AI/hermes-ops/scripts/check_local_backends.py
python3 ~/AI/hermes-ops/scripts/list_ollama_models.py
```

`check_local_backends.py` expects:

- LM Studio at `http://127.0.0.1:1234/v1/models`
- Ollama at `http://127.0.0.1:11434/api/tags`

Current known host state from validation:

- `Ollama` is reachable on `127.0.0.1:11434`
- `LM Studio` is not listening on `127.0.0.1:1234`
- `~/.hermes/config.yaml` is still pointed at `OpenRouter`

If one of the required local backends fails, fix that local service before changing Hermes config.

## Config Strategy
For the current host state, use the simplest supported path from the official Hermes docs: set the main model to `provider: custom` and point `model.base_url` at Ollama.

Copy the relevant structure from [config/hermes-local-providers.yaml.example](../config/hermes-local-providers.yaml.example) and replace `qwen3-coder:30b` if you want a different Ollama model.

Use [scripts/list_ollama_models.py](../scripts/list_ollama_models.py) to identify a model whose reported context window is at least `64000`, which Hermes requires.

Current suitable local candidates discovered on the host:

- `qwen3-coder:30b` with `262144`
- `deepseek-r1:32b` with `131072`
- `qwen2.5vl:7b` with `128000`
- `qwen3.5:latest` with `262144`

Examples:

- Ollama model names often look like `qwen3:8b` or `llama3.1:8b`
- LM Studio model names often look like `qwen/qwen3-32b`

## Recommended Bring-Up Order
1. Validate Hermes is callable on the host.
2. Validate Ollama with `python3 ~/AI/hermes-ops/scripts/check_local_backends.py`.
3. Use `python3 ~/AI/hermes-ops/scripts/list_ollama_models.py` to choose an Ollama model with at least `64000` context.
4. Switch the main Hermes model from `OpenRouter` to `provider: custom` with Ollama, either through `hermes model` or by editing `~/.hermes/config.yaml`.
5. Keep auxiliary tasks on `provider: main` first, so they follow the same local endpoint.
6. Only after model routing works, continue to Telegram and any always-on runtime.

## Known Caution
As of 2026-05-07, there is an open Hermes Agent GitHub issue reporting that `provider: ollama` is not recognized for auxiliary tasks and can fall back silently. For now, prefer `provider: custom` on the main model plus `provider: main` for auxiliary tasks.

Sources:

- Hermes configuration docs: https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
- Hermes providers docs: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md
- Open issue opened 2026-05-07: https://github.com/NousResearch/hermes-agent/issues/21352
