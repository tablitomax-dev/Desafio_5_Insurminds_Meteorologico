"""Testes do relatório de custo/tokens (fase 2)."""

from __future__ import annotations

from ai_dlc_orchestrator import run_loop
from contracts import (
    CriticReview,
    DifficultyLevel,
    ExecutorProposal,
    IterationRecord,
    LoopResult,
)
from cost_report import generate_cost_report, report_markdown
from openrouter_client import missing_credentials_decision


def _record(
    profile: str,
    exec_usage: dict | None = None,
    critic_usage: dict | None = None,
) -> IterationRecord:
    executor = ExecutorProposal(
        summary="s", tests_pass=True, acceptance_criteria_met=True, usage=exec_usage
    )
    critic = CriticReview(verdict="accept", reason="ok", usage=critic_usage)
    return IterationRecord(
        iteration=1, profile=profile, executor=executor, critic=critic, outcome="success"
    )


class TestGenerateCostReport:
    def test_vazio_para_sem_records(self):
        assert generate_cost_report([]) == {}

    def test_agrega_por_perfil_do_executor_e_critico(self):
        result = LoopResult(
            status="success",
            iterations=1,
            level=DifficultyLevel.N1,
            profile="code_fast",
            records=[
                _record(
                    "code_fast",
                    exec_usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    critic_usage={"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38},
                )
            ],
        )
        report = generate_cost_report([result])
        assert report["code_fast"] == {
            "calls": 1, "prompt_tokens": 10, "completion_tokens": 5,
            "total_tokens": 15, "cost": 0.0,
        }
        assert report["critic"]["calls"] == 1
        assert report["critic"]["total_tokens"] == 38

    def test_soma_multiplas_chamadas_no_mesmo_perfil(self):
        results = [
            LoopResult(
                status="success", iterations=2, level=DifficultyLevel.N1,
                profile="code_fast",
                records=[
                    _record("code_fast", exec_usage={"total_tokens": 10}),
                    _record("code_fast", exec_usage={"total_tokens": 7}),
                ],
            ),
            LoopResult(
                status="blocked", iterations=1, level=DifficultyLevel.N3,
                profile="code_deep",
                records=[_record("code_deep", exec_usage={"total_tokens": 100})],
            ),
        ]
        report = generate_cost_report(results)
        assert report["code_fast"]["calls"] == 2
        assert report["code_fast"]["total_tokens"] == 17
        assert report["code_deep"]["total_tokens"] == 100

    def test_custo_numerico_quando_presente(self):
        result = LoopResult(
            status="success", iterations=1, level=DifficultyLevel.N1,
            profile="code_fast",
            records=[_record("code_fast", exec_usage={"total_tokens": 10, "cost": 0.0125})],
        )
        assert generate_cost_report([result])["code_fast"]["cost"] == pytest_approx(0.0125)

    def test_usage_ausente_nao_quebra(self):
        result = LoopResult(
            status="success", iterations=1, level=DifficultyLevel.N1,
            profile="code_fast",
            records=[_record("code_fast", exec_usage=None)],
        )
        assert generate_cost_report([result]) == {}


def pytest_approx(value: float) -> float:
    """Helper local para comparação de float sem importar pytest.approx 2x."""
    import pytest

    return pytest.approx(value)


class TestReportMarkdown:
    def test_markdown_tem_tabela_e_total(self):
        result = LoopResult(
            status="success", iterations=1, level=DifficultyLevel.N1,
            profile="code_fast",
            records=[_record("code_fast", exec_usage={"total_tokens": 15})],
        )
        text = report_markdown(generate_cost_report([result]))
        assert "| perfil |" in text
        assert "code_fast" in text
        assert "TOTAL" in text

    def test_markdown_vazio_nao_explode(self):
        assert "TOTAL" in report_markdown({})


class TestIntegracaoComLoop:
    def test_usage_real_dos_records_alimenta_o_relatorio(self):
        """Records de um run com stubs (usage None) → relatório vazio; com usage → agregado."""
        from ai_dlc_orchestrator import TaskContext

        ctx = TaskContext(
            task_id="cost-1",
            objective="x",
            acceptance_criteria=["criterio"],
        )
        result = run_loop(ctx)  # stubs: sem usage
        assert generate_cost_report([result]) == {}

        # simulando usage de chamada real na 1ª iteração
        result.records[0].executor.usage = {"total_tokens": 42}
        assert generate_cost_report([result])["code_fast"]["total_tokens"] == 42


class TestBlockerHelper:
    def test_missing_credentials_decision_importavel(self):
        decision = missing_credentials_decision()
        assert decision.status == "blocked"
