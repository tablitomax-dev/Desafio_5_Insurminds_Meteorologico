# Bolt — 001-bootstrap-ci-and-merge-governance

> Intent: 001-repository-quality-foundation | Unit: ci-and-merge-governance
> Stage: implementation | Status: `active` | Branch:
> `chore/ci-and-merge-governance` | Iniciado: 2026-08-25

## Plano (estágios TDD onde aplicável)

1. Spec-first: este intent/unit/stories definem o aceite antes do código.
2. Implementação: workflow CI + contratos raiz + fix LRU + fix package.json.
3. Validação: YAML do workflow válido; `npm ci` local; links de ponte
   funcionam; grep confirma ausência de referências quebradas.
4. Registro: execution-log com medições do piloto.

## Fontes carregadas nesta execução (declaração de contexto)

- Lido: `AGENTS.md` (raiz), `.trae/project_rules.md`, índices
  (`standards/_index.csv`, `intents/_index.csv` vazio, `bolts/_index.csv`
  vazio), `context-budget.yaml`, `git-and-collaboration.md`,
  diagnóstico externo (colado pelo usuário).
- NÃO lido nesta tarefa (sem necessidade): lru-policy integral
  (só seção Estado), system-architecture, coding-standards,
  tech-stack, operations/_index (vazio).

## Esclarecimentos pedidos ao humano (checkpoint protocol)

2 perguntas formais: (a) escopo da execução local, (b) sessão do piloto.
Autorizações: editar + commit na branch + push da branch.

## Inconsistências encontradas durante execução

- `package.json` com name/description do projeto antigo (`desafio-5-tempo`).
- `lru-policy.md` apontava ativação para "ADR-004" (que virou
  model-agnostic) — corrigido para "ADR específico futuro".

## Compact Summary (preencher ao concluir)

- Status: ativo — aguarda revisão humana, CI verde e opções de merge
  ajustadas na UI do GitHub (story-2).