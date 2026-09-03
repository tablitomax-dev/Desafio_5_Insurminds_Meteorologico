"""Testes do SimulatedSender — infra do story 07 (envio simulado)."""

from datetime import timezone

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import GeneratedMessage
from app.domain.notify import SimulatedSender
from app.domain.risk import RiskKind
from app.domain.weather import GeoLocation


def make_holder() -> PolicyHolder:
    return PolicyHolder(
        id="h-001",
        name="Maria Silva",
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
    )


def make_message(holder_id: str = "h-001") -> GeneratedMessage:
    return GeneratedMessage(
        holder_id=holder_id,
        alert_kind=RiskKind.HEAVY_RAIN,
        text="Olá, Maria Silva! Chuva intensa prevista. • Verifique a drenagem. • Evite áreas alagadas.",
    )


class TestSimulatedSender:
    def test_send_retorna_notification_record(self, capsys):
        sender = SimulatedSender()
        record = sender.send(make_holder(), make_message())

        assert record.holder_id == "h-001"
        assert record.channel == "sms"
        assert record.status == "simulated"
        assert "Maria Silva" in record.message

    def test_send_imprime_marcacao_simulado(self, capsys):
        sender = SimulatedSender()
        holder = make_holder()
        sender.send(holder, make_message())
        captured = capsys.readouterr()
        assert "[SIMULADO]" in captured.out
        assert holder.phone in captured.out

    def test_records_acumula_despachos(self):
        sender = SimulatedSender()
        holder = make_holder()
        sender.send(holder, make_message())
        sender.send(holder, make_message())
        assert len(sender.records) == 2
        assert all(r.holder_id == "h-001" for r in sender.records)

    def test_sent_at_e_timezone_aware(self):
        sender = SimulatedSender()
        record = sender.send(make_holder(), make_message())
        assert record.sent_at.tzinfo is timezone.utc

    def test_channel_configuravel(self):
        sender = SimulatedSender(channel="push")
        record = sender.send(make_holder(), make_message())
        assert record.channel == "push"
