#!/usr/bin/env python3
"""
Verification:
  python3 scripts/check_local_backends.py
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request


CHECKS = [
    {
        "name": "LM Studio models",
        "url": "http://127.0.0.1:1234/v1/models",
        "timeout": 5,
    },
    {
        "name": "Ollama tags",
        "url": "http://127.0.0.1:11434/api/tags",
        "timeout": 5,
    },
]


def fetch_json(url: str, timeout: int) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "hermes-ops/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            return False, "timeout"
        return False, str(reason)
    except TimeoutError:
        return False, "timeout"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        trimmed = raw[:160].strip().replace("\n", " ")
        return True, f"non-JSON response: {trimmed}"

    if isinstance(payload, dict):
        keys = ", ".join(sorted(payload.keys())[:8])
        if "models" in payload and isinstance(payload["models"], list):
            names = []
            for item in payload["models"][:5]:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id")
                    if isinstance(name, str) and name:
                        names.append(name)
            if names:
                return True, f"JSON object keys: {keys}; models: {', '.join(names)}"
        if "data" in payload and isinstance(payload["data"], list):
            names = []
            for item in payload["data"][:5]:
                if isinstance(item, dict):
                    name = item.get("id") or item.get("name")
                    if isinstance(name, str) and name:
                        names.append(name)
            if names:
                return True, f"JSON object keys: {keys}; models: {', '.join(names)}"
        return True, f"JSON object keys: {keys}"
    if isinstance(payload, list):
        return True, f"JSON list length: {len(payload)}"
    return True, f"JSON type: {type(payload).__name__}"


def main() -> int:
    failed = False

    for check in CHECKS:
        ok, detail = fetch_json(check["url"], check["timeout"])
        status = "OK" if ok else "FAILED"
        print(f"{status}: {check['name']}")
        print(f"  URL: {check['url']}")
        print(f"  Detail: {detail}")
        print()
        if not ok:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
