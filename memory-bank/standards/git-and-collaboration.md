# Padrões de Git e colaboração

version: 1.1.0
effective_date: 2026-08-25
owner: Master Agent (AI-DLC Option A)
status: required

---

## Política (este arquivo declara; não instrui passo a passo)

- **Fonte de verdade**: GitHub. `main` é protegida e só recebe mudanças via PR.
- Uma Issue/tarefa por branch. Nunca compartilhar branch entre pessoas/agentes.
- Todo PR exige **1 aprovação** de desenvolvedor diferente do autor; aprovações são invalidadas a cada novo push (dismiss stale).
- Status checks devem passar; conversas de review resolvidas; branch atualizada contra `main` antes do merge.
- Método de merge padrão: **squash merge** (política; os outros métodos do GitHub são exceção explícita, não rotina).
- Force push e bypass em `main`: proibidos (enforcement do GitHub aplica-se inclusive a admins).
- Agentes aguardam aprovação humana para qualquer operação Git de escrita.

## Separação de responsabilidades

| Camada | Onde | Papel |
|---|---|---|
| Declaração de política | `memory-bank/standards/git-and-collaboration.md` (este arquivo) | O que é obrigatório |
| Procedimento operacional | `.trae/CONTRIBUTING.md` | Comandos e sequência por tarefa |
| Enforcement | Branch protection do GitHub | O que é tecnicamente impossível burlar |

Se houver divergência entre política e procedimento, vale a política deste
arquivo e o CONTRIBUTING deve ser corrigido.

## Conflitos

Explicar a intenção de ambos os lados, resolver com o humano responsável e
executar testes após a resolução. Nunca escolher `ours`/`theirs` automaticamente.
