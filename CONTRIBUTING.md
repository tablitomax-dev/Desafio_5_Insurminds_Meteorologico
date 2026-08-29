# Guia de colaboração (canônico)

> **Fonte canônica**: este arquivo na raiz vale para humanos e
> ferramentas. `.trae/CONTRIBUTING.md` é apenas uma ponte para cá.

## Objetivo

Este repositório é compartilhado por dois desenvolvedores humanos e
agentes de IA. GitHub é a fonte de verdade; a branch `main` deve
permanecer estável.

## Regras essenciais

- Nunca faça commit ou push direto para `main`.
- Toda mudança entra por Pull Request.
- Todo PR exige uma aprovação do outro desenvolvedor.
- CI obrigatório deve estar verde.
- Todas as conversas de review devem estar resolvidas.
- Use `Squash and merge`, salvo decisão explícita diferente.
- Nunca force push em `main`.
- Use o GitStudio para revisar histórico, branch, diffs e conflitos.

## Fluxo por tarefa

1. Criar ou escolher uma Issue.
2. Criar a spec em `docs/tasks/<issue>-<tema>.md` se necessário.
3. Atualizar `main`:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

4. Criar branch:

   ```bash
   git switch -c feature/<issue>-<tema>
   git push -u origin feature/<issue>-<tema>
   ```

5. Implementar em commits pequenos.
6. Executar testes e validar o diff.
7. Atualizar a branch antes do PR:

   ```bash
   git fetch origin
   git rebase origin/main
   ```

8. Resolver conflitos conscientemente e rodar testes novamente.
9. Abrir PR para `main`.
10. Receber revisão e aprovação.
11. Fazer squash merge.
12. Atualizar `main` local:

    ```bash
    git switch main
    git pull --ff-only origin main
    ```

## Convenções

### Branches

```text
feature/<issue>-<tema>
fix/<issue>-<tema>
refactor/<issue>-<tema>
docs/<issue>-<tema>
chore/<issue>-<tema>
```

### Commits

Conventional Commits:

```text
feat(catalog): add product creation endpoint
fix(auth): handle expired refresh token
test(checkout): cover invalid payment method
docs(api): document product payload
```

## Resolução de conflitos

- Não escolha automaticamente uma versão.
- Entenda a intenção de ambos os lados.
- Use o merge editor de três painéis do GitStudio.
- Peça à LLM uma explicação e proposta; a decisão final é humana.
- Rode validações depois da resolução.

## Worktrees

Use worktrees quando houver tarefas ou agentes paralelos na mesma
máquina. Um worktree é uma pasta separada ligada ao mesmo repositório,
com branch própria.

```bash
git fetch origin
git worktree add ../<projeto>-feature-<tema> -b feature/<issue>-<tema> origin/main
```

Nunca use dois agentes no mesmo diretório de trabalho.