# Bolt — 002-domain-core

> Intent: 002-proactive-communication | Unit: risk-detection (+
> message-generation, notification-sim) | Stage: implementation |
> Status: `done` (squash merge no PR #6 → main) | Branch: `feature/002-domain-core` | Iniciado: 2026-09-03

## Plano (TDD rigoroso, núcleo sem I/O)

1. Testes primeiro (vermelho): `tests/domain/` casando os
   given-when-then das stories 02–04 (regras P0/P1) e 05 (template).
