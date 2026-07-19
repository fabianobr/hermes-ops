# Check-system router

O plugin `check-system-router` converte pedidos operacionais em linguagem natural para o comando determinístico `/check-system` antes do despacho ao modelo. Em áudio, o roteamento é limitado ao Telegram e só transcreve remetentes já autorizados pelo gateway.

## Instalação

```bash
mkdir -p ~/.hermes/plugins
cp -a config/hermes-plugins/check-system-router ~/.hermes/plugins/
hermes plugins enable check-system-router
hermes gateway restart
```

Repita a cópia e o restart após atualizar o plugin versionado.

## Áudio em português brasileiro

```bash
hermes config set voice.auto_tts true
hermes config set tts.provider edge
hermes config set tts.edge.voice pt-BR-FranciscaNeural
```

No Hermes atual, o streaming de texto do Telegram pode consumir a resposta antes do auto-TTS global. Desative apenas esse streaming para manter a resposta de voz:

```bash
hermes config set display.platforms.telegram.streaming false
hermes gateway restart
```

## Verificação

```bash
python3 -m unittest tests/test_check_system_router.py
hermes plugins list --enabled --plain
bash scripts/check_system_resources.sh
```

Envie no Telegram um áudio como `Acione a habilidade check system e resuma os gargalos`. O gateway deve registrar o roteamento para `/check-system` e responder com o relatório, incluindo `ollama ps`, em voz.
