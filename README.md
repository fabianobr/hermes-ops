# Hermes Ops

Operations workspace for running [Hermes Agent](https://hermes-agent.nousresearch.com/) as an operator for a local AI stack (Ollama / LM Studio), with localhost-only integrations and a Telegram gateway in polling mode.

This is not a packaged application. It is a set of runbooks, config templates, and small read-only scripts that make the host setup reproducible without storing any secrets in git.

## Layout

- `docs/` - runbooks and architecture notes. Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/reproducibility-status.md](docs/reproducibility-status.md).
- `config/` - secret-free templates to merge into `~/.hermes/` on the host.
- `scripts/` - validation and diagnostic helpers (read-only by design).
- `logs/`, `backups/` - local-only artifacts, ignored by git.

## Quick start

```bash
python3 scripts/check_local_backends.py        # validate Ollama / LM Studio endpoints
python3 scripts/list_ollama_models.py          # list local models and context windows
bash scripts/validate_hermes_baseline.sh       # end-to-end Hermes baseline check
bash scripts/check_telegram_gateway.sh         # non-secret Telegram gateway status
```

## Security model

No secrets, tokens, or host identifiers are committed. Real configuration lives in `~/.hermes/` on the host; this repo only carries placeholders and procedures. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the trust boundaries and [AGENTS.md](AGENTS.md) for contribution rules.

## License

[MIT](LICENSE)
