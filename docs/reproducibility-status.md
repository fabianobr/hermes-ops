# Hermes Ops Reproducibility Status

## Date
2026-06-07

## Purpose
Keep a durable local record of what was discovered, changed, and validated so the Hermes setup can be reproduced later without depending on chat history.

## Current State Summary
- Hermes Agent is installed on the host for user `fabiano`.
- Host launcher path: `/home/fabiano/.local/bin/hermes`
- Host state directory: `/home/fabiano/.hermes`
- Hermes version validated on host: `0.16.0 (2026.6.5)`
- Hermes host config was switched from `OpenRouter` to local `Ollama`.
- Current host default model: `qwen3-coder:30b`
- `LM Studio` is not currently listening on `127.0.0.1:1234`.
- `Ollama` is reachable on `127.0.0.1:11434`.

## Host Changes Already Applied
- Backed up the previous host config to [backups/hermes-config.yaml.20260607-ollama-switch.bak](/home/fabiano/AI/hermes-ops/backups/hermes-config.yaml.20260607-ollama-switch.bak).
- Updated `~/.hermes/config.yaml` on the host with:
  - `model.provider: custom`
  - `model.base_url: http://127.0.0.1:11434/v1`
  - `model.default: qwen3-coder:30b`
  - auxiliary providers set to `main`

## Reproduction Files In This Repository
- Install and continuity notes: [docs/install-notes.md](/home/fabiano/AI/hermes-ops/docs/install-notes.md)
- Baseline model decision: [docs/baseline-decision.md](/home/fabiano/AI/hermes-ops/docs/baseline-decision.md)
- Provider bring-up runbook: [docs/provider-setup.md](/home/fabiano/AI/hermes-ops/docs/provider-setup.md)
- Architecture and security boundaries: [docs/ARCHITECTURE.md](/home/fabiano/AI/hermes-ops/docs/ARCHITECTURE.md)
- Local provider template: [config/hermes-local-providers.yaml.example](/home/fabiano/AI/hermes-ops/config/hermes-local-providers.yaml.example)
- Backend validation script: [scripts/check_local_backends.py](/home/fabiano/AI/hermes-ops/scripts/check_local_backends.py)
- Ollama model inventory script: [scripts/list_ollama_models.py](/home/fabiano/AI/hermes-ops/scripts/list_ollama_models.py)
- Baseline validation script: [scripts/validate_hermes_baseline.sh](/home/fabiano/AI/hermes-ops/scripts/validate_hermes_baseline.sh)
- Telegram gateway check script: [scripts/check_telegram_gateway.sh](/home/fabiano/AI/hermes-ops/scripts/check_telegram_gateway.sh)
- Telegram setup runbook: [docs/telegram-setup.md](/home/fabiano/AI/hermes-ops/docs/telegram-setup.md)
- Telegram env template: [config/hermes-telegram.env.example](/home/fabiano/AI/hermes-ops/config/hermes-telegram.env.example)
- Environment inventory log: [logs/inventory.txt](/home/fabiano/AI/hermes-ops/logs/inventory.txt)
- Prerequisite log: [logs/prerequisites.txt](/home/fabiano/AI/hermes-ops/logs/prerequisites.txt)

## Verified Commands
Run these from a normal host shell as user `fabiano`:

```bash
export PATH="$HOME/.local/bin:$PATH"
hermes --version
python3 ~/AI/hermes-ops/scripts/check_local_backends.py
python3 ~/AI/hermes-ops/scripts/list_ollama_models.py
hermes config show
hermes dump
```

## Verified Local Ollama Models
The following host models were confirmed through Ollama metadata and meet the Hermes minimum context requirement of `64000`:

- `qwen3-coder:30b` with `262144`
- `deepseek-r1:32b` with `131072`
- `qwen2.5vl:7b` with `128000`
- `qwen3.5:latest` with `262144`

## Known Remaining Issue
- A minimal `hermes -z "Reply with exactly OK."` test no longer fails on provider selection, but it did not complete within the active timeout window for the larger local models tested.
- The remaining problem is runtime responsiveness or model load latency, not missing provider configuration.

## Direct Ollama Timing Evidence
On 2026-06-07, the host returned a successful direct OpenAI-compatible chat completion for `qwen3-coder:30b`:

```bash
time curl -sS http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-coder:30b",
    "messages": [
      {
        "role": "user",
        "content": "Reply with exactly OK."
      }
    ]
  }'
```

Observed result:

- response content: `OK`
- wall-clock time: about `40` to `41` seconds

Interpretation:

- the Ollama endpoint itself is working correctly
- the remaining issue is latency, not basic connectivity
- Hermes is expected to be slower than this direct test because it sends a much larger prompt, including system instructions and tool schemas

## Comparative Model Timing
Additional host-side direct timing checks were attempted with the same minimal prompt and a hard timeout of `75` seconds:

- `deepseek-r1:32b` -> timed out at `75s`
- `qwen2.5vl:7b` -> timed out at `75s`
- `qwen3.5:latest` -> timed out at `75s`

Current practical conclusion:

- `qwen3-coder:30b` is the fastest measured Hermes-compatible local candidate so far on this host
- the other tested high-context candidates were slower than `qwen3-coder:30b` for this direct endpoint check

## Comparative Model Timing After Local Ollama Fix
After the local Ollama issue was corrected, the same direct endpoint test was repeated:

- `qwen3-coder:30b` -> success in about `26.995s`, returned clean `OK`
- `qwen3.5:latest` -> success in about `44.899s`, returned `OK` plus unnecessary reasoning
- `deepseek-r1:32b` -> success in about `79.419s`, returned `OK` plus unnecessary reasoning

Updated practical conclusion:

- `qwen3-coder:30b` is clearly the best current local default for Hermes on this host
- `qwen3.5:latest` is slower and leaks reasoning in the direct response
- `deepseek-r1:32b` is significantly slower for this workload

## Clean Retest From Zero
A full retest was run after discarding earlier conclusions that were polluted by the local Ollama issue.

Direct `Ollama` endpoint timings with the same minimal prompt:

- `qwen3-coder:30b` -> `24.198s`, returned clean `OK`
- `qwen3.5:latest` -> `42.730s`, returned `OK` plus reasoning
- `qwen2.5vl:7b` -> `61.798s`, returned clean `OK`
- `deepseek-r1:32b` -> `86.476s`, returned `OK` plus reasoning

Hermes end-to-end retest:

- `hermes --provider custom -m qwen3-coder:30b -z "Reply with exactly OK."` -> success, returned `OK`
- `hermes --provider custom -m qwen2.5vl:7b -z "Reply with exactly OK."` -> failed with `no final response was produced`

Current selection rule after the clean retest:

- prefer models with at least `64000` context
- among those, prefer the fastest direct endpoint result
- require a successful Hermes end-to-end result, not just a successful raw Ollama response

## Grounded Workspace Validation
After selecting `qwen3-coder:30b` as the best candidate, Hermes was tested on a small grounded repository task in `/home/fabiano/AI/hermes-ops`.

Expected local truth:

- current working directory: `/home/fabiano/AI/hermes-ops`
- top-level entries: `.agents`, `.codex`, `.git`, `AGENTS.md`, `backups`, `config`, `docs`, `logs`, `scripts`

Observed Hermes behavior:

- `qwen3-coder:30b` with tools allowed did not produce the requested two-line answer; instead it returned a prose summary and asked what to do next
- `qwen3-coder:30b` with an even narrower workspace prompt emitted a raw tool call for `pwd` instead of a final answer
- `qwen3-coder:30b` with tools explicitly forbidden obeyed format for a minimal prompt but hallucinated the path as `/home/user/project`
- `qwen3-coder:30b` with tools explicitly forbidden did succeed on the trivial prompt `Reply with exactly OK.`
- `qwen3.5:latest` failed the same grounded workspace inspection with `no final response was produced`

Operational conclusion:

- the local setup is now good enough for basic inference
- it is not yet reliable for grounded repository inspection tasks through Hermes oneshot mode
- the main remaining issue is agent reliability with local models, not provider connectivity

## Official Recommended Models Pending Test
The official docs models selected for retest were:

- `gemma4:31b`
- `qwen2.5-coder:32b`

Host status on 2026-06-07:

- neither model was present in the local Ollama inventory
- `ollama pull gemma4:31b` was started
- `ollama pull qwen2.5-coder:32b` was started
- both downloads are roughly `19 GB`
- observed transfer rates were about `1.8` to `2.1 MB/s`
- projected completion time was roughly `2h40m` to `3h+` per model

Practical implication:

- the official recommended-model benchmark and Hermes validation did not complete in this session
- continuation should resume by checking whether the pulls finished, then rerunning the same direct endpoint and Hermes tests used earlier

## Official Docs Model Results
After the pulls completed, both official docs models were tested.

`qwen2.5-coder:32b`

- direct `Ollama` chat-completions test succeeded in about `16.800s`
- local `Ollama` metadata reports `context_length=32768`
- Hermes oneshot rejected it immediately because Hermes requires at least `64000`

Practical result:

- fast on the raw endpoint
- not a valid Hermes candidate on this host as currently served by Ollama

`gemma4:31b`

- local `Ollama` metadata reports `context_length=262144`
- direct `Ollama` chat-completions test succeeded in about `20.596s`
- direct response included `OK` plus leaked reasoning
- Hermes oneshot minimal test failed with:
  - `HTTP 500`
  - `cudaMalloc failed: out of memory`
- grounded Hermes workspace test failed with the same GPU memory exhaustion class

Practical result:

- valid context window for Hermes
- good direct latency
- currently not viable for Hermes on this host because the actual agent prompt/tool load pushes GPU memory over the limit

Updated decision after testing official docs models:

- `qwen3-coder:30b` remains the best working Hermes candidate on this host
- `qwen2.5-coder:32b` is disqualified by context length
- `gemma4:31b` is disqualified by runtime GPU memory exhaustion under Hermes

## Telegram Polling Preparation
The next project phase was prepared without storing secrets in the repository.

Observed host state on 2026-06-08:

- `hermes gateway status --deep` reports that the gateway is not running
- current Hermes config already contains the `telegram` platform toolset
- host `.env` comments confirm that long polling is the default
- webhook mode is only activated when `TELEGRAM_WEBHOOK_URL` is set
- current host config uses `approvals.mode: manual`, so operator approval flow must be expected during bring-up
- `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` currently reports:
  - `TELEGRAM_BOT_TOKEN: missing`
  - `TELEGRAM_ALLOWED_USERS: not configured`
  - `TELEGRAM_HOME_CHANNEL: not configured`
  - `Telegram mode: polling`
  - `No pairing data found`

Repository artifacts added for this phase:

- [docs/telegram-setup.md](/home/fabiano/AI/hermes-ops/docs/telegram-setup.md)
- [config/hermes-telegram.env.example](/home/fabiano/AI/hermes-ops/config/hermes-telegram.env.example)
- [scripts/check_telegram_gateway.sh](/home/fabiano/AI/hermes-ops/scripts/check_telegram_gateway.sh)

Practical bring-up sequence now documented:

1. keep `qwen3-coder:30b` as the baseline model
2. add Telegram secrets only in `~/.hermes/.env`
3. validate with `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh`
4. start the gateway with `hermes gateway run -v`
5. test DM access first, then handle any pending authorization with `hermes pairing`

## Telegram Bring-Up Update On 2026-06-09
Host validation after the user confirmed Telegram setup:

- `TELEGRAM_BOT_TOKEN` is now configured in `~/.hermes/.env`
- `TELEGRAM_ALLOWED_USERS` is now configured in `~/.hermes/.env`
- polling mode remains active
- `TELEGRAM_HOME_CHANNEL` is still unset
- `hermes pairing list` shows one pending Telegram request for user `274873525` / `FabianoBR`
- `hermes gateway status --deep` currently reports the gateway is not running

Important operator finding:

- `hermes pairing list` does not expose the real approval code
- the `Code` column is only the first 8 hex characters of the stored hash
- attempting `hermes pairing approve telegram <value shown in list>` fails even when the pending request is valid
- manual approval must use the actual pairing code shown to the user in Telegram

Follow-up verification on 2026-06-09 at about `05:11 -03`:

- `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` still reports `Gateway is not running`
- `hermes gateway status --deep` still reports `Gateway is not running`
- `hermes pairing list` still shows:
  - one pending Telegram request for `274873525` / `FabianoBR`
  - no approved users

Current implication:

- Telegram secret wiring is in place
- the gateway is not currently active in the host session visible here
- the pairing flow is not yet complete in the host state visible here

Second follow-up verification on 2026-06-09 at about `05:14 -03` clarified the discrepancy:

- `ps -ef` shows a live foreground gateway process:
  - PID `1391163`
  - command: `/home/fabiano/.hermes/hermes-agent/venv/bin/python3 /home/fabiano/.hermes/hermes-agent/venv/bin/hermes gateway run -v`
  - terminal: `pts/1`
- user-provided live gateway log confirms:
  - Telegram connected in polling mode
  - gateway running with `1` platform
  - inbound DM processed from `FabianoBR`
  - response delivered in about `10.9s`

Operational conclusion:

- the Telegram gateway is in fact running in a separate foreground terminal
- `hermes gateway status --deep` returned a false negative for this manual foreground run during this session
- for this environment, process inspection and live gateway logs are more reliable than `gateway status` when the gateway was started manually in another terminal

Safety record:

- backup saved before lockout cleanup: [backups/telegram-rate-limits.20260609-pre-unlock.json](/home/fabiano/AI/hermes-ops/backups/telegram-rate-limits.20260609-pre-unlock.json)
- a temporary Telegram pairing lockout entry was cleared from `~/.hermes/pairing/_rate_limits.json` to continue diagnosis

## Documentation Rule For Next Steps
Before and after each future operational change in this project:
- record the intended change in `docs/install-notes.md`
- store any reusable procedure in `docs/`
- store scripts in `scripts/`
- store config templates in `config/`
- store backups with timestamps in `backups/`

This file is the index for reconstruction when chat context is unavailable.
