"""Simulação de envio de notificações — unit notification-sim.

Port `NotificationSender` isolada para trocar por provider real no
futuro; `SimulatedSender` apenas imprime e registra em memória.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.domain.holders import PolicyHolder
from app.domain.messages import GeneratedMessage


@dataclass(frozen=True)
class NotificationRecord:
    """Registro de um despacho (consultável no relatório da rodada)."""

    holder_id: str
    channel: str
    message: str
    sent_at: datetime
    status: str


class NotificationSender(Protocol):
    """Port de envio — implementação real futura troca só esta peça."""

    def send(
        self, holder: PolicyHolder, message: GeneratedMessage
    ) -> NotificationRecord: ...


class SimulatedSender:
    """Envio simulado: console marcado como [SIMULADO] + lista em memória."""

    def __init__(self, channel: str = "sms"):
        self.channel = channel
        self.records: list[NotificationRecord] = []

    def send(
        self, holder: PolicyHolder, message: GeneratedMessage
    ) -> NotificationRecord:
        record = NotificationRecord(
            holder_id=holder.id,
            channel=self.channel,
            message=message.text,
            sent_at=datetime.now(UTC),
            status="simulated",
        )
        print(f"[SIMULADO] {self.channel} → {holder.phone}: {message.text}")
        self.records.append(record)
        return record
