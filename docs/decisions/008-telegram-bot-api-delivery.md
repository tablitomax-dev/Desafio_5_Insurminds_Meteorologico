# ADR-008: Telegram Bot API como canal real de entrega (intent 004)

- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (intent 004-telegram-delivery, aprovada pelo dono via AskUserQuestion)
- **Path**: `docs/decisions/008-telegram-bot-api-delivery.md` | `app/adapters/telegram_api.py` | `app/domain/notify.py` (`NotificationRecord.detail`) | `app/composition.py` (`build_sender`)

## Contexto

O envio dos alertas era simulado (`SimulatedSender`, SMS fake — story 07).
O dono pediu a entrega REAL via Telegram para os segurados cadastrados.
Restrição da plataforma: a Telegram Bot API entrega mensagens por
`chat_id` — NUNCA por número de telefone — e somente para conversas já
iniciadas com o bot. O telefone dos seeds sozinho não basta.

## Decisão

1. **Adapter `TelegramSender`** implementa a port `NotificationSender`
   existente — o domínio e o pipeline não mudam de forma. Cliente stdlib
   urllib (ADR-005) com User-Agent próprio, timeout 10 s, retry apenas
   para erro de rede (2×/0.2 s) e 4xx sem retry (mesmo contrato da
   BrasilAPI — ADR-007). Payload JSON `{"chat_id": int, "text": str}` no
   endpoint `sendMessage`; chat_id numérico (usuário/grupo, inclusive
   negativo) vira int.
2. **Linking telefone → chat_id** pelo fluxo oficial: segurado manda
   `/start` no bot e compartilha o contato (`request_contact`);
   `fetch_recent_contacts` lê `getUpdates` e a UI casa o `phone_number`
   com o telefone da bancada (só dígitos), preenchendo a coluna
   `telegram_chat_id`. `/start` sem contato aparece na UI para cópia
   manual do chat_id.
3. **Token**: env `TELEGRAM_BOT_TOKEN` (contrato idêntico ao do gerador
   LLM) com campo secreto (`type=password`) na sidebar como conveniência
   da demo — nunca persistido, nunca no repositório. Parâmetro explícito
   vence env; campo vazio na UI cai para env.
4. **Degradação graciosa**: falha de entrega NUNCA quebra a rodada.
   Cada envio vira `NotificationRecord` com status `sent`, `failed`
   (erro da API/rede) ou `skipped` (sem token / segurado sem chat_id),
   com motivo em `detail` (campo novo, default `""`). O relatório
   textual reflete o canal real apenas quando não-SMS — o texto original
   da story 07 (`[SIMULADO]`, "Envios simulados") é preservado para o
   canal SMS/CLI.

## Consequências

- (+) Troca simulated→real por escolha explícita na UI/composition, sem
  tocar em regras; demo da banca mostra status real de entrega.
- (+) Sem credenciais novas no repo; token vive em env/sessão.
- (−) Chat_id exige interação do segurado com o bot (limitação da
  plataforma — mitigada pelo linking automático).
- (−) CEP/bot exigem internet; falhas degradam com aviso, nunca quebram.
- (−) `getUpdates` é polling simples — para produção real: webhook +
  persistência (candidato a intent futura).

## Alternativas consideradas

- **Enviar por telefone via provedor SMS real** (ex.: Twilio): exige
  conta paga/key — fora do escopo acadêmico da demo.
- **Webhook em vez de getUpdates**: exige URL pública/https — atrito de
  demo; getUpdates resolve o linking com o bot rodando localmente.
- **Mapear phone → chat_id automaticamente sem interação**: impossível —
  a plataforma não expõe chat_id sem o usuário iniciar a conversa.
