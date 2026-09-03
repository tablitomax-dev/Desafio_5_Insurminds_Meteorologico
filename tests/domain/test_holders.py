"""Testes da entidade PolicyHolder e InsuranceType (unit policy-holders)."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.weather import GeoLocation


class TestInsuranceType:
    def test_tem_residencial_e_auto(self):
        assert InsuranceType.RESIDENTIAL.value == "residential"
        assert InsuranceType.AUTO.value == "auto"


class TestPolicyHolder:
    def test_cria_com_campos_minimos(self):
        holder = PolicyHolder(
            id="h-001",
            name="Maria Silva",
            phone="+5511999990001",
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
        )
        assert holder.id == "h-001"
        assert holder.name == "Maria Silva"
        assert holder.phone == "+5511999990001"
        assert InsuranceType.RESIDENTIAL in holder.insurance_types

    def test_is_coastal_default_falso(self):
        holder = PolicyHolder(
            id="h-002",
            name="João",
            phone="+5511999990002",
            location=GeoLocation(latitude=-23.0, longitude=-43.0),
            insurance_types=frozenset(),
        )
        assert holder.is_coastal is False

    def test_segurado_litoraneo_com_auto(self):
        holder = PolicyHolder(
            id="h-003",
            name="Ana Costa",
            phone="+5513999990003",
            location=GeoLocation(latitude=-23.98, longitude=-46.30),
            insurance_types=frozenset({InsuranceType.AUTO}),
            is_coastal=True,
        )
        assert holder.is_coastal is True
        assert InsuranceType.AUTO in holder.insurance_types

    def test_e_imutavel(self):
        holder = PolicyHolder(
            id="h-004",
            name="Carlos",
            phone="+5511999990004",
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            insurance_types=frozenset(),
        )
        with pytest.raises(FrozenInstanceError):
            holder.name = "Outro"  # type: ignore[misc]
