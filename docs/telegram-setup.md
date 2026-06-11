# Hermes Telegram Setup

## Purpose
Bring Hermes up on Telegram in polling mode first, with host-side changes that are reproducible without storing secrets in this repository.

## Current Decision
- Keep `qwen3-coder:30b` as the Hermes baseline model.
- Use Telegram in long polling mode first.
- Run the gateway as a user-level systemd service after foreground validation succeeds.
- Keep Telegram secrets only in `~/.hermes/.env`.

## Current Host Status
As of 2026-06-09:

- `hermes-gateway.service` is installed as a user systemd service
- the service is enabled and running
- systemd linger is enabled, so the user service survives logout
- the repository architecture already targets Telegram polling first
- Hermes current host config already includes the `telegram` platform toolset
- the host `.env` template shows Telegram polling is the default unless `TELEGRAM_WEBHOOK_URL` is set

## Required Inputs
- Telegram bot token from `@BotFather`
- your Telegram numeric user ID, typically from `@userinfobot`
- optional target group chat ID and topic/thread ID if you want group use or cron delivery

## Files In This Repository
- template env block: [config/hermes-telegram.env.example](../config/hermes-telegram.env.example)
- gateway check script: [scripts/check_telegram_gateway.sh](../scripts/check_telegram_gateway.sh)
- continuity notes: [docs/install-notes.md](install-notes.md)

## Host-Side Bring-Up
1. Validate the baseline model first:

```bash
export PATH="$HOME/.local/bin:$PATH"
bash ~/AI/hermes-ops/scripts/validate_hermes_baseline.sh
```

2. Copy the example values you actually need from [config/hermes-telegram.env.example](../config/hermes-telegram.env.example) into `~/.hermes/.env`.

Minimum safe first pass:

```dotenv
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USERS=replace-with-telegram-user-id
```

3. Validate the non-secret gateway state:

```bash
bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh
```

4. Start the gateway in the foreground for the first manual test:

```bash
hermes gateway run -v
```

5. Message the bot from Telegram.

For direct-message bring-up, keep the first pass simple:
- start in DM, not in a group
- keep `TELEGRAM_ALLOWED_USERS` set
- leave webhook variables unset so polling remains active

## User Service Operation
After foreground validation, install and start the user service:

```bash
hermes gateway install --force
hermes gateway status --deep
```

The current service unit is:

```text
~/.config/systemd/user/hermes-gateway.service
```

Useful service commands:

```bash
hermes gateway status --deep
hermes gateway start
hermes gateway stop
hermes gateway restart
journalctl --user -u hermes-gateway -f
```

In restricted Codex sessions, the user systemd bus may not be reachable. When that happens, validate from a normal host shell or use process inspection:

```bash
ps -ef | rg 'hermes_cli.main gateway run|hermes gateway run'
```

## Authorization And Pairing
The current host config uses `approvals.mode: manual`. In practice, that means new gateway users should be treated as requiring operator approval before they are trusted.

Operator commands:

```bash
hermes pairing list
hermes pairing approve telegram <CODE>
hermes pairing revoke telegram <USER_ID>
hermes pairing clear-pending
```

Practical flow:
- start the gateway
- send the first message to the bot from Telegram
- inspect pending or approved users with `hermes pairing list`
- approve with the real pairing code shown to the user in Telegram, not with the `Code` column from `hermes pairing list`

Important caveat in this Hermes version:
- `hermes pairing list` shows only the first 8 hex characters of the stored hash so operators can distinguish pending entries
- that displayed value is not the real pairing code and cannot be fed back into `hermes pairing approve`
- if you need to approve manually, use the code the bot actually presented in Telegram

## Polling Versus Webhook
Polling is the default path in this Hermes version. Webhook mode is only enabled when `TELEGRAM_WEBHOOK_URL` is set.

For this project, polling remains the baseline because:
- no public inbound endpoint is required
- it matches the architecture already recorded in [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- it keeps the first operational surface smaller

## First Stable Target
The Telegram phase is considered stable when all of these are true:
- `bash ~/AI/hermes-ops/scripts/check_telegram_gateway.sh` shows token configured and no accidental webhook mode
- `hermes gateway run -v` starts without adapter errors
- the operator can send a DM to the bot and receive a Hermes response
- if manual approval is triggered, the operator can approve with the real Telegram pairing code and the user appears in the approved list

The current deployment has passed the foreground smoke test and has been promoted to a user systemd service.
