# Unit — ci-and-merge-governance

> Intent: [001-repository-quality-foundation](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/intents/001-repository-quality-foundation/intent.md)
> Status: `in-execution` | Criada: 2026-08-25

## Objetivo

Tornar verificáveis no GitHub as regras já declaradas nos contratos:
CI executando em PRs, apenas squash merge, e contratos multiagente
canônicos na raiz — tudo entregue por um único bolt supervisionado.

## Fatia técnica entregável

1. `.github/workflows/ci.yml` (bootstrap: npm ci reproduzível; scripts
   `--if-present` até existirem comandos reais).
2. `AGENTS.md` e `CONTRIBUTING.md` canônicos na raiz; `.trae/` vira ponte.
3. `lru-policy.md` corrigido (referência semântica a ADR).
4. `package.json` renomeado (resto do projeto antigo).
5. Artefatos AI-DLC deste piloto + índices atualizados.

## Stories

- `story-1-ci-on-prs` — validação automática em todo PR para `main`.
- `story-2-squash-only` — `main` aceita apenas squash merge (ação UI humana).

## Critérios de aceite

Ver Intent (link acima) e bolt `001-bootstrap-ci-and-merge-governance`.