# Bolt — 001-pre-merge-quality-repair

> Intent: 001-repository-quality-foundation | Unit: ci-and-merge-governance
> Status: `active` (implementação concluída; aguardando squash merge dos 2 PRs)
> Prioridade: P0 | Data: 2026-09-04

## Objetivo

Fechar as lacunas de governança mapeadas na análise da spec
`tools/ai-dlc/spec_pre_merge_quality_repair.md` e aplicar as melhorias:

1. Corrigir regressão cp1252 em `main` (print ASCII-safe no `notify.py`) — branch de fix separada.
2. Tornar os checks de CI **mandatários em Python** (ruff/mypy/pytest),
   cumprindo a nota de honestidade de gate do bootstrap Node `--if-present`.
3. Implementar a **Fase 1** (`read_only_assess`) do step `pre_merge_quality_repair`:
   state machine mínima, classificação de falhas, decisão auditável e artefatos por `run_id`.
4. Versionar a spec do step e fixar a fonte de verdade das ferramentas (`requirements-dev.txt`).

## Plano TDD

1. [x] Diagnóstico do estado real do GitHub via API (PRs #6/#7/#8 mergeados; 0 checks; sem CI/branch protection).
2. [x] PR fix cp1252 (`fix/002-cp1252-console`, commit d41a950).
3. [x] `ci.yml` Python mandatário + `requirements-dev.txt` (ruff 0.16.5, mypy 2.3.1, pytest 9.1.1).
4. [x] Spec movida para `tools/ai-dlc/` + seção "Implementação neste repositório" + typo corrigido.
5. [x] TDD: 10 testes do step escritos antes do código (fase vermelha confirmada com `ModuleNotFoundError: pre_merge_check`).
6. [x] Gate local verde: ruff `All checks passed!`; mypy `app/` 15 files; pytest 84 passed; suíte ai-dlc 122 passed.
7. [x] Smoke real do step read-only: `approved_for_merge` com 4 artefatos (run `pmqr-20260904T231915Z-448861c`).

## Critérios de aceite

- [x] CI em Python com checks mandatários (bootstrap Node removido, 0 `--if-present`).
- [x] Step Fase 1 read-only: `prepare_context -> validate_quality -> decide`, decisão estruturada `approved_for_merge | blocked` (exit 0/1).
- [x] Artefatos por `run_id`: `pr_context.json`, `quality_report.initial.json`, `failure_report.attempt-1.json` (quando bloqueado), `final_decision.json`, `execution_log.md`.
- [x] Detecção e registro de stacked PR (`parent_branch`) no contexto.
- [x] Suítes verdes: 84 (produto) + 122 (ai-dlc completa).

## Decisões

- **Sem loop de reparo** nesta fase: o step observa, classifica e decide (Fase 2 fica para bolt futuro).
- **Checks como comandos locais canônicos**: a fonte da verdade é o gate do próprio repo
  (`ruff.toml`, `pytest.ini`, `ci.yml`), pois a plataforma ainda não tem checks/branch protection.
- **Fix cp1252 em PR separado** (`fix/002-cp1252-console`) para merge imediato e independente.
- **Branch de governança nascida de `main` pura** (`448861c`), sem carregar o diff do fix.

## Fontes carregadas

`spec_pre_merge_quality_repair.md` (integra), `story-1-ci-on-prs.md`, `ci.yml` (bootstrap anterior),
`ruff.toml`, `pytest.ini`, `run_bolt.py` (padrão de checks via subprocess + estado real).

## Orquestrador (AI-DLC, ADR-006)

- **Run 1** (2026-09-04): `status=blocked` (1 iteração, N2/code_balanced) — o crítico
  independente (gpt-5.6-luna-pro) **vetou** por evidência insuficiente no estado fornecido
  (existência ≠ conteúdo). Custo: US$0.0069.
- **Run 2** (correção humana: evidências consolidadas em `gate_evidence.txt` +
  suíte ai-dlc incluída no `--tests-cmd`): `status=success`, crítico **accept**.
  Custo: US$0.0070. Total dos 2 runs: **US$0.0139** (21.447 tokens).
- Auditoria: `tools/ai-dlc/runs.jsonl` (artefato local, não versionado).

## Compact Summary

**Entregue**: CI Python mandatária de PRs (ruff/mypy/pytest); step `pre_merge_check.py` Fase 1
(read_only_assess) com decisão auditável e artefatos por run_id; spec versionada com seção de
implementação; `requirements-dev.txt` pinnado; fix cp1252 em PR separado; `.gitignore` de runs.
**Qualidade**: ruff limpo; mypy app limpo (15 files); pytest 84 passed; ai-dlc 122 passed;
smoke real `approved_for_merge`.
**Decisões**: sem repair loop (Fase 2); commands locais como fonte de verdade; fix independente.
**Stories**: story-1 ci-on-prs elevada ao gate mandatário; story-2 squash-only `done` na prática
(PRs #6/#7/#8 squash + branch deletadas; formalização de branch protection pendente do admin).
**Próximo**: merge dos PRs (fix → governança); Fase 2 do step (classifier/repair loop pleno);
dívidas do intent 002 (story-06 LlmOptional) e compactação dos bolts 002 mergeados.