# Intent 006 — telegram-links-sql

> Status: `done` (mudança isolada de 1 PR — mergeada no PR #16) | Owner:
> pablo | Priority: P1 | Criado: 2026-09-06
>
> Contexto: a intent 004 entregou o envio real via Telegram, com o
> chat_id lido do campo `telegram_chat_id` do segurado (bancada da UI).
> No teste real, os participantes deram /start SEM compartilhar contato
> → sem vínculo → envios `skipped`. Este intent move o vínculo
> telefone → chat_id para um banco SQLite consultado no envio e torna o
> Telegram o único canal da UI.

## Problema / capacidade

A vinculação dependia de (a) o segurado compartilhar o contato no bot e
(b) a banca copiar/conferir o chat_id manualmente na bancada. No teste
real ambos deram /start apenas — o chat apareceu no `getUpdates`, mas
sem `contact` não há match por telefone. O campo na UI também expõe
dado técnico (chat_id) à banca e não persiste entre sessões.

## Decisões (aprovadas pelo humano 2026-09-06)

| Decisão | Escolha | Registro |
|---|---|---|
| Persistência | **SQLite via stdlib `sqlite3`** (zero dependências): tabela `telegram_links(phone PK, chat_id, first_name, linked_at)` em `data/telegram_links.db` — FORA do Git (dados pessoais) | AskUserQuestion + plano |
| Resolução do destino | `TelegramSender` consulta o repositório por telefone (só dígitos) no momento do envio; campo `telegram_chat_id` REMOVIDO do domínio/catalogo/seeds | plano aprovado |
| Chats sem contato | No "Vincular contatos", o bot envia teclado "Compartilhar meu contato" (`reply_markup` com `request_contact`) para cada chat que deu /start sem telefone; ao tocar, o próximo clique vincula e grava | AskUserQuestion |
| Cadastro manual | NÃO — vinculação apenas automática (contato compartilhado/teclado) | AskUserQuestion |
| UI | Seletor "Envio" REMOVIDO (Telegram é o único canal da UI); coluna "Chat ID Telegram" REMOVIDA da bancada; CLI preserva o SMS simulado da story 07 | pedido do dono |

## Escopo (1 PR)

- `app/domain/ports.py`: port `TelegramLinkRepository`
  (`get_chat_id_by_phone` / `upsert_link`)
- `app/adapters/telegram_links_sqlite.py` (novo):
  `SqliteTelegramLinkRepository` (stdlib sqlite3, path injetável,
  normalização por dígitos, upsert idempotente)
- `app/adapters/telegram_api.py`: `TelegramSender(token, links=…)`
  consulta o repositório; nova `send_contact_request(token, chat_id)`
  (teclado `request_contact`); `fetch_recent_contacts` inalterado
- `app/composition.py`: `build_sender`/`run_proactive_round` recebem
  `link_repository` (default: o SQLite em `data/telegram_links.db`)
- `app/domain/holders.py` + `app/adapters/catalog.py` +
  `data/policy_holders.json`: campo `telegram_chat_id` removido
- `ui/demo_app.py`: só Telegram; sem coluna chat_id; "Vincular
  contatos" grava no SQL e pede contato via teclado para quem falta
- `.gitignore`: `data/*.db`
- Testes: repositório SQLite (upsert/get/normalização), sender com/sem
  vínculo via repo fake, teclado request_contact, composition com
  `link_repository`, catálogo sem o campo

## Fora de escopo

Cadastro manual phone→chat_id na UI (decisão do dono); outros bancos
(Postgres etc.); migração de schema; bot com webhook; exibição do
chat_id na UI.

## Critérios de aceite

1. [x] "Vincular contatos" grava phone→chat_id em `data/telegram_links.db` (fora do Git) para quem compartilhou o contato
2. [x] Chat que deu /start sem contato recebe o teclado "Compartilhar meu contato"; ao tocar, o próximo clique o vincula
3. [x] "Disparar Alertas" entrega a mensagem real consultando o banco (sem coluna chat_id na UI); sem vínculo → `skipped` com motivo, rodada intacta
4. [x] UI não tem seletor SMS nem coluna "Chat ID Telegram"; CLI preserva o SMS simulado da story 07
5. [x] `telegram_chat_id` não existe mais no domínio/seeds; `ruff`/`mypy app`/`pytest` verdes; token e DB nunca no repositório

Validação real (dono, 2026-09-06): teclado do bot recebido, contato
compartilhado, vínculo gravado no SQL e alertas entregues no Telegram
(3 envios reais recebidos). Observação pós-teste → intent 007
(consolidação em 1 mensagem por segurado).
