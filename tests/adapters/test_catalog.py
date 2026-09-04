"""Testes do catálogo de segurados — unit policy-holders (seeds JSON)."""

import json
from pathlib import Path

from app.adapters.catalog import (
    InMemoryPolicyHolderRepository,
    load_policy_holders,
)
from app.domain.holders import InsuranceType

REPO_ROOT = Path(__file__).parent.parent.parent
SEEDS_PATH = REPO_ROOT / "data" / "policy_holders.json"


def _holder(**overrides):
    from app.domain.weather import GeoLocation

    base = dict(
        id="H001",
        name="Maria Silva",
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
        is_coastal=False,
    )
    base.update(overrides)
    from app.domain.holders import PolicyHolder

    return PolicyHolder(**base)


def test_repository_in_memory_lista_todos():
    """Given repositório com 2 segurados, when list_all, then os 2."""
    holders = [_holder(id="H001"), _holder(id="H002")]

    repository = InMemoryPolicyHolderRepository(holders)

    assert [h.id for h in repository.list_all()] == ["H001", "H002"]


def test_load_policy_holders_do_json(tmp_path):
    """Given JSON de seeds no formato do repositório, when load, then
    PolicyHolders com tipos e coastal parseados."""
    path = tmp_path / "policy_holders.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "H001",
                    "name": "Maria Silva",
                    "phone": "+5511999990001",
                    "latitude": -23.55,
                    "longitude": -46.63,
                    "insurance_types": ["residential", "auto"],
                    "is_coastal": False,
                },
                {
                    "id": "H002",
                    "name": "Ana Costa",
                    "phone": "+5513999990002",
                    "latitude": -23.96,
                    "longitude": -46.33,
                    "insurance_types": ["auto"],
                    "is_coastal": True,
                },
            ]
        ),
        encoding="utf-8",
    )

    holders = load_policy_holders(path)

    assert len(holders) == 2
    maria, ana = holders
    assert maria.has_insurance(InsuranceType.RESIDENTIAL)
    assert maria.has_insurance(InsuranceType.AUTO)
    assert ana.is_coastal is True
    assert ana.location.latitude == -23.96


def test_is_coastal_default_false_e_tipos_opcionais(tmp_path):
    """Given seed mínima (sem insurance_types/is_coastal), when load,
    then defaults: frozenset vazio e False."""
    path = tmp_path / "policy_holders.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "H009",
                    "name": "Sem Extras",
                    "phone": "+5511999990009",
                    "latitude": -20.0,
                    "longitude": -45.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    holders = load_policy_holders(path)

    holder = holders[0]
    assert holder.insurance_types == frozenset()
    assert holder.is_coastal is False


def test_seeds_versionados_sao_validos_para_a_demo():
    """Given data/policy_holders.json versionado (demo da banca), when
    load, then 5–10 segurados, ids únicos e mix litoral/auto presentes."""
    holders = load_policy_holders(SEEDS_PATH)

    assert 5 <= len(holders) <= 10
    ids = [h.id for h in holders]
    assert len(ids) == len(set(ids))
    assert any(h.is_coastal for h in holders)
    assert any(h.has_insurance(InsuranceType.AUTO) for h in holders)
    assert any(h.has_insurance(InsuranceType.RESIDENTIAL) for h in holders)
