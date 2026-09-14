# Incidente 2026-09-09 — token de Telegram inválido derrubava a rodada (InvalidURL)

| Campo | Valor |
|---|---|
| Data | 2026-09-09 (aproximada — semana da demo do intent 008) |
| Tipo | production_failure |
| Ambiente | envio real Telegram (adapter) |
| Severidade | S1 (bloqueava o disparo da rodada com exceção) |
| Linked PR | #18 (intent 008) |

## O que aconteceu

Um token colado com caractere/formato inválido gerava `InvalidURL` no
cliente HTTP no momento do envio — a exceção estourava no meio da rodada.

## Impacto

Rodada de alertas interrompida no envio real; mensagem de erro opaca
(URL do request aparecendo no traceback) em vez de degradação reportada.

## Causa raiz

O adapter confiava no formato do token e propagava a exceção de rede/URL
para cima — validação de entrada faltava na borda do sistema.

## Ação tomada

Validação do formato do token (padrão BotFather `<id>:<hash>`) na borda do
adapter + degradação reportada (`skipped` com motivo) em vez de exceção —
PR #18 (intent 008), coerente com ADR-008.

## Prevenção (mecanismo)

Testes do adapter cobrem token inválido ⇒ `skipped` com motivo, nunca
exceção para cima. Regra generalizada no ai-dlc-kit: validação na borda +
degradação auditável.
