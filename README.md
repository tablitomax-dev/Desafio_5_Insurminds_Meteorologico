# Desafio 5 I2A2 — Ferramenta Inteligente para Comunicação Proativa com o Segurado

> Monitoramento meteorológico público → detecção de risco por perfil de seguro →
> mensagem preventiva personalizada (template ou LLM) → envio simulado + relatório.

## O problema

A comunicação seguradora ↔ segurado é historicamente **reativa**: o contato acontece
depois do sinistro. Este projeto inverte a lógica — usa a **API pública Open-Meteo**
para antecipar eventos meteorológicos e avisar o segurado **antes do sinistro**,
demonstrando o valor de agentes inteligentes no relacionamento com o segurado.

## Como rodar a demo

Requisitos: Python 3.12+ (sem instalar nada para o modo template).

```bash
# 1) Demo determinística offline (banca sem internet — fixtures versionadas)
python -m app run --offline

# 2) Demo online (Open-Meteo real, sem API key)
python -m app run

# 3) Demo com LLM reescrevendo as mensagens (Pydantic AI, model-agnostic)
export OPENROUTER_API_KEY=sua-chave          # Windows PowerShell: $env:OPENROUTER_API_KEY='...'
export LLM_MODEL=openrouter:z-ai/glm-5.3-flash  # identificador pydantic-ai
python -m app run --offline

# Forçar o modo template mesmo com LLM_MODEL setada:
export LLM_PROVIDER=template
```

O relatório de rodada no console mostra as 5 etapas: segurados consultados,
eventos detectados, alertas por regra, mensagens geradas (com o **modo**:
`template`, `llm` ou fallback/híbrido) e envios simulados.

**Garantia de robustez**: sem chave, sem rede ou com a LLM instável, a demo
**nunca quebra** — o `LlmGenerator` tem fallback silencioso para o
`TemplateGenerator` (com retry para erros transitórios de API), e o modo
exercitado é sempre reportado.

## Regras de negócio (detecção de risco)

| Evento | Gatilho | Impactados | Severidade |
|---|---|---|---|
| Chuva intensa | precipitação ≥ 10 mm/h | seguros **residenciais** | medium |
| Granizo | weathercode de granizo (WMO) | seguros **auto** | high |
| Vento forte | vento ≥ 60 km/h | região **costeira** | medium |

Cada mensagem traz nome do segurado, evento, severidade e **≥ 2 recomendações
preventivas específicas** do tipo de evento (drenagem/cobertura do veículo/
reforço de estruturas), limitada a 480 caracteres.

## Arquitetura (Ports & Adapters / DDD modular)

```text
data/*.json ──► adapters/catalog.py ─┐
Open-Meteo ──► adapters/open_meteo ──┤      ┌─► domain/risk.py   (regras puras)
fixtures ────► adapters/fixtures ────┴─► pipeline.py ──┼─► domain/messages (template/Llm)
                                             ▲         └─► domain/notify   (simulado)
                              cli.py (composition root) ┘
```

- **Domain puro e sem I/O** (`app/domain/`): regras de risco declarativas,
  ports (`WeatherProvider`, `PolicyHolderRepository`, `MessageGenerator`,
  `NotificationSender`) e entidades.
- **Adapters** (`app/adapters/`): Open-Meteo (stdlib-only), catálogo
  in-memory com seeds JSON, fixtures para demo offline e `LlmGenerator`
  (import lazy de Pydantic AI — o modo template nunca exige o SDK).
- **Pipeline** recebe ports prontas; a **CLI** é o composition root
  (`LLM_MODEL`/`LLM_PROVIDER` selecionam a implementação da mensagem).

Modelo binding default do LLM: `openrouter:z-ai/glm-5.3-flash` (mesmo
executor usado pelas ferramentas AI-DLC deste repositório).

## Qualidade e governança

- **TDD** vermelho→verde em todas as units; **103 testes** do produto +
  **122** da suíte AI-DLC (`pytest`), **ruff** e **mypy** limpos.
- **CI obrigatório** em todo PR/push para `main` (`.github/workflows/ci.yml`):
  `ruff check .` + `mypy app` + `pytest`.
- **AI-DLC completo** (ver [AGENTS.md](AGENTS.md)): intents, stories, units,
  bolts e ADRs em [memory-bank/](memory-bank/) — requisitos, decisões e
  execução auditáveis (`docs/decisions/`, `memory-bank/bolts/`).

## Estrutura

```text
app/            produto (domain, adapters, pipeline, cli)
tests/          testes do produto (pytest; pythonpath=. via pytest.ini)
data/           seeds de segurados + fixtures meteorológicas da demo offline
docs/           decisões (ADRs) e tasks da ferramenta AI-DLC
memory-bank/    intents, stories, units, bolts, standards (AI-DLC Option A)
tools/ai-dlc/   orquestrador + step pré-merge de qualidade (governança)
```
