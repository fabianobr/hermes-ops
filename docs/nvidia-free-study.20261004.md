# Estudo: NVIDIA gratuita no Hermes

Consulta inicial: 2026-10-04. Estudo documental seguido de teste autenticado.

Atualização posterior: o teste autenticado da API e da leitura pelo Hermes
está em [Teste NVIDIA × Qwen](nvidia-qwen-test.20261004.md). A decisão após os
testes é manter Qwen como opção 1 e usar Ultra como opção 2 manual. As seções
abaixo registram a investigação anterior ao cadastro da chave, sem alegar que
os outros modelos da comparação foram testados.

## Recomendação

Usar a API hospedada do NVIDIA Build pelo provider nativo `nvidia` do Hermes.
Começar a avaliação de qualidade com `nvidia/nemotron-3-ultra-550b-a55b`.
Comparar com Super para escolher o padrão após medir qualidade e latência;
avaliar Lightning para tarefas curtas. Manter Ollama disponível para trabalho
privado e operação independente da API externa.

Ultra é a primeira escolha para este estudo porque seu model card descreve
agentes complexos, uso de ferramentas, análise longa e português brasileiro.
Isso sustenta a adequação ao caso, mas não prova superioridade no nosso Hermes.
Sem chave e medições, não há vencedor empírico de qualidade ou velocidade.

## Ambiente observado

- O Hermes instalado reconhece `nvidia`, `NVIDIA_API_KEY` e `NVIDIA_BASE_URL`.
- Endpoint padrão: `https://integrate.api.nvidia.com/v1`.
- Configuração ativa: `custom`, `qwen3.5:latest`, Ollama em localhost,
  contexto de 65.536 tokens. Os documentos antigos sobre Qwen3 Coder não
  representam a seleção atual.
- GPU: RTX 5060 Ti com aproximadamente 16 GiB de VRAM.
- Ollama e LiteLLM estão ativos no Docker.
- Nenhuma variável NVIDIA/NIM foi encontrada no `.env` do Hermes. Credenciais
  fora desse arquivo e acesso da conta ao serviço não foram verificados.
- A ajuda do CLI confirma `--provider`, `--model`, `--oneshot` e `--run-budget`.

A inferência hospedada não ocupa a GPU local, evitando disputar VRAM com
ComfyUI. O Ultra exige hardware muito maior no deployment NIM documentado;
instalá-lo nesta GPU não é a rota recomendada.

## Modelos e disponibilidade pública

Os links abaixo foram abertos diretamente; presença na vitrine sozinha não
garante que o endpoint gratuito continue disponível.

| Modelo | Endpoint gratuito consultado | Papel proposto |
| --- | --- | --- |
| [Nemotron 3 Ultra](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b) | Disponível; texto; contexto anunciado de 1M | Primeiro candidato para qualidade em agentes e raciocínio |
| [Nemotron 3 Super](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b) | Disponível; texto; 1M | Comparativo para o uso cotidiano; também é o exemplo nativo nos docs locais do Hermes |
| [Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b) | Disponível; texto; 1M | Candidato para tarefas curtas e auxiliares; velocidade aqui ainda não medida |
| [Kimi K3](https://build.nvidia.com/moonshotai/kimi-k3) | Disponível; texto e imagem; 1M | Alternativa multimodal hospedada pela NVIDIA, desenvolvida pela Moonshot |
| [DeepSeek V4 Pro 0813](https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813) | Gratuito marcado como Deprecated | Excluir da seleção gratuita inicial |

O endereço antigo de Kimi K2.5 redirecionou para K2.6, cuja página não trouxe
evidência suficiente de disponibilidade. Não usar uma recomendação antiga de
K2.5 como prova de que o endpoint ainda funciona.

O contexto anunciado pertence ao catálogo/modelo. O limite realmente aceito
pela API e pela conta deve ser medido; começar com os atuais 65.536 tokens.

## O que significa gratuito

O [Build](https://build.nvidia.com/explore/discover) anuncia APIs serverless
gratuitas para desenvolvimento. Os
[termos de trial](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf)
limitam o uso a testes/avaliação, permitem limites e créditos e exigem uma
assinatura separada para produção. Portanto, a recomendação é para avaliação
manual no homelab; não é uma base gratuita garantida para gateway de produção.

Não foi confirmado um RPM fixo ou saldo de créditos da conta. Não assumir
40 RPM, 1.000 créditos ou acesso ilimitado a partir de tutoriais antigos.
Confirmar os limites exibidos na conta e tratar 429 com espera e tentativas
limitadas. Começar com uma sessão por vez.

Os termos também restringem envio de dados confidenciais/sensíveis e permitem
coleta de conteúdo em certas condições. No Hermes, arquivos lidos por ferramentas,
memória e instruções podem entrar no prompt. Avaliar com material público ou
sintético; manter operações com segredos no backend local.

## Integração proposta

1. Entrar no NVIDIA Build e gerar a chave para os endpoints gratuitos.
2. Guardar `NVIDIA_API_KEY` em `~/.hermes/.env`, fora do Git e do chat.
3. Testar a seleção somente na sessão:

```bash
hermes chat --provider nvidia --model nvidia/nemotron-3-ultra-550b-a55b
```

O provider nativo evita acrescentar um proxy. LiteLLM pode ser considerado
depois se vários consumidores precisarem de uma política central; não é
necessário para esta primeira integração.

Para uma futura seleção persistente, substituir o bloco `model` completo,
eliminando a URL antiga do Ollama:

```yaml
model:
  provider: nvidia
  default: nvidia/nemotron-3-ultra-550b-a55b
  base_url: https://integrate.api.nvidia.com/v1
  context_length: 65536
```

Esse trecho é uma proposta, não foi aplicado. A chave fica no `.env`.
Auxiliares com `provider: main` acompanham a seleção principal. Antes de
migrar o gateway, revisar especialmente `auxiliary.vision`: Ultra, Super e
Lightning são modelos de texto. Usar uma rota de visão separada, como o
Qwen3.5 local já usado no ambiente, ou avaliar Kimi K3.

## Validação para eventual ativação

Comparar Ultra e Super nos mesmos casos, repetidos três vezes: diagnóstico de
um JSON sintético de serviços; leitura de arquivos públicos com evidências;
uso de ferramenta somente de leitura; resposta em português; e correção de
um script pequeno em diretório temporário. Incluir Lightning nos casos curtos.
Registrar acerto, chamadas de ferramenta válidas, tempo até o primeiro token,
tempo total, 429/timeouts e encerramento do agente. Rejeitar conclusões sem
evidência e execução de ações não pedidas. Testar visão separadamente.

Promover o modelo que passar esses casos com latência aceitável; não escolher
apenas pelo tamanho ou por pontuações publicadas. Nenhuma chamada autenticada,
mudança do provider ativo ou alteração do Telegram foi realizada neste estudo.

## Fontes de integração e modelo

- Hermes instalado: `hermes_cli/auth.py`, `hermes_cli/runtime_provider.py` e
  `website/docs/integrations/providers.md`, revisão `e98be8a328` (2026-09-27).
- [Model card Ultra](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/modelcard): português brasileiro, tarefas alvo e hardware de deployment.
- [Model card Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard): arquitetura e posicionamento para agentes.
