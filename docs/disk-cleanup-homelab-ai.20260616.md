# Disk Cleanup Record — Homelab AI

## Scope

Historical record of the 2026-06-16 investigation on host `llm5060`. Treat every size, model name, and cleanup candidate below as stale until remeasured. This document is not an executable cleanup procedure.

## Measured Usage

The root filesystem was at 88% usage (601 GiB of 719 GiB). The largest observed locations were:

| Path | Size | Observation |
| --- | ---: | --- |
| `~/AI/ComfyUI/models/` | 279 GiB | Mostly LTX Video variants |
| `~/AI/ollama/models/blobs/` | 135 GiB | 18 Ollama models at the time |
| `~/.lmstudio/` | 14 GiB | LM Studio was disabled |
| `~/Downloads/` | 8.5 GiB | Mixed downloads |
| `~/.config/google-chrome` | 1.4 GiB | Browser profile data |

## Recorded Actions

- Removed approximately 6.1 GiB of disabled LM Studio model data.
- Removed approximately 130 GiB of selected ComfyUI checkpoints after checking that they were obsolete or duplicated.
- Identified old Ollama models as possible cleanup candidates, but the inventory must be regenerated before any removal.
- Identified redundant Snap installations for later verification against the Docker-based deployment.

## Swap Observation

The host had a 4 GiB `/swap.img` plus a 32 GiB `/swapfile`. A reduction was discussed, but swap changes require a separate maintenance procedure with current memory-pressure checks, an `/etc/fstab` review, interactive privilege escalation, and post-change verification.

## Revalidation Rule

Before proposing remediation, collect a fresh disk inventory, confirm that each candidate is unused, list exact paths and expected savings, and obtain explicit authorization. Never reuse the historical deletion candidates as a current removal plan.
