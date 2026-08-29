# Unit — notification-sim

> Intent: 002-proactive-communication | Stage: infrastructure (simulação)
> Status: `planned`

## Objetivo

Simular o envio sem SMS/e-mail real: `NotificationSender` (Port) →
`SimulatedSender` grava cada despacho em `NotificationRecord(holder_id,
channel, message, sent_at, status)` exibindo no console como
"[SIMULADO] SMS → +55...: <mensagem>".

## Fatia técnica

- Port `NotificationSender` + impl `SimulatedSender` (console + lista em memória)
- `NotificationRecord` VO; consultável ao final do run (relatório)
- Estrutura pronta para trocar por provider real futuramente (port isolada)