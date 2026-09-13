# Execution Log — bolt 001-pre-merge-quality-repair

> Intent 001-repository-quality-foundation | 2026-09-04 (America/Sao_Paulo)
> Trabalho executado a partir da análise da spec `tools/ai-dlc/spec_pre_merge_quality_repair.md`.

| # | Etapa | Resultado |
|---|-------|-----------|
| 1 | Leitura calma da spec (926 linhas) + cruzamento com o estado real via API do GitHub | PRs #6/#7/#8 mergeados (squash); 0 checks; sem CI/branch protection |
| 2 | Regressão cp1252 confirmada em `main` (fix ficou preso na working tree, fora do commit do bolt 002-2) | bug mapeado |
| 3 | git: stash → checkout main → ff para 448861c → branch `fix/002-cp1252-console` → commit `d41a950` → push | PR 1 entregue |
| 4 | branch `chore/001-pre-merge-quality-repair` criada (recriada com `-B` sobre `main` após nascer errada do d41a950) | escopo isolado |
| 5 | `ci.yml`: bootstrap Node `--if-present` substituído por gates Python mandatários; `requirements-dev.txt` pinnado | gate de CI real |
| 6 | spec movida para `tools/ai-dlc/` + seção "Implementação neste repositório" + typo `invariável`→`invariante` | fonte canônica versionada |
| 7 | TDD: `test_pre_merge_check.py` (10 casos) escrito antes do código; vermelho confirmado (`ModuleNotFoundError: pre_merge_check`) | fase vermelha |
| 8 | `pre_merge_check.py` Fase 1 (state machine, classificação, decisão, artefatos por run_id) | verde: 10 passed |
| 9 | ajuste do teste de categorias (runner que falha lint + type_check simultaneamente) | 10/10 passed |
| 10 | Gate local completo: ruff `All checks passed!`; mypy `app/` 15 files; pytest 84; suíte ai-dlc 122 | verde |
| 11 | Smoke real do step read-only na branch | `approved_for_merge` (run `pmqr-20260904T231915Z-448861c`) |
| 12 | Orquestrador run 1: `blocked` — crítico REAL vetou por evidência insuficiente no estado (existência ≠ conteúdo) | honestidade do gate |
| 13 | Evidências consolidadas de arquivos reais (`gate_evidence.txt`) + suíte ai-dlc no `--tests-cmd`; orquestrador run 2 | `status=success`, crítico **accept** |
| 14 | memory-bank (bolt, índices, stories 1/2, maintenance-log) + commit + push | PR 2 entregue |

## Detalhes relevantes

- **Bug do sandbox** registrado: chamadas idênticas ao `run_bolt.py` oscilaram entre
  exit 1 com relatório completo e exit 0 com stdout completamente vazio (comando engolido).
  Fonte da verdade usada: `tools/ai-dlc/runs.jsonl` (audit) — o run "fantasma" não gravava
  linha, provando que não executou.
- **O crítico real funcionou como o design manda**: no run 1 vetou a iteração por
  "evidência de existência ≠ evidência de conteúdo" (pediu suíte ai-dlc, conteúdo do ci.yml,
  pins do requirements e resultado do smoke). A correção humana forneceu as evidências e o
  run 2 convergiu com `accept` — sem nenhum bypass.

## Decisões tomadas

1. Fix cp1252 independente do PR de governança (merge imediato).
2. Sem loop de reparo nesta fase — Fase 2 do step fica para bolt futuro.
3. Checks como comandos locais canônicos (source of truth = gate do repo).
4. Branch de governança pura a partir de `main` (sem carregar o fix).

## Medição (orquestrador, ADR-006)

- Run 1: `blocked` (stagnation) — US$0.006945 (1.534 executor + 17.042 crítico)
- Run 2: `success` / crítico `accept` — US$0.006960 (21.447 tokens)
- Total dos 2 runs: US$0.0139 — auditados em `runs.jsonl` (artefato local)

## Pendências humanas

1. Abrir e squash mergear os 2 PRs: **fix `d41a950` primeiro**, depois governança.
2. (Opcional) Marcar o check `CI / quality` como required nas branch rules do repo.
3. Compactação dos bolts 002 mergeados (dívida de manutenção do memory-bank).