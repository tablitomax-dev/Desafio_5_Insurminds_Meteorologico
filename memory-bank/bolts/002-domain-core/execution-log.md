# Execution Log — 002-domain-core

Registro cronológico (mais recente primeiro).

---

## [2026-09-03] Execução — núcleo de domínio (TDD) + primeiro run real do orquestrador:

| Estágio | Ação | Resultado |
|---|---|---|
| git | main ff `0350c78`→`cde0c6f` (PR #5 mergeado); branch `feature/002-domain-core` criada (autorizada) | ✅ |
| TDD vermelho | `tests/domain/{test_weather,test_holders,test_risk,test_messages,test_notify}.py` + `pytest.ini` (`pythonpath = .`) | ✅ 5 collection errors |
| TDD verde | `app/domain/{weather,holders,risk,messages,notify}.py` + `__init__.py` | ✅ 65 passed |
| fix | teste usava `isinstance` contra `Protocol` não-runtime_checkable → ajustado para duck typing (domínio intocado) | ✅ |
| lint | ruff/mypy disponibilizados (autorização) em `.venv` local — sandbox bloqueia pip global/user; `ruff.toml` versionado (E4/E7/E9/F/I/B) | ✅ |
| fix | B017: `pytest.raises(Exception)` → `FrozenInstanceError` nos 3 testes de imutabilidade (apontamento ruff legítimo) | ✅ |
| lint | ruff **all checks passed** (repo inteiro, 15 auto-fixes de imports); mypy `app/` **0 erros**; mypy `tools/ai-dlc` 25 apontamentos herdados da fase 1/2 — dívida de CI Python (fase 3) | ✅ |
| validação | pytest (venv, pytest 9.1.1): raiz 65 + ai-dlc 112 = **177 passed** | ✅ |
| run real | `bolt-002-1-domain-core`: success em 1 iteração (N2 → code_balanced); executor glm-5.3-flash 1245 tok US$0.000228; crítico gpt-5.6-luna-pro 13167 tok US$0.004797 — **accept** | ✅ |
| validação | pytest raiz 65 + ai-dlc 112 = **177 passed**; ruff/mypy não instalados no ambiente (não executados — registrar no PR) | ✅ |
| artefatos | bolt.md, execution-log, `bolts/_index.csv`, `intents/_index.csv`, story-index + 5 units do intent, maintenance-log | ✅ |
| entrega | stage/commit/push/PR aguardando autorização humana | ⏳ |

## Medição

| Métrica | Valor |
|---|---|
| Testes novos | 65 (todos TDD vermelho→verde; stories 02–04 casadas 1:1) |
| Suíte total | 177 passed (65 produto + 112 ai-dlc); ruff all checks passed; mypy app/ 0 erros |
| Ambiente | `.venv` local: ruff 0.16.5, mypy 2.3.1, pytest 9.1.1, pydantic, flask, pyyaml |
| Run AI-DLC | bolt-002-1: success em 1 iteração; N2 → `code_balanced` |
| Custo do run | executor 1245 tok US$0.000228 + crítico 13167 tok US$0.004797 ≈ **US$0.005** |
| Dependências novas | 0 (stdlib + pytest) |
| Atrito | ruído de sandbox no terminal satura a saída — resultado lido do audit JSONL (`runs.jsonl`), efeito colateral positivo da observabilidade |
| Confiança | alta — verify real (pytest), crítico independente com modelo forte, proposta fiel ao estado real |

## Pendências (humano)

1. Autorizar stage/commit/push e squash merge do PR (governança).
2. Bolt 002-2: ADR-005 + port/adapter Open-Meteo + seeds JSON + CLI
   `python -m app run` com `--offline` + relatório de rodada.
3. Bolt 002-3: LLM opcional (story 06) — checkpoint de dependência
   (pydantic-ai da decisão de inception vs openai já presente).
