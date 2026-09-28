---
name: telegram-web-search
description: Use when the user asks on Telegram to search the web, look something up, or show/find images. Searches with the Bright Data MCP tools and renders images inline in the chat.
---

# Web search and images on Telegram

## Search

1. Use the Bright Data MCP tools (`mcp_brightdata_*`): `search_engine` for a query, `scrape_as_markdown` to read a result page, `search_engine_batch` for several queries.
2. Answer in a short summary and list the source URLs. Do not paste raw JSON.

## Images

The Telegram gateway turns image references in your reply into native photos:

- Remote image: write `![description](https://host/path/image.jpg)`. The URL must be a direct image link (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`), not an HTML page.
- Local file: write `MEDIA:<absolute path>` on its own line.
- To find images, search with `search_engine` (Google `tbm=isch`) or scrape a page and pick direct image URLs. Send at most 3-4 per reply.
- A page link that is not a direct image will show as text only, so verify the extension first.
