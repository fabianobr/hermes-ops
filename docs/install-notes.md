# Hermes Agent Install Notes

## Date
2026-06-07

## Phase
Phase 3: installation attempt and validation

## Intended Method
- Official Hermes Agent installer from Nous Research
- Host-based install, without Docker
- No `sudo`
- No systemd changes

## Commands Attempted
```bash
command -v git
git --version
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
command -v hermes
hermes --help
```

## Observed Blockers In This Session
- `curl` is not available in the current runtime.
- `wget` is not available in the current runtime.
- The available `git` binary does not support `remote-https`, so it cannot clone from GitHub over HTTPS.
- The current runtime resolves `HOME` through the Codex session environment, which makes host-user installation validation unreliable.

## Result
- Hermes Agent is installed on the real host for user `fabiano`.
- The launcher exists at `/home/fabiano/.local/bin/hermes`.
- Hermes state directory exists at `/home/fabiano/.hermes`.
- This Codex session cannot execute the launcher or read the Hermes home directory because of host permission boundaries in the runtime.

## What This Means
The installation itself appears to have completed on the host, but this session cannot fully validate it because the runtime resolves a different `HOME` and does not have execution/read access to the host user's Hermes files.

## Validation Evidence
The following host paths were confirmed from this session:

```text
/home/fabiano/.local/bin/hermes
/home/fabiano/.hermes
```

## Recommended Next Step
Validate Hermes directly in a normal host shell for user `fabiano`, then continue here with provider configuration:

```bash
export PATH="$HOME/.local/bin:$PATH"
command -v hermes
hermes --version
hermes --help
```

After that, continue with:
- model/provider configuration for LM Studio or Ollama
- Telegram setup
- operational scripts and monitoring

## Phase 4 Continuation Prepared In This Workspace
- Added [scripts/check_local_backends.py](/home/fabiano/AI/hermes-ops/scripts/check_local_backends.py) to validate LM Studio and Ollama without `curl`.
- Added [config/hermes-local-providers.yaml.example](/home/fabiano/AI/hermes-ops/config/hermes-local-providers.yaml.example) as a host-side template for local Hermes provider wiring.
- Added [docs/provider-setup.md](/home/fabiano/AI/hermes-ops/docs/provider-setup.md) as the runbook for provider bring-up.

## Additional Blocker Confirmed In This Session
- This runtime cannot reach `127.0.0.1:1234` or `127.0.0.1:11434`; `python3 scripts/check_local_backends.py` fails here with `Operation not permitted`.

## Updated Practical Next Step
Run the new validation and provider setup steps from a normal host shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
hermes --version
python3 ~/AI/hermes-ops/scripts/check_local_backends.py
```

## Host State Confirmed After Continuation
- `hermes --version` returns `Hermes Agent v0.16.0 (2026.6.5)`.
- A backup of the pre-change host config was saved to [backups/hermes-config.yaml.20260607-ollama-switch.bak](/home/fabiano/AI/hermes-ops/backups/hermes-config.yaml.20260607-ollama-switch.bak).
- `~/.hermes/config.yaml` was switched from `OpenRouter` to `provider: custom` with `base_url: http://127.0.0.1:11434/v1`.
- The current host default model is `qwen3-coder:30b`.
- Auxiliary providers were aligned to `provider: main`.
- `Ollama` responds on `127.0.0.1:11434`.
- `LM Studio` is not listening on `127.0.0.1:1234` and currently returns `Connection refused`.

## Ollama Model Discovery
Host-side inspection found these local models that satisfy the Hermes minimum `64000` context requirement:

- `qwen3-coder:30b` with `262144`
- `deepseek-r1:32b` with `131072`
- `qwen2.5vl:7b` with `128000`
- `qwen3.5:latest` with `262144`

## Remaining Runtime Issue
- A minimal `hermes -z "Reply with exactly OK."` call no longer fails on provider selection, but it does not complete within the current timeout window when forced through large local models.
- That means the configuration problem is mostly resolved; the remaining issue is runtime responsiveness or model load latency on the host.

## Direct Endpoint Confirmation
- A direct host-side `curl` to `http://127.0.0.1:11434/v1/chat/completions` with model `qwen3-coder:30b` returned `OK`.
- Observed wall-clock time was about `40` to `41` seconds for that minimal prompt.
- This confirms the Ollama OpenAI-compatible endpoint is functioning, but response latency is already high before Hermes adds its much larger prompt context.

## Comparative Timing Check
- Additional direct checks with `deepseek-r1:32b`, `qwen2.5vl:7b`, and `qwen3.5:latest` were each capped at `75` seconds and all timed out.
- Based on current measurements, `qwen3-coder:30b` remains the best local Hermes-compatible candidate tested so far, even though it is still slow.

## Retest After Ollama Local Fix
- `hermes -z "Reply with exactly OK."` completed successfully and returned `OK`.
- Fresh direct timings after the local Ollama fix:
  - `qwen3-coder:30b` -> about `26.995s`
  - `qwen3.5:latest` -> about `44.899s`
  - `deepseek-r1:32b` -> about `79.419s`
- `qwen3-coder:30b` remains the preferred local default based on current host measurements.

## Clean Retest From Zero
- Direct endpoint timings were rerun from scratch after the local Ollama issue was fixed:
  - `qwen3-coder:30b` -> `24.198s`
  - `qwen3.5:latest` -> `42.730s`
  - `qwen2.5vl:7b` -> `61.798s`
  - `deepseek-r1:32b` -> `86.476s`
- End-to-end Hermes retest:
  - `qwen3-coder:30b` -> success
  - `qwen2.5vl:7b` -> failed with `no final response was produced`
- After the clean rerun, `qwen3-coder:30b` still remains the correct default choice for Hermes on this host.

## Grounded Workspace Retest
- A real workspace-inspection task was tested in `/home/fabiano/AI/hermes-ops`.
- `qwen3-coder:30b` did not return the requested exact two-line grounded answer when tools were available.
- On a narrower grounded prompt, `qwen3-coder:30b` emitted a raw tool call instead of a final answer.
- With tools forbidden, `qwen3-coder:30b` obeyed formatting but hallucinated the working directory as `/home/user/project`.
- `qwen3.5:latest` failed the same grounded workspace inspection with `no final response was produced`.
- Current status: local Ollama connectivity is fixed, but grounded Hermes reliability with local models still needs work.

## Official Docs Model Pull Attempt
- The next test target was aligned with official Hermes docs recommendations: `gemma4:31b` and `qwen2.5-coder:32b`.
- Neither model was already installed in local Ollama.
- Both `ollama pull` operations were started on the host.
- Observed size for each model was about `19 GB`.
- Observed transfer rates were around `1.8` to `2.1 MB/s`, implying multi-hour downloads.
- Result: these two official-model tests were not completed within this session window and must be resumed after the pulls finish.

## Official Docs Model Test Results
- `qwen2.5-coder:32b`
  - direct endpoint timing: `16.800s`
  - Ollama-reported context window: `32768`
  - Hermes result: rejected before execution because the context window is below Hermes minimum requirements
- `gemma4:31b`
  - direct endpoint timing: `20.596s`
  - Ollama-reported context window: `262144`
  - Hermes minimal oneshot: failed with `cudaMalloc failed: out of memory`
  - Hermes grounded workspace task: failed with the same GPU memory exhaustion class
- Conclusion after official-model testing: `qwen3-coder:30b` still remains the only tested model that is both Hermes-compatible and operational on this host.

## Telegram Polling Preparation
- Inspected the installed Hermes gateway CLI and current config to avoid guessing the Telegram setup flow.
- Confirmed `hermes gateway setup` has no usable non-interactive flags in this version and behaves as an interactive assistant.
- Confirmed `hermes gateway run` is the foreground bring-up path and `hermes gateway status --deep` currently reports that the gateway is not running.
- Confirmed the host `.env` template uses Telegram long polling by default and switches to webhook mode only when `TELEGRAM_WEBHOOK_URL` is set.
- Confirmed the current host config already carries the `telegram` platform toolset and uses `approvals.mode: manual`.
- Added [docs/telegram-setup.md](/home/fabiano/AI/hermes-ops/docs/telegram-setup.md) as the Telegram runbook.
- Added [config/hermes-telegram.env.example](/home/fabiano/AI/hermes-ops/config/hermes-telegram.env.example) as a host-side secret-free example block for `~/.hermes/.env`.
- Added [scripts/check_telegram_gateway.sh](/home/fabiano/AI/hermes-ops/scripts/check_telegram_gateway.sh) for a reproducible non-secret validation pass.
- Ran `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` against the current host state:
  - gateway not running
  - `TELEGRAM_BOT_TOKEN` missing
  - `TELEGRAM_ALLOWED_USERS` not configured
  - `TELEGRAM_HOME_CHANNEL` not configured
  - polling mode active
  - no pairing data yet

## Next Operational Step
The next host-side step is now well-defined:

```bash
export PATH="$HOME/.local/bin:$PATH"
bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh
hermes gateway run -v
```

Then test a Telegram DM and, if manual approval is triggered, manage it with:

```bash
hermes pairing list
hermes pairing approve telegram <CODE>
```

## Telegram Update On 2026-06-09
- Rechecked host-side Telegram status after the user reported success.
- `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` now reports:
  - `TELEGRAM_BOT_TOKEN: configured`
  - `TELEGRAM_ALLOWED_USERS: configured`
  - `TELEGRAM_HOME_CHANNEL: not configured`
  - `Telegram mode: polling`
  - one pending Telegram pairing request for `FabianoBR`
- `hermes gateway status --deep` shows the gateway is currently stopped, so the setup is not yet in an always-available state.
- Diagnosed an operator trap in this Hermes version:
  - `hermes pairing list` shows a hash prefix in the `Code` column, not the real pairing code
  - using that displayed value in `hermes pairing approve telegram <CODE>` fails
- Cleared a temporary pairing lockout after repeated failed approval attempts and saved a backup to [backups/telegram-rate-limits.20260609-pre-unlock.json](/home/fabiano/AI/hermes-ops/backups/telegram-rate-limits.20260609-pre-unlock.json).

## Follow-Up Check On 2026-06-09 05:11 -03
- Rechecked the live host state after the user said the gateway was up and approvals were done.
- Observed result from both `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` and `hermes gateway status --deep`:
  - `Gateway is not running`
- Observed result from `hermes pairing list`:
  - one pending Telegram request for `FabianoBR`
  - no approved users
- Current conclusion: the host state visible from this session still does not reflect a completed Telegram bring-up.

## Clarification On 2026-06-09 05:14 -03
- A direct process inspection with `ps -ef` confirmed the gateway is actually running in another terminal:
  - PID `1391163`
  - command `hermes gateway run -v`
  - terminal `pts/1`
- The live gateway log from that terminal confirms successful Telegram polling connection and a real DM round-trip from `FabianoBR`.
- Revised conclusion: the earlier `hermes gateway status --deep` result was a false negative for this manually started foreground gateway process.
