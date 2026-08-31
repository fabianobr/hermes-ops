"""Behavior tests for the deterministic start-comfyui gateway router."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace


PLUGIN_PATH = (
    Path(__file__).parents[1]
    / "config"
    / "hermes-plugins"
    / "start-comfyui-router"
    / "__init__.py"
)
SPEC = importlib.util.spec_from_file_location("start_comfyui_router", PLUGIN_PATH)
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


class StartComfyuiRouterTests(unittest.TestCase):
    def test_matches_operational_requests(self):
        examples = (
            "Inicie o ComfyUI, por favor.",
            "sobe o comfyui",
            "Suba o container do ComfyUI agora.",
            "Liga o Comfy UI.",
            "start comfyui",
            "Acione a habilidade start comfyui.",
            "Preciso rodar o ComfyUI, ativa ele.",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertTrue(ROUTER.is_start_comfyui_request(example))

    def test_rejects_conceptual_or_unrelated_requests(self):
        examples = (
            "O que é o ComfyUI?",
            "Explique como funciona o ComfyUI.",
            "Onde fica a documentação do ComfyUI?",
            "O ComfyUI está fora do ar?",
            "Sobre o ComfyUI, qual workflow você recomenda?",
            "Inicie o Ollama.",
            "Bom dia",
            "",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_rejects_stop_and_restart_requests(self):
        examples = (
            "Pare o ComfyUI.",
            "Desliga o comfyui.",
            "Reinicie o ComfyUI.",
            "Derruba e sobe o comfyui de novo.",
            "Faz um rebuild do comfyui e liga.",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_rejects_negated_requests(self):
        # A rewrite bypasses the LLM, so a user declining to start the
        # container must never end up starting it.
        examples = (
            "Não inicie o ComfyUI agora.",
            "nao sobe o comfyui",
            "Não precisa subir o comfyui.",
            "Sobe o ollama, sem iniciar o comfyui.",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_rejects_questions_that_merely_contain_a_start_verb(self):
        examples = (
            "Explicar como iniciar o comfyui.",
            "Depois que eu subir o comfyui, o que faço?",
            "Por que o comfyui não sobe?",
            "Como funciona o start do comfyui?",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_rejects_generation_work_owned_by_the_bundled_skill(self):
        # Hermes ships a bundled comfyui skill for workflows. Rewriting these
        # would discard the request instead of serving it.
        examples = (
            "Quero rodar um workflow no ComfyUI.",
            "Abre a interface do comfyui pra mim.",
            "Usa o comfyui pra gerar uma imagem.",
            "Executa esse fluxo no comfyui.",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_rejects_multi_service_requests(self):
        # Routing would silently drop the half this command cannot serve.
        examples = (
            "sobe o comfyui e o ollama",
            "Inicie o comfyui e o n8n, por favor.",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(ROUTER.is_start_comfyui_request(example))

    def test_generic_verbs_need_an_explicit_target(self):
        self.assertTrue(
            ROUTER.is_start_comfyui_request("Acione a habilidade start comfyui.")
        )
        self.assertTrue(
            ROUTER.is_start_comfyui_request("Rode o container do comfyui.")
        )
        self.assertFalse(ROUTER.is_start_comfyui_request("Roda o comfyui aí."))

    def test_accepts_start_verb_after_the_preposition_para(self):
        self.assertTrue(
            ROUTER.is_start_comfyui_request("Use a skill para iniciar o comfyui.")
        )

    def test_rewrites_matching_text_message(self):
        result = ROUTER.route_start_comfyui(event=make_event("sobe o comfyui"))
        self.assertEqual(result, {"action": "rewrite", "text": "/start-comfyui"})

    def test_ignores_explicit_commands(self):
        self.assertIsNone(
            ROUTER.route_start_comfyui(event=make_event("/start-comfyui"))
        )

    def test_ignores_voice_messages(self):
        result = ROUTER.route_start_comfyui(
            event=make_event(
                "sobe o comfyui",
                message_type="voice",
                media_urls=["https://example.invalid/audio.ogg"],
            )
        )
        self.assertIsNone(result)

    def test_ignores_missing_event(self):
        self.assertIsNone(ROUTER.route_start_comfyui())

    def test_registers_hook_and_menu_command(self):
        hooks: list[tuple[str, object]] = []
        commands: list[tuple[str, object, str]] = []

        class Context:
            def register_hook(self, name, handler):
                hooks.append((name, handler))

            def register_command(self, name, handler, description=""):
                commands.append((name, handler, description))

        ROUTER.register(Context())
        self.assertEqual(hooks[0][0], "pre_gateway_dispatch")
        self.assertEqual(commands[0][0], "start-comfyui")
        self.assertTrue(commands[0][2])


if __name__ == "__main__":
    unittest.main()
