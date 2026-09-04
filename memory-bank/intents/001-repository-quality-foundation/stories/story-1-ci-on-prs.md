# Story — story-1-ci-on-prs

> Intent: 001-repository-quality-foundation | Unit: ci-and-merge-governance
> Status: `done` (CI Python obrigatória: ruff+mypy+pytest; gate ativo após merge do PR) | Prioridade: P0

## História

Como desenvolvedor, quero que todo PR para `main` execute uma validação
automática, para não depender apenas de revisão manual.

## Critérios de aceite (Given/When/Then)

- **Given** um PR aberto para `main`, **when** qualquer push na branch,
  **then** o workflow `CI / quality` roda e aparece no PR.
- **Given** o job concluído com sucesso, **then** há execução verde em
  GitHub Actions.
- **Given** o check publicado numa execução, **when** o humano o marcar
  como required, **then** PR sem check verde não pode ser mergeado.

## Notas

Upgrade bolt 001-pre-merge-quality-repair (2026-09-04): o bootstrap Node
`--if-present` foi removido e os gates Python agora são mandatários —
Lint: `ruff check .` (gate canônico `E4,E7,E9,F,I,B` do `ruff.toml`);
Type-check: `mypy app`; Unit tests: `pytest` — com `requirements-dev.txt`
pinnado. O check `CI / quality` roda em todo PR e push para `main`.
Step local read-only `tools/ai-dlc/pre_merge_check.py` (Fase 1 da spec
`spec_pre_merge_quality_repair.md`) valida os mesmos gates na working tree
antes de abrir o PR.