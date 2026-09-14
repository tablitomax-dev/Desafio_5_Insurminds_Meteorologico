# Incidente 2026-09-13 — PII real versionada em repositório público

| Campo | Valor |
|---|---|
| Data | 2026-09-13 (identificado na preparação da entrega) |
| Tipo | secret_exposure |
| Ambiente | GitHub público (tablitomax-dev/Desafio_5_Insurminds_Meteorologico) |
| Severidade | S1 |
| Linked PR | #19 (sanitização) |

## O que aconteceu

Dados pessoais reais do dono — telefone celular, chat_id de Telegram e
nome — estavam versionados em 3 arquivos de teste/docstring desde o intent
006, passando por todos os gates (ruff/mypy/pytest validam forma, nunca
conteúdo) e por revisão humana, em um repositório **público**.

## Impacto

PII acessível por qualquer um via histórico (`fe1a685` e anteriores,
diff do próprio commit de sanitização, `git show`).

## Causa raiz

Nenhum gate validava CONTEÚDO (só forma); fixtures de teste usavam dados
reais do dono em vez de sintéticos; `memory-bank/standards/` não definia
política de PII em fixtures.

## Ação tomada

Sanitização format-preserving no PR #19 (telefone `+5511900000000`,
chat_id `XXXXXXXXXX`/`1234567890`, seeds sintéticas mantidas); remoção
real de histórico avaliada (filter-repo + force-push + GitHub Support) e
não executada por custo/risco; mitigação recomendada ao dono: `/revoke`
do token no BotFather se algum token tenha sido versionado, e avaliar
tornar o repo privado.

## Prevenção (mecanismo)

Gate de conteúdo implementado no ai-dlc-kit (`secrets_scan.py`: token,
chave, celular BR, chat_id — com allowlist justificada), rodando local
(`gates.ps1`) e no CI; política: fixtures SEMPRE sintéticas.
