"""Deterministic natural-language routing for the check-system command."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any


logger = logging.getLogger(__name__)

_CONCEPTUAL_PATTERNS = (
    r"\bo que e\b",
    r"\bo que significa\b",
    r"\bcomo funciona\b",
    r"\bexplique\b",
    r"\bexplica\b",
    r"\bdocumentacao\b",
    r"\bqual (?:e )?a finalidade\b",
)

_CHECK_SYSTEM_PATTERNS = (
    r"\b(?:skill|habilidade) (?:de )?(?:check system|checar o sistema)\b",
    r"\bcheck system\b",
    r"\bcheck do sistema\b",
    r"\bchecar o sistema\b",
    r"\bcheque (?:o|do) sistema\b",
    r"\bchecagem do sistema\b",
    r"\bstatus (?:do|da) (?:host|sistema|servidor|maquina)\b",
)

_ACTION_PATTERN = re.compile(
    r"\b(?:acione|aciona|ative|ativa|execute|executa|rode|rodar|roda|faca|"
    r"fazer|verifique|verifica|cheque|use|mostre|mostra|resuma|resumir|"
    r"qual|quero|preciso)\b"
)


def normalize_request(text: str) -> str:
    """Normalize accents and punctuation without retaining message content."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^a-z0-9]+", " ", ascii_text.lower())
    return " ".join(words_only.split())


def is_check_system_request(text: str) -> bool:
    """Return True only for operational requests, not conceptual questions."""
    normalized = normalize_request(text)
    if not normalized:
        return False

    if any(re.search(pattern, normalized) for pattern in _CONCEPTUAL_PATTERNS):
        return False

    matched = any(re.search(pattern, normalized) for pattern in _CHECK_SYSTEM_PATTERNS)
    if not matched:
        return False

    if normalized in {
        "check system",
        "check do sistema",
        "checar o sistema",
        "checagem do sistema",
        "status do host",
        "status do sistema",
    }:
        return True

    return bool(_ACTION_PATTERN.search(normalized))


def _message_type_value(event: Any) -> str:
    message_type = getattr(event, "message_type", "")
    return str(getattr(message_type, "value", message_type)).lower()


def _platform_value(event: Any) -> str:
    source = getattr(event, "source", None)
    platform = getattr(source, "platform", "")
    return str(getattr(platform, "value", platform)).lower()


def _authorized_for_voice(event: Any, gateway: Any) -> bool:
    """Avoid running STT before auth for unknown gateway senders."""
    checker = getattr(gateway, "_is_user_authorized", None)
    source = getattr(event, "source", None)
    if not callable(checker) or source is None:
        return False
    try:
        return bool(checker(source))
    except Exception:
        logger.debug("Could not verify voice sender authorization", exc_info=True)
        return False


def route_check_system(**kwargs: Any) -> dict[str, str] | None:
    """Rewrite matching text or Telegram voice requests to /check-system."""
    event = kwargs.get("event")
    if event is None:
        return None

    text = str(getattr(event, "text", "") or "").strip()
    if text.startswith("/"):
        return None

    message_type = _message_type_value(event)
    if message_type in {"voice", "audio"}:
        if _platform_value(event) != "telegram":
            return None
        if not _authorized_for_voice(event, kwargs.get("gateway")):
            return None

        media_urls = list(getattr(event, "media_urls", None) or [])
        if not media_urls:
            return None

        from tools.transcription_tools import transcribe_audio

        result = transcribe_audio(media_urls[0])
        if not result.get("success"):
            return None
        text = str(result.get("transcript", "") or "").strip()

    if not is_check_system_request(text):
        return None

    logger.info(
        "Routing natural check-system request to /check-system (platform=%s, type=%s)",
        _platform_value(event) or "unknown",
        message_type or "unknown",
    )
    return {"action": "rewrite", "text": "/check-system"}


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", route_check_system)
