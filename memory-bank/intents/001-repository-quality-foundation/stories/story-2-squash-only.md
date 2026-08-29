# Story — story-2-squash-only

> Intent: 001-repository-quality-foundation | Unit: ci-and-merge-governance
> Status: `pending` — AÇÃO HUMANA na UI do GitHub | Prioridade: P0

## História

Como revisor, quero que `main` aceites apenas squash merge, para que o
histórico principal permaneça linear e legível.

## Critérios de aceite

- Settings → General → Pull Requests:
  - Allow merge commits: **OFF**
  - Allow squash merging: **ON**
  - Allow rebase merging: **OFF**
  - Automatically delete head branches: **ON**

## Notas

Impossível de fazer por agente (requer admin na UI). Não é código.