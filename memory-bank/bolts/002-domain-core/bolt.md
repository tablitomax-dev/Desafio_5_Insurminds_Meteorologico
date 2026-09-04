# Bolt — 002-domain-core

> Intent: 002-proactive-communication | Unit: risk-detection (+
> message-generation, notification-sim) | Stage: implementation |
> Status: `active` | Branch: `feature/002-domain-core` | Iniciado: 2026-09-03

## Plano (TDD rigoroso, núcleo sem I/O)

1. Testes primeiro (vermelho): `tests/domain/` casando os
   given-when-then das stories 02–04 (regras P0/P1) e 05 (template).
2. Implementação: `app/domain/{weather,holders,risk,messages,notify}.py`
   — VOs WMO, entidade, motor de regras com dedup, template, envio
   simulado. Sem I/O, sem dependências novas.
3. Validação: pytest raiz verde + suíte ai-dlc (112) intacta; primeiro
   run REAL do orquestrador (fase 2) gateando o bolt.
4. Registro: bolt.md + execution-log + índices.

## Fontes carregadas nesta execução (declaração de contexto)

- Lido: `AGENTS.md`, `.trae/project_rules.md`, intent 002 (intent.md,
  story-index.md, 6 units), stories 02–05, `ci.yml`,
  `tools/ai-dlc/contracts.py`, `tools/ai-dlc/ai_dlc_orchestrator.py`,
  bolt 001 (formato), índices.
- NÃO lido (sem necessidade): stories 01/06/07 detalhadas (bolts 2–3),
  system-architecture, coding-standards (CI de Python é fase 3).

## Execução com o orquestrador AI-DLC (fase 2 — modo "run_loop completo por bolt")

- Runner novo: `tools/ai-dlc/run_bolt.py` — executor LLM recebe o
  estado objetivo real (saída do pytest, git status), `verify` injetado
  roda a suíte de verdade, crítico independente gateia, run auditado
  em `runs.jsonl` (dashboard).
- Modo de operação: iteração a iteração (`--max-iterations 1`,
  correção entre runs) — o loop não pausa entre iterações.
- Run do bolt (`bolt-002-1-domain-core`): **status=success em 1 iteração**
  (classificado N2 → `code_balanced`).
  - executor `z-ai/glm-5.3-flash` (GMICloud): 1245 tok, US$0.000228 —
    proposta fiel (evidenciou `65 passed`, critérios ✓ com evidências)
  - crítico `openai/gpt-5.6-luna-pro` (openai/flex): 13167 tok,
    US$0.004797 — **verdict accept** (stop rule satisfeita)
  - risk_notes do crítico: commit pendente (aguarda autorização
    humana) e revisão humana (acontece no PR)

## Compact Summary (preencher ao concluir)

- Núcleo de domínio 100% TDD: 65 testes novos (vermelho→verde), suíte
  total 177 passed; zero I/O; zero dependências novas no produto.
- Lint/tipo (autorização do usuário): `ruff.toml` versionado +
  `.venv` local — ruff all checks passed (repo inteiro), mypy `app/`
  0 erros; mypy `tools/ai-dlc` 25 apontamentos herdados (dívida CI
  Python, fase 3).
- stories 02–05 `done`; units atualizadas. Pendências: stage/commit/
  push/PR (humano); bolt 002-2 (ADR-005 + Open-Meteo + seeds + CLI
  `--offline`); bolt 002-3 (LLM opcional — checkpoint de dependência).
