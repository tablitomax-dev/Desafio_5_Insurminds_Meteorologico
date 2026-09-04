"""TDD fase 1 — contratos tipados (contracts.py)."""

from __future__ import annotations

import pytest
from contracts import (
    BlockerType,
    CapacityDecision,
    DifficultyLevel,
    ExecutorProposal,
    ModelProfile,
    TaskContext,
)
from pydantic import ValidationError


def _ctx(**kwargs) -> TaskContext:
    base = dict(task_id="t1", objective="objetivo", acceptance_criteria=["c1"])
    base.update(kwargs)
    return TaskContext(**base)


class TestTaskContext:
    def test_defaults_fase_1(self) -> None:
        ctx = _ctx()
        assert ctx.files_involved == 1
        assert ctx.risk.value == "low"
        assert not ctx.has_schema_changes

    def test_aceitacao_obrigatoria(self) -> None:
        with pytest.raises(ValidationError):
            TaskContext(task_id="t1", objective="x", acceptance_criteria=[])


class TestDifficultyLevel:
    def test_unificacao_com_depth_levels(self) -> None:
        """Níveis = depth_levels do context-budget (TINY/STANDARD/DEEP)."""
        assert DifficultyLevel.N1.depth == "TINY"
        assert DifficultyLevel.N2.depth == "STANDARD"
        assert DifficultyLevel.N3.depth == "DEEP"

    def test_max_iterations_por_nivel(self) -> None:
        assert DifficultyLevel.N1.max_iterations == 3
        assert DifficultyLevel.N2.max_iterations == 5
        assert DifficultyLevel.N3.max_iterations == 7


class TestBlockerType:
    def test_seis_tipos_do_contrato(self) -> None:
        esperados = {
            "missing_credentials",
            "missing_product_decision",
            "ambiguous_requirement",
            "destructive_next_step",
            "non_reproducible_error",
            "stagnation",
        }
        assert {b.value for b in BlockerType} == esperados


class TestCapacityDecision:
    def test_blocked_exige_blocker_type(self) -> None:
        with pytest.raises(ValidationError):
            CapacityDecision(status="blocked", confidence=0.9)

    def test_blocked_recusa_autonomia(self) -> None:
        with pytest.raises(ValidationError):
            CapacityDecision(
                status="blocked",
                confidence=0.9,
                can_continue_autonomously=True,
                blocker_type=BlockerType.stagnation,
            )

    def test_ok_recusa_blocker_type(self) -> None:
        with pytest.raises(ValidationError):
            CapacityDecision(
                status="ok", confidence=0.9, blocker_type=BlockerType.stagnation
            )

    def test_warning_exige_input_humano(self) -> None:
        with pytest.raises(ValidationError):
            CapacityDecision(status="warning", confidence=0.85)

    def test_warning_valido(self) -> None:
        d = CapacityDecision(
            status="warning",
            confidence=0.85,
            required_human_input=["decidir entre A e B"],
        )
        assert d.can_continue_autonomously is True

    def test_confidence_limitada_0_1(self) -> None:
        with pytest.raises(ValidationError):
            CapacityDecision(status="ok", confidence=1.5)


class TestModelProfile:
    def test_env_override_tem_prioridade(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_MODEL_FAST", "outro/modelo")
        p = ModelProfile(
            name="code_fast",
            env_var="OPENROUTER_MODEL_FAST",
            default_model="deepseek/deepseek-v4-flash-latest",
            temperature=0.2,
        )
        assert p.resolve_model() == "outro/modelo"

    def test_sem_env_usa_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENROUTER_MODEL_FAST", raising=False)
        p = ModelProfile(
            name="code_fast",
            env_var="OPENROUTER_MODEL_FAST",
            default_model="deepseek/deepseek-v4-flash-latest",
            temperature=0.2,
        )
        assert p.resolve_model() == "deepseek/deepseek-v4-flash-latest"

    def test_env_vazia_cai_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_MODEL_DEEP", "  ")
        p = ModelProfile(
            name="code_deep",
            env_var="OPENROUTER_MODEL_DEEP",
            default_model="z-ai/glm-5.3-flash",
            temperature=0.5,
        )
        assert p.resolve_model() == "z-ai/glm-5.3-flash"


class TestExecutorProposal:
    def test_stub_marcado(self) -> None:
        p = ExecutorProposal(
            stub=True,
            summary="stub",
            tests_pass=True,
            acceptance_criteria_met=False,
        )
        assert p.stub is True


class TestModelProfileBinding:
    """Binding definitivo (decisão do usuário, 2026-09-01)."""

    def test_provider_policy_whitelist(self) -> None:
        p = ModelProfile(
            name="code_fast",
            env_var="OPENROUTER_MODEL_FAST",
            default_model="~deepseek/deepseek-v4-flash-latest",
            endpoint_tags=["baidu/fp8", "deepinfra/fp8", "open-inference/fp8"],
            quantizations=["fp8"],
        )
        assert p.provider_policy() == {
            "only": ["baidu/fp8", "deepinfra/fp8", "open-inference/fp8"],
            "quantizations": ["fp8"],
        }

    def test_provider_policy_vazia(self) -> None:
        p = ModelProfile(
            name="x", env_var="X", default_model="m"
        )
        assert p.provider_policy() == {}

    def test_effort_valores_validos(self) -> None:
        p = ModelProfile(
            name="code_deep",
            env_var="OPENROUTER_MODEL_DEEP",
            default_model="z-ai/glm-5.3-flash",
            reasoning_effort="max",
            max_tokens=16384,
        )
        assert p.reasoning_effort == "max"
        assert p.max_tokens == 16384

    def test_effort_invalido_rejeitado(self) -> None:
        with pytest.raises(ValidationError):
            ModelProfile(
                name="x", env_var="X", default_model="m", reasoning_effort="ultra"
            )

    def test_max_tokens_positivo(self) -> None:
        with pytest.raises(ValidationError):
            ModelProfile(name="x", env_var="X", default_model="m", max_tokens=0)
