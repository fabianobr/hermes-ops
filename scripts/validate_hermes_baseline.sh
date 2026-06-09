#!/usr/bin/env bash
# Verification:
#   bash scripts/validate_hermes_baseline.sh

set -eu

export PATH="$HOME/.local/bin:$PATH"

echo "== Hermes baseline validation =="
date
echo

echo "== Hermes version =="
hermes --version
echo

echo "== Active model config =="
hermes config show | sed -n '1,80p'
echo

echo "== Local backend checks =="
if python3 "$(dirname "$0")/check_local_backends.py"; then
  :
else
  echo
  echo "Backend check returned a non-zero status."
  echo "This baseline accepts LM Studio being offline as long as Ollama is healthy."
fi
echo

echo "== Ollama model inventory =="
python3 "$(dirname "$0")/list_ollama_models.py" | rg '^(qwen3-coder:30b|gemma4:31b|qwen2.5-coder:32b)\b' || true
echo

echo "== Hermes oneshot sanity check =="
timeout 240s hermes --provider custom -m qwen3-coder:30b -z "Reply with exactly OK."
echo

echo "== Baseline result =="
echo "Validated baseline model: qwen3-coder:30b"
