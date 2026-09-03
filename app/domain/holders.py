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
    """

    id: str
    name: str
    phone: str
    location: GeoLocation
    insurance_types: frozenset[InsuranceType] = frozenset()
    is_coastal: bool = False

    def has_insurance(self, kind: InsuranceType) -> bool:
        return kind in self.insurance_types
