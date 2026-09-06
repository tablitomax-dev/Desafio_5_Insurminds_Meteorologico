"""Testes do adapter Telegram Bot API — intent 004.

Contrato testado contra respostas gravadas (sem rede): sendMessage
envia por chat_id (nunca por telefone), degradação skipped/failed sem
quebrar a rodada, retry apenas para erro de rede e getUpdates
parseando contatos para o linking telefone → chat_id.
"""

import json
from urllib.error import HTTPError, URLError

import pytest

from app.adapters.telegram_api import (
    TelegramApiError,
    TelegramSender,
    fetch_recent_contacts,
)
from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import GeneratedMessage
from app.domain.risk import RiskKind
from app.domain.weather import GeoLocation

_OK = json.dumps({"ok": True, "result": {"message_id": 1}}).encode()


def _holder(chat_id: str = "123456789") -> PolicyHolder:
    return PolicyHolder(
        id="H001",
        name="Maria Silva",
        phone="+5511987650001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
        telegram_chat_id=chat_id,
    )


def _message() -> GeneratedMessage:
    return GeneratedMessage(
        holder_id="H001",
        alert_kind=RiskKind.HAIL,
        text="Olá, Maria! Granizo previsto.",
    )


def test_send_entrega_por_chat_id_e_retorna_sent():
    """Given token + chat_id vinculado, when send, then POST sendMessage
    com chat_id numérico e NotificationRecord 'sent'."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["url"] = url
        captured["payload"] = payload
        return _OK

    record = TelegramSender("T0K3N", post=post).send(_holder(), _message())

    assert captured["url"] == "https://api.telegram.org/botT0K3N/sendMessage"
    assert captured["payload"] == {
        "chat_id": 123456789,
        "text": "Olá, Maria! Granizo previsto.",
    }
    assert record.status == "sent"
    assert record.channel == "telegram"
    assert record.holder_id == "H001"
    assert record.detail == ""


def test_send_sem_token_e_skipped_sem_rede():
    """Given token vazio, when send, then 'skipped' sem chamada de rede
    (degradação — a rodada segue)."""

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API sem token")

    record = TelegramSender("", post=post).send(_holder(), _message())

    assert record.status == "skipped"
    assert "token" in record.detail


def test_send_sem_chat_id_e_skipped_sem_rede():
    """Given segurado sem chat_id, when send, then 'skipped' — o
    Telegram NÃO entrega por número de telefone."""

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API sem chat_id")

    record = TelegramSender("T0K3N", post=post).send(_holder(""), _message())

    assert record.status == "skipped"
    assert "chat_id" in record.detail


def test_chat_id_negativo_de_grupo_vira_int():
    """Given chat_id negativo (grupos/supergroups), when send, then
    payload com chat_id inteiro negativo."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["payload"] = payload
        return _OK

    TelegramSender("T0K3N", post=post).send(
        _holder("-100123456"), _message()
    )

    assert captured["payload"]["chat_id"] == -100123456


def test_erro_http_400_e_failed_sem_retry():
    """Given HTTPError 400 (determinístico), when send, then 'failed'
    em 1 tentativa — sem retry, mesmo contrato da BrasilAPI."""
    attempts: list[int] = []

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        attempts.append(1)
        raise HTTPError(url, 400, "Bad Request", None, None)  # type: ignore[arg-type]

    record = TelegramSender("T0K3N", post=post).send(_holder(), _message())

    assert len(attempts) == 1
    assert record.status == "failed"
    assert "HTTP 400" in record.detail


def test_ok_false_com_200_e_failed_sem_retry():
    """Given 200 com {"ok": false, "description": "chat not found"},
    when send, then 'failed' com a descrição em detail."""
    attempts: list[int] = []
    body = json.dumps({"ok": False, "description": "chat not found"}).encode()

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        attempts.append(1)
        return body

    record = TelegramSender("T0K3N", post=post).send(_holder(), _message())

    assert len(attempts) == 1
    assert record.status == "failed"
    assert "chat not found" in record.detail


def test_falha_de_rede_tem_retry_e_failed():
    """Given URLError, when retries esgotam, then 'failed' após
    retries + 1 tentativas."""
    attempts: list[int] = []

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        attempts.append(1)
        raise URLError("connection refused")

    record = TelegramSender(
        "T0K3N", post=post, retries=2, retry_delay_s=0.0
    ).send(_holder(), _message())

    assert len(attempts) == 3
    assert record.status == "failed"


def test_rede_instavel_recupera_e_envia():
    """Given 1ª tentativa com erro de rede e 2ª ok, when send, then
    'sent' (o retry de rede recupera a entrega)."""
    calls: list[int] = []

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        calls.append(1)
        if len(calls) == 1:
            raise URLError("transient")
        return _OK

    record = TelegramSender("T0K3N", post=post, retry_delay_s=0.0).send(
        _holder(), _message()
    )

    assert len(calls) == 2
    assert record.status == "sent"


def _updates_fixture() -> bytes:
    return json.dumps(
        {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "message": {
                        "chat": {"id": 42, "first_name": "Maria"},
                        "contact": {
                            "phone_number": "+5511987650001",
                            "first_name": "Maria",
                        },
                    },
                },
                {
                    "update_id": 2,
                    "message": {"chat": {"id": 42}, "text": "/start"},
                },
                {
                    "update_id": 3,
                    "message": {
                        "chat": {"id": 7, "first_name": "Joao"},
                        "text": "/start",
                    },
                },
            ],
        }
    ).encode()


def test_fetch_recent_contacts_parseia_e_deduplica():
    """Given getUpdates com contato compartilhado, /start repetido e
    /start sem contato, when fetch, then contatos deduplicados com
    preferência pelo que tem telefone."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["url"] = url
        captured["payload"] = payload
        return _updates_fixture()

    contatos = fetch_recent_contacts("T0K3N", post=post)

    assert captured["url"].endswith("/getUpdates")
    assert captured["payload"] == {"allowed_updates": ["message"]}
    assert len(contatos) == 2
    maria, joao = contatos
    assert maria.chat_id == "42"
    assert maria.phone == "+5511987650001"
    assert maria.is_contact_shared is True
    assert joao.chat_id == "7"
    assert joao.phone == ""
    assert joao.is_contact_shared is False


def test_fetch_sem_token_levanta_erro_sem_rede():
    """Given token vazio, when fetch_recent_contacts, then
    TelegramApiError sem chamada de rede (UI mostra aviso)."""

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API sem token")

    with pytest.raises(TelegramApiError, match="token"):
        fetch_recent_contacts("", post=post)
