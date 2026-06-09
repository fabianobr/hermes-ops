# Hermes Baseline Decision

## Date
2026-06-07

## Selected Baseline
`qwen3-coder:30b`

## Why This Is The Current Baseline
- It satisfies the Hermes minimum context requirement on this host as served by Ollama.
- It completes `hermes -z` successfully.
- It has better direct latency than the other tested Hermes-compatible local candidates.
- The official docs candidates were tested and did not displace it:
  - `qwen2.5-coder:32b` is served with only `32768` context on this host, so Hermes rejects it.
  - `gemma4:31b` has enough context and decent direct latency, but Hermes fails with GPU memory exhaustion on this host.

## Host Configuration Baseline
- `model.provider: custom`
- `model.base_url: http://127.0.0.1:11434/v1`
- `model.default: qwen3-coder:30b`
- auxiliary providers: `main`

## Revalidation Command
Run this in a normal host shell:

```bash
bash ~/AI/hermes-ops/scripts/validate_hermes_baseline.sh
```

## Known Limitation
This baseline is the best tested working choice for Hermes on this host, but it is still not fully reliable for grounded repository inspection tasks in oneshot mode.
