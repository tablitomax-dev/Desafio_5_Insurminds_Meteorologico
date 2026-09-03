# Spec — 004-ai-dlc-phase2-real-executor (fase 2)

- **Tipo**: mudança isolada de 1 PR (rastreabilidade AI-DLC: spec curta + branch + PR)
- **Branch**: `chore/004-ai-dlc-phase2-real-executor`
- **Data**: 2026-09-03
- **Decisão**: ADR-006 (fase 2 executa o backlog dele — sem ADR novo)

## Contexto

Fase 1 (task 003) entregou roteamento/loop/gates com stubs determinísticos.
O `phase_2_backlog` da `ai-dlc-spec.yaml` definiu o próximo bolt. Escopo
ampliado pelo usuário (2026-09-03): dashboard, cost report e `.aiignore`
entram; Telegram é adiado para a fase 3.

## Objetivo

Tornar o orquestrador secundário **funcional de ponta a ponta**: executor e
crítico reais via OpenRouter, spec como fonte da verdade validada e
observabilidade (audit JSONL + dashboard + cost report).

## Escopo (fase 2)

- `openrouter_client.py`: transporte urllib stdlib (sem SDK), key de env ou
  registro HKCU (nunca impressa), `OpenRouterError`,
  `missing_credentials_decision()` canônica.
- `call_executor_llm_real` / `call_independent_critic_real`: interior real
  mantendo o contrato da fase 1; fns reais injetadas via `real_functions()`
  (stubs permanecem default — determinismo dos testes). Parse JSON
  tolerante (direto, cercado ```json, embutido em prosa).
- `spec_loader.py`: PyYAML; `check_consistency()` valida perfis/routing da
  spec contra o código; spec → v0.2.0 (`enabled: true`; Telegram → fase 3).
- `cost_report.py`: `generate_cost_report()` + `report_markdown()` a partir
  do `usage` dos records; contratos ganham `model/provider/usage` e
  `LoopResult.task_id` (aditivos).
- Auditoria: `run_loop(audit_path=...)` → 1 linha JSONL por run.
- `dashboard.py`: Flask (já presente no ambiente) com `/`, `/runs/<n>`,
  `/cost-report`; porta 5001.
- `.aiignore` na raiz (padrões da referência); `.gitignore` + `__pycache__/`
  e `tools/ai-dlc/runs.jsonl`.
- Suíte TDD: 56 testes novos (total 112).

## Fora de escopo (fase 3)

Telegram ("Grill Me"); `requirements-ai-dlc.txt` (manifest de deps —
pyyaml/flask/openai já instalados no ambiente; declarar após decisão
humana); CI de Python.

## Critérios de aceite

1. `python -m pytest tools/ai-dlc/tests -q` verde (112 testes).
2. Consistência spec↔código: `verify_spec_consistency() == []`.
3. Nenhuma dependência nova instalada (pyyaml/flask/openai já presentes).
4. Sem segredos no diff; key nunca impressa/gravada; `runs.jsonl` não
   versionado.
5. Smoke real opcional (executor + crítico) com custo mínimo.
6. Rastreabilidade: task spec 004 + keyword-index (3 keywords) +
   maintenance-log + `_index.csv`.
