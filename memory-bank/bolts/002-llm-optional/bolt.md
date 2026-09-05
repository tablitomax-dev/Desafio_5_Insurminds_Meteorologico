# Bolt — 002-llm-optional

> Intent: 002-proactive-communication | Unit: message-generation (story 06)
> Status: `active` (implementação concluída; aguardando revisão → commit → PR)
> Prioridade: P1 | Data: 2026-09-04

## Objetivo

Implementar a story-06 (LLM opcional melhora a mensagem):

1. `LlmGenerator` implementando a port `MessageGenerator` via **Pydantic AI**
   (model-agnostic), com fallback silencioso para `TemplateGenerator`.
2. Seleção via env no composition root (CLI), conforme unit message-generation.
3. Modo exercitado reportado no relatório da rodada (llm | template | híbrido).
4. Demo NUNCA quebra sem API key (critério de aceite #4 do intent).
5. Binding do modelo: o MESMO executor do ai-dlc definido pelo dono —
   `openrouter:z-ai/glm-5.3-flash` (OpenRouter).

## Plano TDD

1. [x] Contexto: intent 002 + story-06 + unit + `messages.py`/`pipeline.py`/`cli.py`.
2. [x] Checkpoint SDK: `pydantic-ai==1.107.1` e `openai==2.36.0` presentes; escolha
    pydantic-ai (decisão do intent 002). `OPENROUTER_API_KEY` presente, `OPENAI_API_KEY` não.
3. [x] TDD vermelho: `tests/adapters/test_llm_messages.py` (14 casos, fake agent injetado,
    zero rede) — vermelho confirmado (`ModuleNotFoundError: app.adapters.llm_messages`).
4. [x] Verde: `app/adapters/llm_messages.py` (adapter hexagonal, import LAZY do SDK) +
    promoção de `_EVENT_BY_KIND`/`_RECOMMENDATIONS_BY_KIND` para públicos em `messages.py`.
5. [x] CLI (composition root): `build_generator()` via env + `describe_mode()` no relatório.
6. [x] Retry curto com backoff (3 tentativas, 1s/2s) para 429/5xx transitórios —
    descoberto no smoke: chamadas em rajada caem em rate limit do provedor.
7. [x] Gate completo + suíte ai-dlc + smoke real com LLM (GLM-5.3-flash via OpenRouter).

## Critérios de aceite

- [x] `LLM_MODEL` setada → mensagens do `LlmGenerator`; relatório mostra `(modo llm)`.
- [x] Env ausente OU erro de LLM (chave, API, resposta vazia, SDK ausente) →
  fallback silencioso; demo segue; relatório mostra o modo real (template/fallback/híbrido).
- [x] `LLM_PROVIDER=template` força template mesmo com `LLM_MODEL` setada.
- [x] Mensagem ≤ 480 chars (truncamento com salvaguarda igual ao template).
- [x] Testes sem rede/SDK (CI seguro) + smoke real aprovado com as 5 mensagens do LLM.
- [x] Suítes verdes: pytest 103 (produto) + 122 (ai-dlc); ruff limpo; mypy `app/` 16 files limpo.

## Decisões

- **Contrato de env** (aprovado pelo humano): `LLM_MODEL` (identificador pydantic-ai) ativa o
  modo LLM; `LLM_PROVIDER=llm` ativa com `DEFAULT_MODEL`; `LLM_PROVIDER=template` força template;
  default sem env = template (demo da banca imune).
- **Binding do modelo**: `openrouter:z-ai/glm-5.3-flash` — mesmo executor do ai-dlc (decisão do
  dono; GLM aceita effort apenas max/high/low, irrellevante aqui). Key via `OPENROUTER_API_KEY`.
- **Import LAZY do pydantic-ai** + agente injectável nos testes: modo template nunca exige SDK;
  CI roda os testes do caminho LLM sem chave e sem rede.
- **Retry curto no adapter** (não no pipeline): fronteira externa; falha definitiva → fallback
  silencioso, modo reportado.
- **pydantic-ai pinado em `requirements-dev.txt`** (1.107.1, py.typed): mypy resolve sem ignore;
  CI/CI-cache reproduzem o ambiente da demo. Modo template segue indep. do pacote.

## Fontes carregadas

`AGENTS.md`, intent 002 (`intent.md`, `story-index.md`, `stories/story-06-llm-optional.md`,
`units/message-generation.md`), `app/domain/{messages,risk,holders}.py`, `app/pipeline.py`,
`app/cli.py`, `tests/test_cli.py`, `tools/ai-dlc` (binding GLM: `ai-dlc-spec.yaml`, ADR-006,
README). Não carregados: standards required completos (só `_index.csv`), bolts anteriores.

## Smoke real (OpenRouter + GLM-5.3-flash)

`python -m app run --offline` com `LLM_MODEL=openrouter:z-ai/glm-5.3-flash`: **5/5 mensagens
reescritas pelo LLM** (empáticas, com nome, severidade/motivo e TODAS as recomendações;
ex.: "João Souza, alerta da sua seguradora: granizo de alta severidade previsto na sua
região..."), relatório: `4. Mensagens geradas: 5 (modo llm)`. Rodada sem LLM (default):
mesmo fluxo, `(modo template)`. Nota: o fallback completo observado num smoke intermediário foi
causa do env reduzido do driver de teste (cliente HTTP do filho quebrado), não do produto.

## Compact Summary

**Entregue**: `LlmGenerator` (story-06) com fallback silencioso + retry de 429; seleção por env
no composition root; modo reportado no relatório; pydantic-ai pinado no gate.
**Qualidade**: TDD vermelho→verde (16 testes novos: 14 adapter + 3 CLI, com fakes);
pytest 103; ai-dlc 122; ruff limpo; mypy limpo (16 files); smoke real 5/5 `(modo llm)`.
**Decisões**: env contract aprovado (`LLM_MODEL`/`LLM_PROVIDER`); binding GLM-5.3-flash/OpenRouter;
lazy import; retry no adapter.
**Stories**: story-06 → done; unit message-generation → done (7/7 do intent 002 concluídas).
**Próximo**: revisão humana → commit/push → PR; após merge, intent 002 MVP completo ponta a ponta
(stories 01–07 done); Fase 2 do step pre-merge e compactação de bolts como dívidas.
