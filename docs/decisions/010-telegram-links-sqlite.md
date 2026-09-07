# ADR-010: Vínculos Telegram em SQLite consultados no envio (intent 006)

- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (intent 006-telegram-links-sql, aprovada pelo dono)
- **Path**: `docs/decisions/010-telegram-links-sqlite.md` | `app/domain/ports.py` (`TelegramLinkRepository`) | `app/adapters/telegram_links_sqlite.py` | `app/adapters/telegram_api.py` (`send_contact_request`) | `app/composition.py`
- **Summary**: O vínculo telefone → chat_id sai do campo `telegram_chat_id` do segurado (UI/bancada, volátil) e passa a viver em **SQLite via stdlib `sqlite3`** (zero dependências — ADR-005/008): tabela `telegram_links(phone PK, chat_id, first_name, linked_at)` no arquivo `data/telegram_links.db`, **fora do versionamento** (dados pessoais). Nova port `TelegramLinkRepository`; `TelegramSender` consulta o repositório por telefone (só dígitos) no momento do envio — sem vínculo → `skipped` (degradação graciosa, ADR-008). Chats que deram /start sem compartilhar contato recebem o teclado **"Compartilhar meu contato"** (`reply_markup` com `request_contact`) — tocar no botão gera o update com telefone e o próximo "Vincular contatos" grava o vínculo. UI sem seletor de canal (Telegram único) e sem coluna de chat_id; CLI preserva o SMS simulado da story 07. Cadastro manual de vínculo rejeitado pelo dono (vinculação apenas automática).
- **Read when**: Ao implementar/alterar o linking Telegram, o repositório de vínculos, a resolução do destino de envio, ou ao avaliar mover os vínculos para outro banco.
