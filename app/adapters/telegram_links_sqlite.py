"""Adapter SQLite do repositório de vínculos Telegram (intent 006).

Implementa a port `TelegramLinkRepository` com a stdlib `sqlite3`
(zero dependências novas — mesma disciplina dos demais adapters). O
arquivo de banco (`data/telegram_links.db`) contém dados pessoais
(telefone + chat_id) e NUNCA é versionado (`.gitignore`: `data/*.db`).

Telefones são normalizados para SÓ DÍGITOS na gravação e na consulta —
o Telegram envia E.164 (`+5511960628711`) e a bancada pode ter
formatação livre (`(11) 96062-8711`): o match é pelos dígitos.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB_PATH = Path("data") / "telegram_links.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS telegram_links (
    phone TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    linked_at TEXT NOT NULL
)
"""


def _digits(phone: str) -> str:
    """Normaliza telefone para só dígitos (match E.164 ↔ formatado)."""
    return "".join(ch for ch in str(phone) if ch.isdigit())


class SqliteTelegramLinkRepository:
    """Port `TelegramLinkRepository` em arquivo SQLite local."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def get_chat_id_by_phone(self, phone_digits: str) -> str | None:
        phone = _digits(phone_digits)
        if not phone:
            return None
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(_SCHEMA)
            row = conn.execute(
                "SELECT chat_id FROM telegram_links WHERE phone = ?",
                (phone,),
            ).fetchone()
        finally:
            conn.close()
        return str(row[0]) if row is not None else None

    def upsert_link(
        self, phone_digits: str, chat_id: str, first_name: str = ""
    ) -> None:
        phone = _digits(phone_digits)
        chat = str(chat_id).strip()
        if not phone or not chat:
            return  # nada a vincular (chamada defensiva: ignora)
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(_SCHEMA)
            conn.execute(
                "INSERT INTO telegram_links (phone, chat_id, first_name,"
                " linked_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(phone) DO UPDATE SET chat_id = excluded.chat_id,"
                " first_name = excluded.first_name,"
                " linked_at = excluded.linked_at",
                (phone, chat, str(first_name), datetime.now(UTC).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
