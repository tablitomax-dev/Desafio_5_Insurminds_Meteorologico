# Execution Log — bolt 002-llm-optional

> Intent 002-proactive-communication | unit message-generation (story 06) | 2026-09-04 (America/Sao_Paulo)
> Branch `feature/002-llm-optional` criada de `main` (517a1a1) com autorização do humano.

| # | Etapa | Resultado |
|---|-------|-----------|
| 1 | Protocolo pré-edição (git status/branch/remote/diff): main limpa em 517a1a1 | ok |
| 2 | Contexto: story-06, unit message-generation, `messages.py`/`pipeline.py`/`cli.py` | plano proposto |
| 3 | Decisões do humano via AskUserQuestion: contrato `LLM_MODEL`+`LLM_PROVIDER`; pin pydantic-ai no requirements-dev; autorização da branch; usar o MESMO binding do ai-dlc (glm-5.3 flash) | contrato fixado |
| 4 | Binding localizado: `z-ai/glm-5.3-flash` via OpenRouter (ai-dlc-spec.yaml, ADR-006, README) | `DEFAULT_MODEL="openrouter:z-ai/glm-5.3-flash"` |
| 5 | Branch `feature/002-llm-optional` de `main` | escopo isolado |
| 6 | TDD vermelho: 14 testes com `_FakeAgent` (fake `run_sync`→`.output`; fail_first=N para retries/híbrido) | `ModuleNotFoundError` confirmado |
| 7 | Verde: adapter hexagonal com import LAZY do SDK, salvaguarda 480, contadores, `mode_label`, `describe_mode`, factory por env | 14 passed |
| 8 | Promoção de `_EVENT_BY_KIND`/`_RECOMMENDATIONS_BY_KIND` → públicos (reuso consistente no prompt) | sem mudança de comportamento |
| 9 | CLI: `build_generator()` + `describe_mode()`; 3 testes de wiring (modo llm, forçar template, fallback no relatório) | verde |
| 10 | `requirements-dev.txt` + `pydantic-ai==1.107.1`; `pip install -r` no `.venv` (não estava lá — check prévio tinha rodado no python do sistema) | pin ativo |
| 11 | Gate: pytest 101 → ruff I001 (autofix) → mypy import-not-found no pydantic_ai → instalado no `.venv` resolvido | verde |
| 12 | Smoke real 1 (driver com env REDUZIDA ao subprocesso): 5/5 caíram no fallback | investigar |
| 13 | Diagnóstico: chamada direta in-process OK (344 chars); rajadas rápidas em rate limit → retry com backoff (3 tentativas, 1s/2s) implementado + 2 testes novos + caso híbrido ajustado (fail_first=3) | pytest 103 |
| 14 | Smoke real 2 (env herdada integralmente): **5/5 mensagens do LLM**, `(modo llm)`; smoke sem env: `(modo template)` | critérios OK |
| 15 | Suíte ai-dlc: 122 passed; memory-bank (bolt, índices, story-06, unit, maintenance-log) | PR preparado |

## Detalhes relevantes

- **Descoberta de rate limit**: chamadas LLM consecutivas sem intervalo falhavam (429);
  com retries (1s/2s) a rodada completa com 5 mensagens passa sem fallback. O retry mora no
  adapter (fronteira externa); o pipeline permanece puro.
- **Falso negativo do smoke intermediário**: driver com env reduzida (`PATH`,`SYSTEMROOT`,key)
  quebrou o cliente HTTP (httpx/openai) no processo filho → todas as mensagens em fallback.
  Com env herdada, produto ok. Aprendizado: isolar env em subprocesso no Windows quebra SSL/DNS
  implícitos.
- **Sandbox engoliu comandos** (padrão conhecido): smoke reescrito como driver Python que
  captura RC/stdout/stderr em arquivo — fonte da verdade.
- **Faux pas corrigido na edição**: uma SearchReplace removeu `__post_init__`/`_create_agent`;
  detectado pela releitura e restaurado imediatamente.

## Decisões tomadas

1. Contrato de env aprovado pelo humano (`LLM_MODEL` ativa; `LLM_PROVIDER=template` força template).
2. Binding = mesmo executor do ai-dlc: `openrouter:z-ai/glm-5.3-flash`.
3. Retry curto no adapter; fallback silencioso como última linha; modo exercitado sempre reportado.
4. `pydantic-ai==1.107.1` em `requirements-dev.txt` (mypy py.typed resolve; CI = ambiente da demo).
