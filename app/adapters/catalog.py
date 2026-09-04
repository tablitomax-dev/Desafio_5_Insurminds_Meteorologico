"""Catálogo de segurados — unit policy-holders (seeds JSON).

Repository in-memory carregado de `data/policy_holders.json`
(5–10 segurados fictícios com mix residencial/auto/litoral/rural).
Sem I/O além da carga inicial — o pipeline recebe a port pronta.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.weather import GeoLocation

DEFAULT_SEEDS_PATH = Path("data") / "policy_holders.json"


def load_policy_holders(path: str | Path = DEFAULT_SEEDS_PATH) -> list[PolicyHolder]:
    """Carrega seeds JSON → entidades PolicyHolder do domínio."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    holders: list[PolicyHolder] = []
    for record in records:
        holders.append(
            PolicyHolder(
                id=record["id"],
                name=record["name"],
                phone=record["phone"],
                location=GeoLocation(
                    latitude=float(record["latitude"]),
                    longitude=float(record["longitude"]),
                ),
                insurance_types=frozenset(
                    InsuranceType(kind) for kind in record.get("insurance_types", [])
                ),
                is_coastal=bool(record.get("is_coastal", False)),
            )
        )
    return holders


class InMemoryPolicyHolderRepository:
    """Port PolicyHolderRepository backed por lista em memória."""

    def __init__(self, holders: list[PolicyHolder]):
        self._holders = list(holders)

    def list_all(self) -> list[PolicyHolder]:
        return list(self._holders)


def load_default_repository() -> InMemoryPolicyHolderRepository:
    """Atalho da CLI: seeds padrão → repository in-memory."""
    return InMemoryPolicyHolderRepository(load_policy_holders())
