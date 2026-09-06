"""Entidade PolicyHolder e InsuranceType — unit policy-holders.

Domínio puro: o catálogo/repositório vive em application/infrastructure;
aqui apenas a modelagem do segurado.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.weather import GeoLocation


class InsuranceType(str, Enum):
    """Ramos de seguro relevantes para as regras de risco (extensível)."""

    RESIDENTIAL = "residential"
    AUTO = "auto"


@dataclass(frozen=True)
class PolicyHolder:
    """Segurado com localização e ramos contratados.

    `is_coastal` marca região costeira — sinal usado pela StrongWindRule
    (story 04). Seeds preenchem o mix residencial/auto/litoral/rural.
    `city` é rótulo de apresentação (UI da banca, intent 003).
    `telegram_chat_id` é o destino real do envio (intent 004): a
    Telegram Bot API entrega por chat_id — NUNCA por número de telefone
    — e o vínculo nasce quando o segurado inicia a conversa com o bot.
    """

    id: str
    name: str
    phone: str
    location: GeoLocation
    insurance_types: frozenset[InsuranceType] = frozenset()
    is_coastal: bool = False
    city: str = ""
    cep: str = ""  # geocoding via BrasilAPI (intent 003)
    telegram_chat_id: str = ""  # envio real via Telegram (intent 004)

    def has_insurance(self, kind: InsuranceType) -> bool:
        return kind in self.insurance_types
