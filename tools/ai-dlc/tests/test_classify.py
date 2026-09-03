"""TDD fase 1 — roteamento determinístico por sinais objetivos."""

from __future__ import annotations

import pytest

from ai_dlc_orchestrator import classify_task, profile_for, requires_dual_confirmation
from contracts import DifficultyLevel, TaskContext


def _ctx(**kwargs) -> TaskContext:
    base = dict(task_id="t1", objective="objetivo", acceptance_criteria=["c1"])
    base.update(kwargs)
    return TaskContext(**base)


class TestClassifyTask:
    def test_n1_tarefa_pequena_isolada(self) -> None:
        assert classify_task(_ctx()) is DifficultyLevel.N1

    def test_n2_arquivos_multiplus(self) -> None:
        assert classify_task(_ctx(files_involved=4)) is DifficultyLevel.N2

    def test_n2_risco_medio(self) -> None:
        from contracts import RiskLevel

        assert classify_task(_ctx(risk=RiskLevel.MEDIUM)) is DifficultyLevel.N2

    def test_n2_concorrencia_ou_infra(self) -> None:
        assert (
            classify_task(_ctx(has_concurrency_or_infra=True)) is DifficultyLevel.N2
        )

    @pytest.mark.parametrize(
        "flag",
        [
            "involves_architecture",
            "involves_security_or_data",
            "involves_migration",
            "has_schema_changes",
            "has_auth_or_secrets",
        ],
    )
    def test_n3_sinais_criticos(self, flag: str) -> None:
        assert classify_task(_ctx(**{flag: True})) is DifficultyLevel.N3

    def test_n3_risco_alto_vence_qualquer_signal(self) -> None:
        from contracts import RiskLevel

        assert classify_task(_ctx(risk=RiskLevel.HIGH)) is DifficultyLevel.N3

    def test_precedencia_n3_sobre_n2(self) -> None:
        """Schema + 8 arquivos: N3 ganha (checkpoint do project_rules)."""
        assert (
            classify_task(_ctx(files_involved=8, has_schema_changes=True))
            is DifficultyLevel.N3
        )


class TestProfileFor:
    def test_mapeamento_niveis_perfis(self) -> None:
        assert profile_for(DifficultyLevel.N1).name == "code_fast"
        assert profile_for(DifficultyLevel.N2).name == "code_balanced"
        assert profile_for(DifficultyLevel.N3).name == "code_deep"


class TestGates:
    def test_apenas_n3_exige_dupla_confirmacao(self) -> None:
        assert requires_dual_confirmation(DifficultyLevel.N3) is True
        assert requires_dual_confirmation(DifficultyLevel.N1) is False
        assert requires_dual_confirmation(DifficultyLevel.N2) is False
