# Intent 004 — telegram-delivery

> Status: `in_progress` (mudança isolada de 1 PR em execução) | Owner: pablo |
> Priority: P1 | Criado: 2026-09-06
>
> Contexto: a intent 003 entregou a demo visual da banca (merge #13). Este
> intent leva o envio do SIMULADO ao REAL via Telegram Bot API — a port
> `NotificationSender` já isola a peça; nenhuma regra de negócio nova.

## Problema / capacidade

O envio de alertas é simulado (`SimulatedSender`, SMS fake). Para a banca,
a demo fica mais forte com entrega REAL via Telegram: o segurado recebe a
mensagem preventiva no celular. A plataforma Telegram entrega por
`chat_id` — nunca por número de telefone — e apenas para conversas já
iniciadas com o bot; o linking telefone → chat_id precisa nascer do fluxo
"/start + compartilhar contato".

## Decisões (aprovadas pelo humano 2026-09-06)

| Decisão | Escolha | Registro |
|---|---|---|
| Sequenciamento | Fechar a 003 primeiro (merge #13) e abrir branch nova `feature/004-telegram-delivery` | AskUserQuestion |
| Obtenção do chat_id | **Linking automático**: segurado manda /start e compartilha o contato (`request_contact`); botão "Vincular contatos" na UI casa o telefone da bancada via `getUpdates` | AskUserQuestion |
| Token do bot | env `TELEGRAM_BOT_TOKEN` + campo secreto (`type=password`) na sidebar da UI como conveniência (não persiste, não vai ao repo) | AskUserQuestion |
| Degradação | falha de entrega NUNCA quebra a rodada: `sent`/`failed`/`skipped` com motivo em `NotificationRecord.detail` (ADR-008) | AskUserQuestion |

## Escopo (1 PR)

- `app/adapters/telegram_api.py` (novo): `TelegramSender` (implementa a
  port `NotificationSender`) + `fetch_recent_contacts` (getUpdates para o
  linking); stdlib urllib com User-Agent próprio, timeout, retry só para
  erro de rede, 4xx sem retry (mesmo contrato da BrasilAPI), `post`
  injetável (testes sem rede); chat_id numérico (usuário/grupo, inclusive
  negativo) → int no payload
- `app/domain/notify.py`: `NotificationRecord.detail` (motivo de
  failed/skipped para UI/relatório; default `""` — sem quebra de
  contratos)
- `app/domain/holders.py` + `app/adapters/catalog.py` +
  `data/policy_holders.json`: campo `telegram_chat_id` (default `""`)
- `app/composition.py`: `build_sender(delivery, telegram_token)` —
  `simulated` | `telegram`; token explícito (UI) vence env
  `TELEGRAM_BOT_TOKEN` (mesmo contrato do gerador LLM);
  `run_proactive_round` expõe `delivery`/`telegram_token`
- `app/pipeline.py`: `format_report` reflete canal real quando não-SMS
  (texto original da story 07 preservado para o canal SMS/CLI)
- `ui/demo_app.py`: seletor "Envio" (Simulado default), campo secreto do
  token, coluna Chat ID na bancada, botão "Vincular contatos" (linking
  automático por telefone), cards mostram destino real e status
  (`sent`/`failed`/`skipped` + motivo)
- Testes TDD: `tests/adapters/test_telegram_api.py` (10) + composition
  (build_sender, rodada Telegram real com HTTP fake, skipped sem chat_id)
  + catálogo (telegram_chat_id)

## Fora de escopo

Scheduler/proatividade real (rodar sem clique); persistência de
chat_ids/tokens; SMS/WhatsApp real; fila com retry de entrega; webhook do
Telegram (usa `getUpdates` por simplicidade de demo).

## Critérios de aceite

1. [ ] Com bot criado no BotFather, quem mandou /start e compartilhou o contato aparece no "Vincular contatos" e o chat_id é preenchido na bancada
2. [ ] "Disparar Alertas" com Telegram entrega a mensagem real no chat vinculado (status `sent`)
3. [ ] Sem token ou sem chat_id: envio `skipped` com motivo; a rodada segue intacta (nunca quebra)
4. [ ] Canal Simulado (SMS) preserva comportamento e textos originais da CLI
5. [ ] `ruff` / `mypy app` / `pytest` verdes (133 testes); token nunca no repo
