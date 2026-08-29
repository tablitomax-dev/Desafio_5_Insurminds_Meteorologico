# Instruções para agentes (canônico, multiagente)

> **Fonte canônica universal** de regras para QUALQUER agente de IA
> (Trae, GitStudio AI, MCP, outros). Ferramentas específicas não devem
> duplicar este arquivo — apenas apontar para ele. Adaptações por
> ambiente vivem em subpastas (ex.: `.trae/project_rules.md`).

## Missão

Trabalhar com segurança em um repositório compartilhado por dois
desenvolvedores humanos e múltiplos agentes de IA.

O projeto usa:
- GitHub como fonte de verdade e camada de governança
- GitStudio para contexto, histórico, diffs, branches e conflitos
- Trae para desenvolvimento assistido por IA
- AI-DLC para artefatos persistentes de requisitos, decisões e execução

## Hierarquia de contexto

Antes de qualquer alteração, leia nesta ordem:

1. Este arquivo (`AGENTS.md`)
2. `.trae/project_rules.md` (ou o equivalente da sua ferramenta)
3. `CONTRIBUTING.md`
4. `memory-bank/standards/` — índices primeiro (`standards/_index.csv`),
   depois apenas os standards required relevantes à tarefa
5. `docs/architecture.md`
6. A Issue, spec em `docs/tasks/` ou artefato em `memory-bank/intents/`
   relacionado à tarefa
7. Arquivos, testes, histórico e diffs diretamente envolvidos

Recupere contexto progressivamente (índices → seleção → conteúdo) —
não despeje o memory-bank inteiro em toda tarefa. Declare quais fontes
foram carregadas e quais não foram. Se houver conflito entre
instruções, pare e peça orientação humana.

## Protocolo obrigatório antes de editar

Execute e informe o resultado resumido:

```bash
git status
git branch --show-current
git remote -v
git diff
```

Depois:

- Confirme que a branch atual não é `main`.
- Identifique alterações locais que não foram feitas nesta sessão.
- Não sobrescreva, descarte, mova, reverta, faça stash ou commite alterações
  do usuário ou de outro agente.
- Leia a spec e os padrões relevantes.
- Apresente um plano curto, contendo: objetivo; arquivos a criar e alterar;
  risco de conflito com outras áreas; testes e validações esperados.
- Aguarde autorização explícita para editar.

## Regras absolutas de Git

### Proibido

- Trabalhar, commitar, enviar ou fazer merge diretamente em `main`.
- Executar `git push --force` ou `git push --force-with-lease` em `main`.
- Executar `git reset --hard`, `git clean -fd`, `git branch -D` ou comandos
  destrutivos sem autorização explícita.
- Executar merge, rebase, cherry-pick, pull, push, stash, troca de branch,
  criação de branch ou alteração de remote sem autorização explícita.
- Fazer merge ou aprovar Pull Requests.
- Desativar proteções de branch, CI, checks ou regras do GitHub.
- Resolver conflitos escolhendo automaticamente apenas "ours" ou "theirs".
- Alterar `.env`, chaves, tokens, credenciais, dados pessoais ou segredos.
- Incluir segredos, artefatos gerados, dumps, logs ou dependências
  vendorizadas em commits.

### Permitido sem nova autorização

- `git status`, `git diff`, `git log`, `git show`, `git blame`,
  `git branch --show-current`, `git remote -v`, `git fetch origin`.
- Ler código, documentação, specs, histórico e configurações.
- Executar testes, lint, type-check e build já definidos no projeto,
  desde que não alterem ambiente, dependências ou infraestrutura.
- Propor planos, diffs, mensagens de commit, descrições de PR e resoluções
  de conflito, sem aplicá-los.

## Branches e escopo

- Uma branch representa uma única Issue/tarefa.
- Formatos permitidos:
  - `feature/<issue>-<tema>`
  - `fix/<issue>-<tema>`
  - `refactor/<issue>-<tema>`
  - `docs/<issue>-<tema>`
  - `chore/<issue>-<tema>`
- Não faça refactors amplos ou mudanças cosméticas fora do escopo.
- Antes de tocar em arquivos compartilhados ou críticos, avise:
  manifests e lockfiles; configuração de build, deploy, CI e
  infraestrutura; autenticação e segredos; schemas, migrations e
  contratos públicos; `.github/`; `docs/architecture.md`;
  `memory-bank/standards/`.

## Escopo de rastreabilidade AI-DLC

Nem todo trabalho precisa do ciclo completo. Classifique antes de criar artefatos:

| Trabalho | Obrigatório | Opcional |
|---|---|---|
| Pergunta/diagnóstico sem mudança | nada | nada |
| Bug pequeno (≈ 1 PR) | Issue + branch + PR | intent/bolt se recorrente |
| Mudança isolada de 1 PR | Issue + spec curta + branch + PR | intent, bolt |
| Feature com múltiplas units | Intent + stories + units + story-index do intent | resumo compacto |
| Execução de unit relevante (construction) | Bolt + bolts/_index.csv | operations |
| Deploy/incidente/migração | registro em operations/ | compact summary |
| Decisão arquitetural duradoura | ADR + decision-index | keywords |
| Qualquer mudança para `main` | branch + PR | — |

## Ciclo de execução

1. Inspecionar contexto (índices → seleção) e confirmar escopo.
2. Propor plano com formato de resposta definido.
3. Aguardar autorização.
4. Fazer uma mudança pequena e focada.
5. Rodar validações relevantes.
6. Revisar o diff.
7. Informar: arquivos alterados; comportamento modificado; testes e
   resultados (executado/aprovado, executado/falhou, não executado);
   riscos, limitações e próximos passos.
8. Aguardar autorização antes de stage, commit ou push.

## Testes e qualidade

- Toda alteração de comportamento deve incluir ou atualizar testes.
- Rode a menor validação adequada primeiro; depois a suíte relevante.
- Não declare sucesso se comandos falharem, forem ignorados ou não existirem.

## Conflitos

1. Pare a edição autonômica.
2. Liste os arquivos conflitados.
3. Explique a intenção da mudança local e da remota.
4. Proponha composição que preserve os dois comportamentos quando possível.
5. Informe testes necessários; aguarde aprovação humana antes de editar
   o resultado.

## AI-DLC e memória persistente

- Registre decisões arquiteturais duradouras em `docs/decisions/`
  (imutáveis; revisões criam novo ADR com `supersedes`).
- Atualize padrões em `memory-bank/standards/` apenas após decisão humana.
- Features relevantes: spec em `docs/tasks/` e/ou artefato em
  `memory-bank/intents/`.
- Execução relevante: `memory-bank/bolts/`.
- Atualize `last_touched_at` nos índices apenas por alteração material
  (reformatação ou typo não reclassifica recência).
- `keyword-index.md`: atualize somente quando surgir vocabulário estável
  novo (bounded context, agregado, padrão, mecanismo, ADR, integração).
- Não invente requisitos, decisões ou documentação: marque dúvidas e peça
  esclarecimentos.

## Commits e Pull Requests

- Somente commite, faça push ou abra/atualize PR com autorização humana.
- Antes de commit, apresente `git diff --staged` e valide o escopo.
- Use Conventional Commits (`feat|fix|refactor|test|docs|chore`).
- Antes de propor PR, confirme: branch atualizada contra `main`;
  CI/testes relevantes aprovados; diff limitado à tarefa; documentação
  atualizada quando necessária; ausência de segredos e arquivos indevidos.