"""Testes do adapter Telegram Bot API — intents 004/006.

Contrato testado contra respostas gravadas (sem rede): sendMessage
envia por chat_id resolvido NO REPOSITÓRIO de vínculos (nunca por
telefone), degradação skipped/failed sem quebrar a rodada, retry apenas
para erro de rede, teclado request_contact para quem não compartilhou
o contato e getUpdates parseando contatos para o linking.
"""

import json
from urllib.error import HTTPError, URLError

import pytest

from app.adapters.telegram_api import (
    TelegramApiError,
    TelegramSender,
    fetch_recent_contacts,
    send_contact_request,
)
from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import GeneratedMessage
from app.domain.risk import RiskKind
from app.domain.weather import GeoLocation

_OK = json.dumps({"ok": True, "result": {"message_id": 1}}).encode()


class _RepoFake:
    """Fake do TelegramLinkRepository (mapa telefone → chat_id)."""

    def __init__(self, mapping: dict[str, str] | None = None):
        self._mapping = dict(mapping or {})

    def get_chat_id_by_phone(self, phone_digits: str) -> str | None:
        return self._mapping.get(phone_digits)

    def upsert_link(
        self, phone_digits: str, chat_id: str, first_name: str = ""
    ) -> None:
        self._mapping[phone_digits] = chat_id


def _holder() -> PolicyHolder:
    """Segurado SEM chat_id — o destino vem do repositório (intent 006)."""
    return PolicyHolder(
        id="H001",
        name="Maria Silva",
        phone="+5511987650001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
    )


def _message() -> GeneratedMessage:
    return GeneratedMessage(
        holder_id="H001",
        alert_kind=RiskKind.HAIL,
        text="Olá, Maria! Granizo previsto.",
    )


def test_send_entrega_por_chat_id_do_repo_e_retorna_sent():
    """Given token + vínculo no repo (telefone → chat_id), when send,
    then POST sendMessage com chat_id numérico e NotificationRecord
    'sent' — o holder NÃO carrega chat_id."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["url"] = url
        captured["payload"] = payload
        return _OK

    repo = _RepoFake({"5511987650001": "123456789"})
    record = TelegramSender("123456:T0K3N", links=repo, post=post).send(
        _holder(), _message()
    )

    assert captured["url"] == "https://api.telegram.org/bot123456:T0K3N/sendMessage"
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

    record = TelegramSender("", links=_RepoFake(), post=post).send(
        _holder(), _message()
    )

    assert record.status == "skipped"
    assert "token" in record.detail


def test_send_token_invalido_e_skipped_sem_rede():
    """Given token inválido (texto colado no campo da UI), when send,
    then 'skipped' sem chamada de rede e SEM http.client.InvalidURL —
    o token fora do formato <id>:<hash> é rejeitado antes da URL."""
    texto_colado = (
        "Pablo, alerta preto: aja imediatamente. Chuva intensa (12 mm/h)."
    )

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API com token inválido")

    record = TelegramSender(texto_colado, links=_RepoFake(), post=post).send(
        _holder(), _message()
    )

    assert record.status == "skipped"
    assert "token" in record.detail
    assert "inválido" in record.detail


def test_send_sem_vinculo_no_repo_e_skipped_sem_rede():
    """Given telefone sem vínculo no repositório, when send, then
    'skipped' — o Telegram NÃO entrega por número de telefone."""

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API sem vínculo")

    record = TelegramSender("123456:T0K3N", links=_RepoFake(), post=post).send(
        _holder(), _message()
    )

    assert record.status == "skipped"
    assert "vínculo" in record.detail


def test_chat_id_negativo_de_grupo_vira_int():
    """Given chat_id negativo (grupos/supergroups) no repo, when send,
    then payload com chat_id inteiro negativo."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["payload"] = payload
        return _OK

    repo = _RepoFake({"5511987650001": "-100123456"})
    TelegramSender("123456:T0K3N", links=repo, post=post).send(
        _holder(), _message()
    )

    assert captured["payload"]["chat_id"] == -100123456


def test_telefone_formatado_casa_pelos_digitos():
    """Given vínculo gravado por dígitos e holder com telefone formatado,
    when send, then o match é normalizado (intent 006)."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["payload"] = payload
        return _OK

    repo = _RepoFake({"5511987650001": "999"})
    holder = PolicyHolder(
        id="H001",
        name="Maria Silva",
        phone="+55 (11) 98765-0001",  # formatação livre na bancada
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
    )
    TelegramSender("123456:T0K3N", links=repo, post=post).send(holder, _message())

    assert captured["payload"]["chat_id"] == 999


def test_erro_http_400_e_failed_sem_retry():
    """Given HTTPError 400 (determinístico), when send, then 'failed'
    em 1 tentativa — sem retry, mesmo contrato da BrasilAPI."""
    attempts: list[int] = []

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        attempts.append(1)
        raise HTTPError(url, 400, "Bad Request", None, None)  # type: ignore[arg-type]

    record = TelegramSender(
        "123456:T0K3N", links=_RepoFake({"5511987650001": "1"}), post=post
    ).send(_holder(), _message())

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

    record = TelegramSender(
        "123456:T0K3N", links=_RepoFake({"5511987650001": "1"}), post=post
    ).send(_holder(), _message())

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
        "123456:T0K3N",
        links=_RepoFake({"5511987650001": "1"}),
        post=post,
        retries=2,
        retry_delay_s=0.0,
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

    record = TelegramSender(
        "123456:T0K3N",
        links=_RepoFake({"5511987650001": "1"}),
        post=post,
        retry_delay_s=0.0,
    ).send(_holder(), _message())

    assert len(calls) == 2
    assert record.status == "sent"


def test_send_contact_request_envia_teclado_request_contact():
    """Given chat que só mandou /start, when send_contact_request, then
    sendMessage com reply_markup keyboard request_contact (intent 006)."""
    captured: dict = {}

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        captured["url"] = url
        captured["payload"] = payload
        return _OK

    send_contact_request("123456:T0K3N", "1234567890", post=post)

    assert captured["url"].endswith("/sendMessage")
    assert captured["payload"]["chat_id"] == 1234567890
    keyboard = captured["payload"]["reply_markup"]["keyboard"]
    assert keyboard[0][0]["request_contact"] is True
    assert "contato" in captured["payload"]["text"]


def test_send_contact_request_sem_token_levanta_erro():
    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API sem token")

    with pytest.raises(TelegramApiError, match="token"):
        send_contact_request("", "42", post=post)


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

    contatos = fetch_recent_contacts("123456:T0K3N", post=post)

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


def test_fetch_token_invalido_levanta_erro_sem_rede():
    """Given token inválido (fora do formato <id>:<hash>), when
    fetch_recent_contacts, then TelegramApiError SEM rede — nunca
    http.client.InvalidURL (a UI mostra aviso amigável)."""

    def post(url: str, payload: dict, timeout_s: float) -> bytes:
        raise AssertionError("não deveria chamar a API com token inválido")

    with pytest.raises(TelegramApiError, match="inválido"):
        fetch_recent_contacts("abc123 sem dois pontos", post=post)
