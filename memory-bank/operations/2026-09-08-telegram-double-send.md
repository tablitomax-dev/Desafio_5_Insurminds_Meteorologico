# Incidente 2026-09-08 — envio duplicado de alerta via Telegram

| Campo | Valor |
|---|---|
| Data | 2026-09-08 (aproximada — semana da demo do intent 008) |
| Tipo | production_failure |
| Ambiente | envio real Telegram (UI demo) |
| Severidade | S2 (degrada — mesmo segurado recebeu o mesmo alerta 2×) |
| Linked PR | #18 (intent 008) |

## O que aconteceu

Durante a demonstração com envio real, o mesmo chat recebeu o mesmo alerta
preventivo mais de uma vez na mesma rodada.

## Impacto

Credibilidade do alerta preventivo (mensagem repetida parece spam/bot
quebrado); risco de desgaste do segurado com o canal.

## Causa raiz

Ausência de guard de deduplicação no disparo: nada impunha que um vínculo
telefone→chat recebesse o mesmo alerta 2× em uma rodada — lacuna de
processo/mecanismo, não de atenção.

## Ação tomada

Guard de duplo disparo implementado no adapter de envio (um envio por
vínculo na rodada), com testes — entregue no PR #18 (intent 008).

## Prevenção (mecanismo)

Teste de regressão do guard cobre a recorrência: qualquer alteração futura
no adapter que reintroduza o duplo envio quebra o CI. (Mecanismo análogo
generalizado no ai-dlc-kit: `secrets_scan`/gates de conteúdo.)
