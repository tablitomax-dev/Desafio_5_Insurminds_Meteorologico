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

    `is_coastal` marca região costeira — sinal usado pela RessacaRule
    (o gate geográfico da StrongWindRule foi removido na emenda do dono
    de 2026-09-13 — ADR-011). Seeds preenchem o mix residencial/auto/litoral/rural.
    `city` é rótulo de apresentação (UI da banca, intent 003). O destino
    Telegram NÃO vive aqui: o chat_id é resolvido por telefone no
    repositório de vínculos (SQLite — intent 006, ADR-010).
    """

    id: str
    name: str
    phone: str
    location: GeoLocation
    insurance_types: frozenset[InsuranceType] = frozenset()
    is_coastal: bool = False
    city: str = ""
    cep: str = ""  # geocoding via BrasilAPI (intent 003)

    def has_insurance(self, kind: InsuranceType) -> bool:
        return kind in self.insurance_types
