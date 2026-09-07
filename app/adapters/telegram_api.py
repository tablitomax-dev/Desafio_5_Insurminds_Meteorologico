"""Adapter Telegram Bot API — envio real dos alertas (intents 004/006).

Implementa a port `NotificationSender` (app.domain.notify). A API do
Telegram entrega mensagens por `chat_id` — NUNCA por número de
telefone — e somente para conversas já iniciadas com o bot. O vínculo
telefone → chat_id nasce quando o segurado manda /start no bot e
compartilha o contato (`fetch_recent_contacts` lê `getUpdates`) e é
PERSISTIDO no repositório `TelegramLinkRepository` (SQLite — intent
006): no envio, o chat_id é resolvido por telefone no banco, sem campo
na UI. Para chats que só mandaram /start, `send_contact_request` envia
o teclado "Compartilhar meu contato" (`request_contact`) — tocar no
botão gera o update com telefone e o próximo linking grava o vínculo.

Degradação graciosa (ADR-008): falha de entrega NUNCA quebra a rodada —
cada `send` vira um `NotificationRecord` com status "sent", "failed"
(erro da API/rede) ou "skipped" (sem token / telefone sem vínculo), e o
motivo vai em `detail` para o relatório. Token via env
TELEGRAM_BOT_TOKEN ou campo secreto da UI; NUNCA no repositório.
Mesma disciplina da BrasilAPI: User-Agent próprio, timeout, retry
apenas para erro de rede e `post` injetável para testes sem rede.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.domain.holders import PolicyHolder
from app.domain.messages import GeneratedMessage
from app.domain.notify import NotificationRecord
from app.domain.ports import TelegramLinkRepository

API_BASE = "https://api.telegram.org/bot"
_USER_AGENT = "insurminds-meteorologico-demo/1.0 (desafio I2A2)"
_FETCH_TIMEOUT_S = 10.0
_DEFAULT_RETRIES = 2
_RETRY_DELAY_S = 0.2
_CHAT_ID_RE = re.compile(r"-?\d+")


class TelegramApiError(RuntimeError):
    """Erro da Telegram Bot API (HTTP/JSON) — degrada, não quebra a rodada."""


class _HttpPostFn(Protocol):
    """Assinatura do POST injetável (testes sem rede)."""

    def __call__(
        self, url: str, payload: dict[str, Any], timeout_s: float
    ) -> bytes: ...


def _http_post_json(
    url: str, payload: dict[str, Any], timeout_s: float
) -> bytes:
    """POST JSON com User-Agent próprio (mesmo cuidado da BrasilAPI)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return response.read()


@dataclass(frozen=True)
class TelegramContact:
    """Contato visto no bot via getUpdates (linking telefone → chat_id)."""

    chat_id: str
    first_name: str
    phone: str  # vazio quando o segurado só mandou /start (sem contato)
    is_contact_shared: bool


def _parse_chat_id(chat_id: str) -> int | str:
    """chat_id numérico (usuário/grupo — pode ser negativo) vira int;
    nomes de canal (@...) seguem como string."""
    texto = chat_id.strip()
    if _CHAT_ID_RE.fullmatch(texto):
        return int(texto)
    return texto


class _TelegramClient:
    """Cliente Bot API mínimo: retry de rede, erros 4xx sem retry."""

    def __init__(
        self,
        token: str,
        *,
        post: _HttpPostFn | None = None,
        retries: int = _DEFAULT_RETRIES,
        retry_delay_s: float = _RETRY_DELAY_S,
    ) -> None:
        self.token = token
        # Resolvido em runtime (não como default da assinatura) para que
        # o monkeypatch de _http_post_json funcione via composition.
        self._post = post if post is not None else _http_post_json
        self.retries = retries
        self.retry_delay_s = retry_delay_s

    def call(self, method: str, payload: dict[str, Any]) -> Any:
        url = f"{API_BASE}{self.token}/{method}"
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                raw = self._post(url, payload, _FETCH_TIMEOUT_S)
                data = json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                # 4xx é determinístico (401 token inválido, 400 chat
                # not found) — sem retry, mesmo contrato da BrasilAPI.
                raise TelegramApiError(
                    f"{method}: HTTP {exc.code} da Telegram Bot API"
                ) from exc
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                UnicodeDecodeError,
            ) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_delay_s)
                continue
            if not data.get("ok"):
                # A API responde 200 com {"ok": false, "description": ...}
                # para erros de uso (ex.: "chat not found") — sem retry.
                description = str(data.get("description") or "resposta not ok")
                raise TelegramApiError(f"{method}: {description}")
            return data.get("result", {})
        raise TelegramApiError(
            f"{method}: falha de rede após {self.retries + 1} tentativas"
            f" ({last_error})"
        )


class TelegramSender:
    """Envio real via Telegram (port NotificationSender — intents 004/006).

    - sem token: todo envio vira "skipped" (nenhuma chamada de rede);
    - telefone sem vínculo no repositório: "skipped" — Telegram não
      entrega por telefone; o vínculo nasce do /start + contato
      compartilhado (ou do teclado `send_contact_request`) e fica
      gravado no `TelegramLinkRepository`;
    - erro de API/rede: "failed" com o motivo em `detail`.
    """

    def __init__(
        self,
        token: str = "",
        *,
        links: TelegramLinkRepository,
        post: _HttpPostFn | None = None,
        retries: int = _DEFAULT_RETRIES,
        retry_delay_s: float = _RETRY_DELAY_S,
    ) -> None:
        self.token = (token or "").strip()
        self._links = links
        self._client = _TelegramClient(
            self.token, post=post, retries=retries, retry_delay_s=retry_delay_s
        )

    def send(
        self, holder: PolicyHolder, message: GeneratedMessage
    ) -> NotificationRecord:
        if not self.token:
            return NotificationRecord(
                holder_id=holder.id,
                channel="telegram",
                message=message.text,
                sent_at=datetime.now(UTC),
                status="skipped",
                detail="token do bot ausente (TELEGRAM_BOT_TOKEN)",
            )
        phone_digits = "".join(ch for ch in holder.phone if ch.isdigit())
        chat_id = self._links.get_chat_id_by_phone(phone_digits) or ""
        if not chat_id:
            return NotificationRecord(
                holder_id=holder.id,
                channel="telegram",
                message=message.text,
                sent_at=datetime.now(UTC),
                status="skipped",
                detail="telefone sem vínculo no bot — segurado precisa"
                " mandar /start e compartilhar o contato",
            )
        try:
            self._client.call(
                "sendMessage",
                {"chat_id": _parse_chat_id(chat_id), "text": message.text},
            )
        except TelegramApiError as exc:
            return NotificationRecord(
                holder_id=holder.id,
                channel="telegram",
                message=message.text,
                sent_at=datetime.now(UTC),
                status="failed",
                detail=str(exc),
            )
        return NotificationRecord(
            holder_id=holder.id,
            channel="telegram",
            message=message.text,
            sent_at=datetime.now(UTC),
            status="sent",
        )


def send_contact_request(
    token: str,
    chat_id: str,
    *,
    post: _HttpPostFn | None = None,
    retries: int = _DEFAULT_RETRIES,
    retry_delay_s: float = _RETRY_DELAY_S,
) -> None:
    """Envia o teclado "Compartilhar meu contato" (`request_contact`).

    Para chats que deram /start SEM compartilhar o telefone (intent
    006): tocar no botão gera um update com `contact` — o próximo
    "Vincular contatos" grava o vínculo no repositório. Erros de API
    propagam como `TelegramApiError` (chamador decide a degradação).
    """
    client = _TelegramClient(
        (token or "").strip(),
        post=post,
        retries=retries,
        retry_delay_s=retry_delay_s,
    )
    if not client.token:
        raise TelegramApiError("sendMessage: token do bot ausente")
    client.call(
        "sendMessage",
        {
            "chat_id": _parse_chat_id(chat_id),
            "text": (
                "Toque no botão abaixo para compartilhar seu contato e"
                " receber os alertas meteorológicos."
            ),
            "reply_markup": {
                "keyboard": [
                    [
                        {
                            "text": "📱 Compartilhar meu contato",
                            "request_contact": True,
                        }
                    ]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            },
        },
    )


def fetch_recent_contacts(
    token: str,
    *,
    post: _HttpPostFn | None = None,
    retries: int = _DEFAULT_RETRIES,
    retry_delay_s: float = _RETRY_DELAY_S,
) -> list[TelegramContact]:
    """Contatos/starts recentes no bot (getUpdates) — linking da UI.

    Update com contato compartilhado traz `phone` (E.164 do Telegram);
    /start sem contato entra com `phone=""` — a banca pode copiar o
    chat_id manualmente na bancada. Updates do mesmo chat são
    deduplicados, com preferência pelo que tem telefone.
    """
    client = _TelegramClient(
        (token or "").strip(),
        post=post,
        retries=retries,
        retry_delay_s=retry_delay_s,
    )
    if not client.token:
        raise TelegramApiError("getUpdates: token do bot ausente")
    updates = client.call("getUpdates", {"allowed_updates": ["message"]})
    if not isinstance(updates, list):
        raise TelegramApiError("getUpdates: formato inesperado da resposta")
    contatos: dict[str, TelegramContact] = {}
    for update in updates:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not chat_id:
            continue
        contact = message.get("contact") or {}
        phone = str(contact.get("phone_number") or "")
        name = str(contact.get("first_name") or chat.get("first_name") or "")
        novo = TelegramContact(
            chat_id=chat_id,
            first_name=name,
            phone=phone,
            is_contact_shared=bool(phone),
        )
        anterior = contatos.get(chat_id)
        if anterior is None or (
            novo.is_contact_shared and not anterior.is_contact_shared
        ):
            contatos[chat_id] = novo
    return list(contatos.values())
