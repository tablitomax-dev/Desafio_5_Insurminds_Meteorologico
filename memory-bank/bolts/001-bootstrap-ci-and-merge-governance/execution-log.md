# Execution Log — 001-bootstrap-ci-and-merge-governance

Registro cronológico (mais recente primeiro).

---

## [2026-08-25] Execução — implementação do unit (TDD adaptado):

| Estágio | Ação | Resultado |
|---|---|---|
| spec-first | intent.md + unit + 2 stories criados ANTES do código | ✅ |
| impl | `lru-policy.md` corrigido (Opção A — experimental/desativada + ADR específico) | ✅ |
| impl | `AGENTS.md` e `CONTRIBUTING.md` canônicos na raiz; pontes em `.trae/` (cópia zero) | ✅ |
| impl | `package.json` renomeado (resto `desafio-5-tempo`) | ✅ |
| impl | `.github/workflows/ci.yml` bootstrap `honesto` (npm ci real; scripts `--if-present`) | ✅ |
| índices | intents/_index.csv, bolts/_index.csv, standards (last_touched), keyword-index (2 keywords novas), story-index raiz | ✅ |
| validação | YAML conferido; greps de referências quebradas agendados pré-commit | ⏳ |
| entrega | commit único na branch + push; PR a ser aberto pelo humano (sem token de admin/PR) | ⏳ |

## Medição do piloto (o objetivo real deste bolt)

| Métrica | Valor |
|---|---|
| Documentos lidos para a tarefa | 7 (AGENTS raiz criado nesta execução contando como fonte; índices 3; contexto-budget; git-and-collaboration; diagnóstico externo) |
| Documentos evitados conscientemente | 4 (system-architecture, coding-standards, tech-stack, operations/_index) |
| Esclarecimentos formais pedidos | 2 (escopo de execução; sessão do piloto) |
| Regras contraditórias/duplicadas encontradas | 2 (package.json com nome antigo; LRU→ADR-004 incorreto) — corrigidas |
| Arquivos atualizados de índice nesta tarefa pequena | 4 (sinal de alerta: somente aceitável porque a tarefa CRIA artefatos; política de escopo do AGENTS.md agora limita isso) |
| Atrito principal | commits anteriores em `main` direto (bootstrap) divergem da política — este PR é a correção do processo |
| Confiança no registro | alta; pendências de conclusão dependem de ação humana na UI do GitHub |

## Pendências de conclusão (humano)

1. Abrir PR da branch `chore/ci-and-merge-governance` → `main`.
2. Ver execução verde do workflow no PR.
3. Marcar `CI / quality` como required status check na proteção de `main`.
4. Settings → Pull Requests: somente squash + auto-delete head branches.
5. Criar a Issue correspondente e editar o PR para `Closes #<n>`.
6. Revisão/aprovação do parceiro → squash merge.