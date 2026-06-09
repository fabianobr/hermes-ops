# Hermes Ops Architecture

## Objective
Deploy Hermes Agent as an operator for the local AI stack, with direct access to diagnostics and automation, while reducing blast radius through least-privilege execution and localhost-only integrations.

## Proposed Topology
- Hermes Agent runs on the host, under a dedicated non-privileged user.
- Operational workspace remains in `~/AI/hermes-ops/`.
- Hermes state and secrets stay under `~/.hermes/`.
- Local model backends remain separate services:
  - `LM Studio` on `127.0.0.1:1234`
  - `Ollama` on `127.0.0.1:11434`
- Telegram is connected through the Hermes gateway in polling mode first, avoiding inbound public exposure.

## Security Boundaries
- No `sudo` for Hermes runtime.
- No external bind for dashboard or local model APIs.
- No webhook exposure in the initial setup.
- Secrets stored only in `.env`/Hermes auth files, never in repository docs.
- Future automation should stay inside `~/AI/hermes-ops/scripts/` and default to read-only or dry-run behavior.

## Renderable Diagram
```mermaid
flowchart LR
    TG[Telegram User] -->|polling via gateway| HG[Hermes Gateway]

    subgraph HOST[Ubuntu Host]
        subgraph HU[Dedicated hermes user]
            HG
            HC[Hermes CLI / Agent Runtime]
            HS[~/.hermes<br/>config.yaml<br/>auth.json<br/>.env]
            HW[~/AI/hermes-ops<br/>scripts logs docs config backups]
        end

        subgraph LOCAL[Local AI Services]
            LM[LM Studio<br/>127.0.0.1:1234]
            OL[Ollama<br/>127.0.0.1:11434]
            CF[ComfyUI<br/>optional local service]
        end

        subgraph SYS[Host Resources]
            GPU[GPU / VRAM]
            MEM[RAM / Swap]
            DSK[SSD / Filesystems]
            SVC[Docker / Ollama / system services]
        end
    end

    HC <-->|read/write config, sessions, tokens| HS
    HC <-->|run bounded ops scripts| HW
    HC <-->|local API| LM
    HC <-->|local API| OL
    HC -. optional checks .-> CF
    HC -->|diagnostics / monitoring| GPU
    HC -->|diagnostics / monitoring| MEM
    HC -->|diagnostics / monitoring| DSK
    HC -->|service status checks| SVC
```

## Accepted Risks
- Running Hermes on the host gives it direct access to the dedicated user context.
- A compromised Hermes session or leaked token could affect files and services reachable by that user.
- Telegram adds a remote control surface, even when using polling.

## Initial Mitigations
- Use a dedicated runtime user instead of the main personal account.
- Restrict Hermes working directories to the ops workspace where possible.
- Keep model servers on localhost only.
- Prefer polling over webhook for Telegram.
- Delay any systemd installation or auto-start until the manual workflow is stable.
- Introduce terminal isolation later if needed through Hermes terminal backend configuration such as Docker or SSH.

## Next Hardening Steps
1. Create the dedicated `hermes` user and isolate file ownership.
2. Set Hermes terminal working directory to the ops workspace.
3. Validate Telegram in polling mode before considering any always-on service.
4. Review whether shell execution should later move to a Docker or SSH backend.
