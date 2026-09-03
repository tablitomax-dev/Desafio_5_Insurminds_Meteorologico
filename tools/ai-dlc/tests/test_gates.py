"""TDD fase 1 — gates: N1/N2 autônomos, N3 com dupla confirmação."""

from __future__ import annotations

from contracts import RiskLevel, TaskContext
from ai_dlc_orchestrator import run_loop


def _n3_ctx() -> TaskContext:
    return TaskContext(
        task_id="t-n3",
        objective="migrar schema",
        acceptance_criteria=["c1"],
        has_schema_changes=True,
        risk=RiskLevel.HIGH,
    )


class TestGateN3:
    def test_n3_sem_confirmacao_para_em_gate(self) -> None:
        result = run_loop(_n3_ctx())
        assert result.status == "awaiting_dual_confirmation"
        assert result.iterations == 0
        assert result.records[0].outcome == "awaiting_human"

    def test_n3_com_dupla_confirmacao_executa(self) -> None:
        result = run_loop(_n3_ctx(), human_confirmed=True)
        assert result.status == "success"


class TestGateN1N2:
    def test_n1_autonomo_sem_confirmacao(self) -> None:
        result = run_loop(
            TaskContext(task_id="t1", objective="x", acceptance_criteria=["c1"])
        )
        assert result.status == "success"

    def test_n2_autonomo_sem_confirmacao(self) -> None:
        result = run_loop(
            TaskContext(
                task_id="t2", objective="x", acceptance_criteria=["c1"],
                files_involved=5,
            )
        )
        assert result.status == "success"
