# Intent 001 — repository-quality-foundation

> Status: `active` | Owner: pablo | Priority: P0 | Criado: 2026-08-25
>
> Contexto: intent piloto do AI-DLC — primeiro ciclo real
> Intent → Unit → Story → Bolt, limitado a governança verificável.

## Problema / capacidade

As regras de colaboração declaradas (CI verde, squash merge, contratos
multiagente) estão em documentos, mas não são verificáveis no GitHub.
O framework AI-DLC também nunca rodou um ciclo real — índices e
contratos ainda são hipóteses.

## Capacidade desejada

Tornar verificáveis no GitHub as regras já declaradas e validar o
fluxo AI-DLC com um ciclo pequeno, mensurável e real.

## Escopo

- CI mínimo real na branch `chore/ci-and-merge-governance`, gate de PR.
- Contratos canônicos multiagente na raiz (`AGENTS.md`, `CONTRIBUTING.md`).
- Correção da referência LRU → ADR (sem ADR artificial).
- Medições do piloto registradas no bolt.

## Fora de escopo

- Código de aplicação do desafio meteorológico (backend) — vem depois.
- LRU, operations obrigatório, CODEOWNERS, merge queue, automatização
  de índices.
- Mudanças na proteção de branch feitas por agente (humano só).

## Units

- `ci-and-merge-governance` (única; ver `units/`)

## Critérios de aceite do intent

1. Workflow CI existe, roda em PRs para `main` e há execução verde.
2. Check real marcado como obrigatório na proteção de `main` (humano).
3. Apenas squash merge habilitado (humano, Settings).
4. Contratos canônicos na raiz; `.trae/` vira ponte.
5. lru-policy.md sem referência semântica incorreta a ADR.
6. Medições do piloto registradas no bolt.
