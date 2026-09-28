# Web Search and Images on Telegram

## Purpose

Let Hermes search the web with Bright Data and show images inline in the Telegram chat.

## Setup

1. Keep `BRIGHTDATA_API_KEY` in `~/.hermes/.env` (never commit it).
2. Register the Bright Data MCP server in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  brightdata:
    command: npx
    args: ["-y", "@brightdata/mcp"]
    env:
      API_TOKEN: ${BRIGHTDATA_API_KEY}
    timeout: 120
    connect_timeout: 120
```

3. Install the guidance skill:

```bash
mkdir -p ~/.hermes/skills/research/telegram-web-search
install -m 600 config/hermes-skills/telegram-web-search/SKILL.md ~/.hermes/skills/research/telegram-web-search/SKILL.md
```

4. Restart the gateway: `hermes gateway restart`.

## Images

No code change is needed. The gateway already converts `![alt](https://...img.jpg)` and `MEDIA:<path>` in replies into native Telegram photos. The skill tells the model to use those forms.

## Verify

```bash
hermes mcp test brightdata
```

Then send on Telegram: "search for X and show me a picture".
