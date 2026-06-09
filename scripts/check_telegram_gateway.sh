#!/usr/bin/env bash
# Verification:
#   bash scripts/check_telegram_gateway.sh

set -eu

export PATH="$HOME/.local/bin:$PATH"

ENV_FILE="${HOME}/.hermes/.env"

has_nonempty_env_key() {
  key="$1"
  if [ ! -f "$ENV_FILE" ]; then
    return 1
  fi
  rg -q "^${key}=.+$" "$ENV_FILE"
}

find_gateway_processes() {
  ps -ef | rg '[h]ermes gateway run|[g]ateway run -v|[h]ermes_cli\.main gateway run' || true
}

echo "== Telegram gateway check =="
date
echo

echo "== Hermes version =="
hermes --version
echo

echo "== Gateway runtime status =="
if hermes gateway status --deep; then
  :
else
  echo
  echo "Hermes gateway status did not report an active gateway."
fi
echo

echo "== Gateway process check =="
gateway_processes="$(find_gateway_processes)"
if [ -n "$gateway_processes" ]; then
  echo "$gateway_processes"
else
  echo "No gateway process found by ps."
fi
echo

echo "== Telegram env status =="
if [ -f "$ENV_FILE" ]; then
  echo "Env file: $ENV_FILE"
else
  echo "Env file missing: $ENV_FILE"
fi

if has_nonempty_env_key "TELEGRAM_BOT_TOKEN"; then
  echo "TELEGRAM_BOT_TOKEN: configured"
else
  echo "TELEGRAM_BOT_TOKEN: missing"
fi

if has_nonempty_env_key "TELEGRAM_ALLOWED_USERS"; then
  echo "TELEGRAM_ALLOWED_USERS: configured"
else
  echo "TELEGRAM_ALLOWED_USERS: not configured"
fi

if has_nonempty_env_key "TELEGRAM_HOME_CHANNEL"; then
  echo "TELEGRAM_HOME_CHANNEL: configured"
else
  echo "TELEGRAM_HOME_CHANNEL: not configured"
fi

if has_nonempty_env_key "TELEGRAM_WEBHOOK_URL"; then
  echo "Telegram mode: webhook"
else
  echo "Telegram mode: polling"
fi
echo

echo "== Pairing state =="
if hermes pairing list; then
  :
else
  echo
  echo "Could not read pairing state through Hermes CLI."
  echo "In restricted sessions this can happen because 'hermes pairing list' may prune expired entries and write to ~/.hermes/pairing."
fi
