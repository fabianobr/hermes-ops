# Teste NVIDIA como alternativa ao Qwen

O comparativo está em `scripts/benchmark_nvidia_qwen.py`. Ele usa os mesmos
dados sintéticos em português com `qwen3.5:latest` local e
`nvidia/nemotron-3-ultra-550b-a55b` hospedado. Não muda o provider do Hermes.

Casos: diagnóstico com JSON validado por valores esperados; chamada de
ferramenta de leitura com argumentos verificados, retorno sintético e resposta
final validada. Nenhuma ferramenta solicitada pelo modelo é executada no host.
São até três requisições por modelo, sequenciais, sem repetição automática.
O script mede tempo total por chamada, não tempo até o primeiro token.

```bash
python3 scripts/benchmark_nvidia_qwen.py --dry-run
python3 scripts/benchmark_nvidia_qwen.py --provider ollama --output logs/qwen-baseline.20261004.json
python3 scripts/benchmark_nvidia_qwen.py --provider nvidia --output logs/nvidia-candidate.20261004.json
```

A chamada NVIDIA exige `NVIDIA_API_KEY` no ambiente ou em `~/.hermes/.env`.
Se a chave estiver em outro arquivo, usar `--env-file /caminho/do/arquivo`.
O arquivo é lido como dados, nunca executado como shell. Não fornecer a chave
como argumento nem colocá-la no repositório. Os resultados locais em `logs/`
ficam ignorados pelo Git. O modelo recebe apenas prompts sintéticos definidos
no script, sem memória, arquivos privados ou dados de Telegram.

Uma aprovação nesses dois casos comprova somente o funcionamento desses casos
na API direta. Antes de selecionar a NVIDIA no Hermes, testar também o agente
com ferramentas reais de leitura em um workspace sem segredos. Verificar
latência, erros e consistência em mais repetições antes de mudar o padrão.

## Resultado inicial local

Em 2026-10-04, uma execução por caso no Qwen3.5:

| Caso | Resultado | Tempo total das chamadas |
| --- | --- | --- |
| Diagnóstico | Passou; JSON e valores corretos | 54,860 s |
| Ferramenta e retorno | Chamada e valores corretos; falhou no formato JSON puro por incluir cercas Markdown | 3,649 s |

O modelo estava descarregado antes do teste e apareceu depois com 65.536 tokens
de contexto e execução 100% GPU. O tempo do primeiro caso inclui o possível
custo de carregamento; não representa latência estável nem mediana. Foram
reportados 3.025 tokens de conclusão no diagnóstico, embora a resposta final
seja curta; o tempo inclui geração que não aparece no texto final.

A chave foi posteriormente cadastrada no `.env` do Hermes e lida pelo helper
sem exibição. O Ultra passou nos dois casos da API direta:

| Caso | Resultado | Tempo total das chamadas |
| --- | --- | --- |
| Diagnóstico | Passou; JSON e valores corretos | 107,269 s |
| Ferramenta e retorno | Passou; argumentos, valores e JSON puro corretos | 4,609 s |

Uma segunda rodada completa foi executada para verificar a variação:

| Caso | Qwen: tempo / resultado | Ultra: tempo / resultado |
| --- | --- | --- |
| Diagnóstico | 46,476 s / passou | 33,856 s / passou |
| Ferramenta e retorno | 3,641 s / valores corretos, mesmo erro de formato | 28,574 s / passou |

Nos quatro casos executados por modelo, Ultra passou em 4/4 e Qwen em 2/4
sob o critério estrito de JSON puro. O Qwen acertou os valores e as chamadas
de ferramenta em ambas as rodadas; sua reprovação foi somente por cercas
Markdown. Não interpretar o resultado como incapacidade de usar ferramentas.

Ultra é uma alternativa funcional para seleção manual: autenticação, API de
ferramentas e leitura pelo Hermes foram verificadas. Tem latência variável
(diagnóstico: 107,269 → 33,856 s; ferramenta: 4,609 → 28,574 s). Esses poucos
casos não provam superioridade geral ou velocidade previsível. Manter Qwen como
padrão local e selecionar Ultra para avaliação com dados apropriados à nuvem,
especialmente quando for útil liberar a GPU local. Não ativar fallback automático
com base neste teste. Não houve 429, timeout ou erro HTTP nas chamadas NVIDIA.

Capturas locais: `logs/qwen-baseline.20261004.json`,
`logs/nvidia-candidate.20261004.json`, `logs/nvidia-qwen-second.20261004.json`.
O helper retornou 1 na rodada conjunta devido ao formato do Qwen; isso não
representa falha do provider NVIDIA.

## Integração pelo Hermes

Também foi executado o agente instalado com provider `nvidia`, modelo Ultra,
`--safe-mode`, toolset `file`, até três iterações e orçamento de 120 segundos.
O workspace temporário tinha somente um `services.json` sintético. O agente
usou `read_file` e retornou corretamente:

```json
{"unhealthy_services":["comfyui"],"gpu_sufficient":false,"missing_mib":4096}
```

O CLI encerrou com código 0 e duração reportada de 46 segundos.
Esse tempo é de uma execução completa do Hermes,
não da mesma chamada direta usada na tabela. O modo de teste ignorou regras,
memória e customizações; gateway e auxiliares da configuração cotidiana não
foram validados. Não houve solicitação de escrita ou execução de comandos.

O launcher reportou um problema já presente: `agent.reasoning_overrides` está
como string, embora devesse ser um mapping YAML. Isso não impediu o teste e
não foi alterado como parte deste comparativo.

## Como usar como alternativa

Em uma nova sessão do CLI, selecionar explicitamente o provider e o modelo:

```bash
hermes chat --provider nvidia --model nvidia/nemotron-3-ultra-550b-a55b
```

Esse comando usa o Ultra naquela sessão. O padrão foi conferido após o teste:
continua `qwen3.5:latest`, provider `custom`, URL do Ollama em localhost e
contexto de 65.536 tokens. Não foi criada troca automática ou fallback.
O uso normal carrega suas customizações, portanto somente conteúdo apropriado
para a API externa deve entrar na sessão; veja os termos no estudo relacionado.

Dentro do chat do Hermes, os comandos documentados na versão instalada são:

```text
/model nvidia:nvidia/nemotron-3-ultra-550b-a55b
/model custom:qwen3.5:latest
```

O primeiro seleciona a NVIDIA e o segundo volta ao Qwen no endpoint local
configurado. No CLI, usar `--session` para forçar a troca somente na sessão;
`--global` persiste a seleção como padrão. `/model` sozinho abre o seletor no
CLI. A sintaxe foi conferida nos docs/código instalados; não foi exercitado o
comando de troca em uma conversa de Telegram. Um processo do gateway iniciado
antes do cadastro da chave pode precisar ser reiniciado para carregar o `.env`.

Validações do helper: `--dry-run`, `python3 -m py_compile` e `git diff --check`.
