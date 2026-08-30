"""Deterministic natural-language routing for the start-comfyui command."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any


logger = logging.getLogger(__name__)

_MENU_COMMAND_DESCRIPTION = "Start the local ComfyUI container."

# Every guard below fails towards the agent, never towards the container: an
# unmatched request still reaches the LLM, which can start ComfyUI after asking.
# A false positive is the expensive direction, because the rewrite bypasses the
# LLM entirely and starts a GPU container without anyone in the loop.

_CONCEPTUAL_PATTERNS = (
    r"\bo que\b",
    r"\bcomo (?:funciona|faco|posso|uso|usar|seria)\b",
    r"\bexplic\w*\b",
    r"\bdocumenta\w*\b",
    r"\bqual (?:e )?a finalidade\b",
    r"\bdepois que\b",
    r"\bpor que\b",
)

_NEGATION_PATTERN = re.compile(r"\b(?:nao|nunca|jamais|sem|nem)\b")

# Requests that ask for the opposite action, or for a restart, must reach the
# agent instead of a start-only script. Bare "para" is excluded on purpose: in
# Portuguese it is usually the preposition, as in "para iniciar o comfyui".
_OPPOSITE_ACTION_PATTERN = re.compile(
    r"\b(?:pare|parar|desliga|desligue|desligar|derruba|derrube|derrubar|"
    r"stop|down|encerre|encerra|encerrar|mate|matar|kill|remova|remove|"
    r"remover|reinicie|reinicia|reiniciar|restart|rebuild)\b"
)

# Hermes ships a bundled "comfyui" skill that runs workflows through comfy-cli.
# Anything that smells like generation work belongs to that skill, so it must
# reach the agent with the request intact instead of being rewritten away.
_CREATIVE_TASK_PATTERN = re.compile(
    r"\b(?:workflow\w*|fluxo\w*|node|nodes|imagem|imagens|video|videos|audio|"
    r"prompt\w*|gera|gere|gerar|gerando|render\w*|checkpoint\w*|lora|loras|"
    r"modelo|modelos|interface|api)\b"
)

# A message naming another service is a multi-target request. Routing it would
# silently discard the half this command cannot serve.
_OTHER_SERVICE_PATTERN = re.compile(
    r"\b(?:ollama|lm studio|lmstudio|open webui|openwebui|n8n|litellm|"
    r"searxng|whisper|docker)\b"
)

_COMFYUI_PATTERNS = (
    r"\bcomfy ?ui\b",
    r"\bconfy ?ui\b",
    r"\bcomfy\b",
)

# Verbs that can only mean "bring the container up".
_START_PATTERN = re.compile(
    r"\b(?:inicie|inicia|iniciar|sobe|suba|subir|liga|ligue|ligar|levante|"
    r"levanta|levantar|ative|ativa|ativar|start|starta|startar)\b"
)

# Generic verbs such as "rode" mean "run a workflow" as often as they mean
# "start the container", so they only count when the message also names the
# skill or the container itself.
_GENERIC_VERB_PATTERN = re.compile(
    r"\b(?:acione|aciona|acionar|execute|executa|executar|rode|roda|rodar|"
    r"use|usa|usar|utilize|utiliza|utilizar|chame|chama|chamar)\b"
)

_EXPLICIT_TARGET_PATTERN = re.compile(
    r"\b(?:skill|habilidade|comando|container|containner|conteiner)\b"
)


def normalize_request(text: str) -> str:
    """Normalize accents and punctuation without retaining message content."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^a-z0-9]+", " ", ascii_text.lower())
    return " ".join(words_only.split())


def mentions_comfyui(normalized: str) -> bool:
    return any(re.search(pattern, normalized) for pattern in _COMFYUI_PATTERNS)


def is_start_comfyui_request(text: str) -> bool:
    """Return True only for unambiguous requests to start the container."""
    normalized = normalize_request(text)
    if not normalized:
        return False

    if not mentions_comfyui(normalized):
        return False

    if normalized in {"start comfyui", "start comfy ui", "comfyui start"}:
        return True

    for pattern in (
        _NEGATION_PATTERN,
        _OPPOSITE_ACTION_PATTERN,
        _CREATIVE_TASK_PATTERN,
        _OTHER_SERVICE_PATTERN,
    ):
        if pattern.search(normalized):
            return False

    if any(re.search(pattern, normalized) for pattern in _CONCEPTUAL_PATTERNS):
        return False

    if _START_PATTERN.search(normalized):
        return True

    return bool(
        _GENERIC_VERB_PATTERN.search(normalized)
        and _EXPLICIT_TARGET_PATTERN.search(normalized)
    )


def _message_type_value(event: Any) -> str:
    message_type = getattr(event, "message_type", "")
    return str(getattr(message_type, "value", message_type)).lower()


def _platform_value(event: Any) -> str:
    source = getattr(event, "source", None)
    platform = getattr(source, "platform", "")
    return str(getattr(platform, "value", platform)).lower()


def route_start_comfyui(**kwargs: Any) -> dict[str, str] | None:
    """Rewrite matching text requests to /start-comfyui.

    Voice messages are deliberately not routed. Unlike the read-only
    check-system report, this command changes host state, so a transcription
    error must not be enough to start a GPU container.
    """
    event = kwargs.get("event")
    if event is None:
        return None

    text = str(getattr(event, "text", "") or "").strip()
    if text.startswith("/"):
        return None

    if _message_type_value(event) not in {"", "text"}:
        return None

    if not is_start_comfyui_request(text):
        return None

    logger.info(
        "Routing natural start-comfyui request to /start-comfyui (platform=%s)",
        _platform_value(event) or "unknown",
    )
    return {"action": "rewrite", "text": "/start-comfyui"}


def start_comfyui_command_fallback(raw_args: str) -> str:
    """Explain the required quick command when its dispatch entry is missing.

    Hermes dispatches configured quick commands before plugin commands. This
    handler therefore runs only when the plugin is installed without the
    corresponding quick command.
    """
    del raw_args
    return (
        "The /start_comfyui menu entry requires the start-comfyui quick command. "
        "Install config/hermes-quick-commands.yaml.example and restart the gateway."
    )


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", route_start_comfyui)
    # Plugin commands are placed ahead of capped skill entries in Telegram's
    # menu. Telegram renders this hyphenated name as the valid /start_comfyui
    # form, while the configured quick command still handles execution first.
    ctx.register_command(
        "start-comfyui",
        start_comfyui_command_fallback,
        description=_MENU_COMMAND_DESCRIPTION,
    )
