#!/usr/bin/env python3
"""
Verification:
  python3 scripts/list_ollama_models.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


TAGS_URL = "http://127.0.0.1:11434/api/tags"
SHOW_URL = "http://127.0.0.1:11434/api/show"
TIMEOUT = 10


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "hermes-ops/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "hermes-ops/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def extract_context_length(payload: dict) -> str:
    model_info = payload.get("model_info")
    if isinstance(model_info, dict):
        for key, value in model_info.items():
            lowered = key.lower()
            if "context_length" in lowered or lowered.endswith(".context_length"):
                return str(value)
    details = payload.get("details")
    if isinstance(details, dict) and "num_ctx" in details:
        return str(details["num_ctx"])
    return "unknown"


def main() -> int:
    try:
        tags = get_json(TAGS_URL)
    except urllib.error.URLError as exc:
        print(f"FAILED: {exc}")
        return 1

    models = tags.get("models", [])
    if not isinstance(models, list) or not models:
        print("No Ollama models found.")
        return 1

    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if not isinstance(name, str) or not name:
            continue
        try:
            details = post_json(SHOW_URL, {"name": name})
            context_length = extract_context_length(details)
        except urllib.error.URLError as exc:
            context_length = f"error: {exc}"
        print(f"{name}\tcontext_length={context_length}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
