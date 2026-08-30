"""Deterministic natural-language routing for the start-comfyui command."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any


logger = logging.getLogger(__name__)

_MENU_COMMAND_DESCRIPTION = "Start the local ComfyUI container."

_CONCEPTUAL_PATTERNS = (
    r"\bo que e\b",
    r"\bo que significa\b",
    r"\bcomo funciona\b",
    r"\bexplique\b",
    r"\bexplica\b",
    r"\bdocumentacao\b",
    r"\bqual (?:e )?a finalidade\b",
)

# Requests that ask for the opposite action, or for a restart, must reach the
# agent instead of a start-only script. Bare "para" is excluded on purpose: in
# Portuguese it is usually the preposition, as in "para iniciar o comfyui".
_OPPOSITE_ACTION_PATTERN = re.compile(
    r"\b(?:pare|parar|desliga|desligue|desligar|derruba|derrube|derrubar|"
    r"stop|down|encerre|encerra|encerrar|mate|matar|kill|remova|remove|"
    r"remover|reinicie|reinicia|reiniciar|restart|rebuild)\b"
)

_COMFYUI_PATTERNS = (
    r"\bcomfy ?ui\b",
    r"\bconfy ?ui\b",
    r"\bcomfy\b",
)

_START_PATTERN = re.compile(
    r"\b(?:inicie|inicia|iniciar|sobe|suba|subir|liga|ligue|ligar|levante|"
    r"levanta|levantar|ative|ativa|ativar|start|starta|startar|acione|aciona|"
    r"acionar|execute|executa|executar|rode|roda|rodar|abre|abra|abrir|"
    r"disponibilize|disponibiliza)\b"
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
    """Return True only for explicit requests to start ComfyUI."""
    normalized = normalize_request(text)
    if not normalized:
        return False

    if any(re.search(pattern, normalized) for pattern in _CONCEPTUAL_PATTERNS):
        return False

    if _OPPOSITE_ACTION_PATTERN.search(normalized):
        return False

    if not mentions_comfyui(normalized):
        return False

    if normalized in {"start comfyui", "start comfy ui", "comfyui start"}:
        return True

    # Starting a container is a write action, so require an explicit verb
    # rather than any mention of ComfyUI.
    return bool(_START_PATTERN.search(normalized))


def _message_type_value(event: Any) -> str:
    message_type = getattr(event, "message_type", "")
    return str(getattr(message_type, "value", message_type)).lower()


def _platform_value(event: Any) -> str:
    source = getattr(event, "source", None)
    platform = getattr(source, "platform", "")
    return str(getattr(platform, "value", platform)).lower()


def route_start_comfyui(**kwargs: Any) -> dict[str, str] | None:
    """Rewrite matching text requests to /start-comfyui.

    Voice messages are deliberately not routed here. Unlike the read-only
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
