#!/usr/bin/env python3
"""Compare synthetic ops tasks without changing Hermes configuration.

Verification: python3 scripts/benchmark_nvidia_qwen.py --dry-run
Local baseline: python3 scripts/benchmark_nvidia_qwen.py --provider ollama
Comparison: python3 scripts/benchmark_nvidia_qwen.py --output logs/nvidia-qwen.json
This tests direct APIs; a passing result still needs an end-to-end Hermes test.
"""

import argparse
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request


MODELS = {
    "ollama": ("http://127.0.0.1:11434/v1/chat/completions", "qwen3.5:latest"),
    "nvidia": ("https://integrate.api.nvidia.com/v1/chat/completions",
               "nvidia/nemotron-3-ultra-550b-a55b"),
}
SYSTEM = "Responda em português. Use somente os dados fornecidos. Não invente medições."
DIAGNOSIS = (
    'Dados sintéticos: {"ollama":{"status":"healthy"},'
    '"comfyui":{"status":"exited"},"gpu":{"free_mib":4096},'
    '"requested_model":{"required_mib":8192}}. '
    'Retorne apenas JSON com estas chaves: unhealthy_services (lista), '
    'gpu_sufficient (booleano), missing_mib (inteiro).'
)
TOOL = {
    "type": "function",
    "function": {
        "name": "read_service_status",
        "description": "Consulta somente de leitura do estado de um serviço.",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "enum": ["comfyui"]}},
            "required": ["service"], "additionalProperties": False},
    },
}


def read_key(filename):
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if key:
        return key
    path = Path(filename).expanduser()
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip().removeprefix("export ")
            if line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "NVIDIA_API_KEY":
                return value.strip().strip("\"'")
    return ""


def chat(provider, key, messages, timeout, **extra):
    url, model = MODELS[provider]
    headers = {"Content-Type": "application/json"}
    if provider == "nvidia":
        headers["Authorization"] = "Bearer " + key
    data = {"model": model, "messages": messages, "max_tokens": 4096,
            "temperature": 0, "stream": False, **extra}
    request = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        # Avoid printing provider error bodies that may contain credentials.
        raise RuntimeError(f"HTTP {exc.code}") from None
    message = body["choices"][0]["message"]
    return message, round(time.monotonic() - started, 3), body.get("usage", {})


def run_case(provider, key, case, timeout):
    messages = [{"role": "system", "content": SYSTEM}]
    started = time.monotonic()
    result = {"provider": provider, "model": MODELS[provider][1], "case": case}
    try:
        if case == "diagnosis":
            messages.append({"role": "user", "content": DIAGNOSIS})
            message, elapsed, usage = chat(provider, key, messages, timeout)
            content = message.get("content") or ""
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None
            passed = (isinstance(parsed, dict)
                      and set(parsed) == {"unhealthy_services", "gpu_sufficient", "missing_mib"}
                      and parsed["unhealthy_services"] == ["comfyui"]
                      and parsed["gpu_sufficient"] is False
                      and type(parsed["missing_mib"]) is int
                      and parsed["missing_mib"] == 4096)
            result.update(passed=passed, api_seconds=elapsed, usage=usage, content=content)
        else:
            messages.append({"role": "user", "content":
                "Consulte o estado do comfyui usando a ferramenta. Depois retorne "
                "apenas JSON com service e status. Não execute mudanças."})
            message, first_elapsed, first_usage = chat(
                provider, key, messages, timeout, tools=[TOOL], tool_choice="auto")
            calls = message.get("tool_calls", [])
            if len(calls) != 1:
                raise ValueError("Expected exactly one tool call")
            call = calls[0]
            if (call.get("type") != "function" or not call.get("id")
                    or call["function"]["name"] != "read_service_status"
                    or json.loads(call["function"]["arguments"]) != {"service": "comfyui"}):
                raise ValueError("Incorrect tool call")
            # Synthetic tool result: no shell or Docker action is executed.
            messages.append({"role": "assistant", "content": message.get("content"),
                             "tool_calls": calls})
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": '{"service":"comfyui","status":"exited"}'})
            final, second_elapsed, second_usage = chat(provider, key, messages, timeout)
            content = final.get("content") or ""
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None
            result.update(passed=parsed == {"service": "comfyui", "status": "exited"},
                          api_seconds=round(first_elapsed + second_elapsed, 3),
                          usage=[first_usage, second_usage], content=content)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError,
            IndexError, TypeError, RuntimeError) as exc:
        result.update(passed=False, error=(str(exc) if isinstance(exc, RuntimeError)
                                          else type(exc).__name__))
    result["total_seconds"] = round(time.monotonic() - started, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["all", *MODELS], default="all")
    parser.add_argument("--env-file", default="~/.hermes/.env")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    providers = list(MODELS) if args.provider == "all" else [args.provider]
    if args.dry_run:
        print(json.dumps({"models": {p: MODELS[p] for p in providers},
                          "cases": ["diagnosis", "tool_roundtrip"],
                          "synthetic_data_only": True}, indent=2))
        return 0
    key = read_key(args.env_file) if "nvidia" in providers else ""
    if "nvidia" in providers and not key:
        parser.error("NVIDIA_API_KEY missing. Store it in the env file; never pass it as an argument.")
    results = []
    for provider in providers:
        for case in ["diagnosis", "tool_roundtrip"]:
            result = run_case(provider, key, case, args.timeout)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.output:
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
