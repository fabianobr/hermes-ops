"""Behavior tests for the deterministic check-system gateway router."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PLUGIN_PATH = (
    Path(__file__).parents[1]
    / "config"
    / "hermes-plugins"
    / "check-system-router"
    / "__init__.py"
)
SPEC = importlib.util.spec_from_file_location("check_system_router", PLUGIN_PATH)
assert SPEC and SPEC.loader
ROUTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTER)


def make_event(
    text: str = "",
    message_type: str = "text",
    platform: str = "telegram",
    media_urls: list[str] | None = None,
):
    return SimpleNamespace(
        text=text,
        message_type=SimpleNamespace(value=message_type),
        source=SimpleNamespace(platform=SimpleNamespace(value=platform)),
        media_urls=media_urls or [],
    )


class CheckSystemRouterTests(unittest.TestCase):
    def test_matches_operational_requests(self):
        examples = (
            "Acione a habilidade check system e resuma os gargalos.",
            "Faça um check-system agora.",
            "Qual o status do host?",
            "check_system",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertTrue(ROUTER.is_check_system_request(example))

    def test_rejects_conceptual_or_unrelated_requests(self):
        examples = (
            "O que é a skill check-system?",
            "Explique como funciona o check system.",
            "Quais processos estão usando a GPU?",
            "Bom dia",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_check_system_request(example))

    def test_rewrites_matching_text(self):
        event = make_event(text="Rode o check do sistema")
        self.assertEqual(
            ROUTER.route_check_system(event=event, gateway=object()),
            {"action": "rewrite", "text": "/check-system"},
        )

    def test_rewrites_authorized_telegram_voice(self):
        event = make_event(message_type="voice", media_urls=["/tmp/request.ogg"])
        gateway = SimpleNamespace(_is_user_authorized=lambda source: True)
        transcription = types.ModuleType("tools.transcription_tools")
        transcription.transcribe_audio = lambda path: {
            "success": True,
            "transcript": "Acione a habilidade check system",
        }
        tools_package = types.ModuleType("tools")

        with patch.dict(
            sys.modules,
            {
                "tools": tools_package,
                "tools.transcription_tools": transcription,
            },
        ):
            result = ROUTER.route_check_system(event=event, gateway=gateway)

        self.assertEqual(result, {"action": "rewrite", "text": "/check-system"})

    def test_does_not_transcribe_unauthorized_voice(self):
        event = make_event(message_type="voice", media_urls=["/tmp/request.ogg"])
        gateway = SimpleNamespace(_is_user_authorized=lambda source: False)
        self.assertIsNone(ROUTER.route_check_system(event=event, gateway=gateway))


if __name__ == "__main__":
    unittest.main()
