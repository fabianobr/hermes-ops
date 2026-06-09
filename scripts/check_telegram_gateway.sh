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
  echo "Gateway is not active right now."
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
hermes pairing list
