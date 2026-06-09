#!/usr/bin/env python3
"""
Verification:
  python3 scripts/benchmark_ollama_chat.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request


CHAT_URL = "http://127.0.0.1:11434/v1/chat/completions"
TIMEOUT = 180
PROMPT = "Reply with exactly OK."
MODELS = [
    "qwen3-coder:30b",
    "deepseek-r1:32b",
    "qwen2.5vl:7b",
    "qwen3.5:latest",
]


def run_once(model: str) -> tuple[bool, float, str]:
    started = time.monotonic()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CHAT_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "hermes-ops/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")
        elapsed = time.monotonic() - started
    except urllib.error.URLError as exc:
        elapsed = time.monotonic() - started
        return False, elapsed, str(exc)
    except TimeoutError:
        elapsed = time.monotonic() - started
        return False, elapsed, "timeout"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        trimmed = raw[:200].strip().replace("\n", " ")
        return False, elapsed, f"non-JSON response: {trimmed}"

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return True, elapsed, content.strip()
    return True, elapsed, "response without assistant content"


def main() -> int:
    failed = False
    for model in MODELS:
        ok, elapsed, detail = run_once(model)
        status = "OK" if ok else "FAILED"
        print(f"{status}\t{model}\t{elapsed:.2f}s\t{detail}")
        if not ok:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
