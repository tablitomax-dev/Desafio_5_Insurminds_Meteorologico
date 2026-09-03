"""TDD fase 1 — loop, stop rules e persistência por iteração."""

from __future__ import annotations

from contracts import (
    BlockerType,
    CapacityDecision,
    CriticReview,
    ExecutorProposal,
    RiskLevel,
    TaskContext,
)
from ai_dlc_orchestrator import run_loop


def _ctx(**kwargs) -> TaskContext:
    base = dict(task_id="t1", objective="objetivo", acceptance_criteria=["c1"])
    base.update(kwargs)
    return TaskContext(**base)


def _always_fails(ctx: TaskContext, iteration: int, profile) -> ExecutorProposal:
    return ExecutorProposal(
        stub=True,
        summary="nunca converge",
        tests_pass=False,
        acceptance_criteria_met=False,
    )


class TestStopRules:
    def test_stubs_default_convergem(self) -> None:
        """Stub determinístico: tests na 2ª, aceitação na 3ª iteração."""
        result = run_loop(_ctx())
        assert result.status == "success"
        assert result.iterations == 3
        assert len(result.records) == 3
        assert result.records[-1].outcome == "success"

    def test_sucesso_exige_tests_pass_e_acceptance(self) -> None:
        """Stop rule: success = tests_pass E acceptance_criteria_met.
        Sem aceitação, mesmo com tests verdes, roda até estagnar."""
        def executor(ctx, iteration, profile):
            return ExecutorProposal(
                stub=True,
                summary="tests verdes, aceitação pendente",
                tests_pass=True,
                acceptance_criteria_met=False,
            )

        result = run_loop(_ctx(), executor_fn=executor)
        assert result.status == "blocked"
        assert result.blocker_type is BlockerType.stagnation

    def test_max_iterations_respeitado_por_nivel(self) -> None:
        result = run_loop(_ctx(files_involved=4), executor_fn=_always_fails)
        assert result.status == "blocked"
        assert result.iterations == 5  # N2 → cap 5
        assert result.records[-1].outcome == "blocked"

    def test_blocked_capacity_interrompe_loop(self) -> None:
        """Capacidade bloqueada (ex.: decisão de produto ausente) para na hora."""
        def capacity(proposal, iteration):
            return CapacityDecision(
                status="blocked",
                confidence=0.95,
                can_continue_autonomously=False,
                blocker_type=BlockerType.missing_product_decision,
                required_human_input=["definir política de desconto"],
            )

        result = run_loop(_ctx(), capacity_fn=capacity)
        assert result.status == "blocked"
        assert result.blocker_type is BlockerType.missing_product_decision
        assert result.iterations == 1


class TestCriticIndependente:
    def test_critic_accept_e_condicao_de_sucesso(self) -> None:
        """Critic recusando (repair) impede fechamento mesmo com critérios ok."""
        def executor(ctx, iteration, profile):
            return ExecutorProposal(
                stub=True,
                summary="ok",
                tests_pass=True,
                acceptance_criteria_met=True,
            )

        def critic(proposal):
            return CriticReview(stub=True, verdict="repair", reason="risco não mitigado")

        result = run_loop(_ctx(), executor_fn=executor, critic_fn=critic)
        assert result.status == "blocked"
        assert result.blocker_type is BlockerType.stagnation


class TestPersistencia:
    def test_log_por_iteracao(self) -> None:
        """Toda decisão de loop persiste por iteração (fase 1: sink em memória)."""
        sink: list[dict] = []
        result = run_loop(_ctx(), log_sink=sink)
        assert result.status == "success"
        assert len(sink) == len(result.records) == 3
        assert all("iteration" in entry and "outcome" in entry for entry in sink)

    def test_sem_sink_nao_explode(self) -> None:
        result = run_loop(_ctx())
        assert result.status == "success"
