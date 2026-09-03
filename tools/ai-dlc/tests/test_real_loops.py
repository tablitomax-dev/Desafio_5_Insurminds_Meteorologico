"""Testes do executor e crítico REAIS (fase 2) — chat() é mockado.

Assinaturas preservadas (contrato da fase 1): o loop mantém os stubs
determinísticos por padrão; as fns reais são injetadas via
`real_functions()` (executor_fn/critic_fn).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from ai_dlc_orchestrator import (
    call_executor_llm_real,
    call_independent_critic_real,
    real_functions,
)
from contracts import (
    CriticReview,
    ExecutorProposal,
    ModelProfile,
    TaskContext,
)

CTX = TaskContext(
    task_id="t-100",
    objective="Implementar parseador JSON tolerante",
    acceptance_criteria=["parseia bloco cercado", "testes verdes"],
    files_involved=1,
)

PROFILE = ModelProfile(
    name="code_fast_test",
    env_var="OPENROUTER_MODEL_TEST",
    default_model="~deepseek/deepseek-v4-flash-latest",
    temperature=0.2,
    reasoning_effort="low",
    max_tokens=512,
)


def _chat_return(content: str, usage: dict | None = None) -> dict:
    payload = {
        "model": "~deepseek/deepseek-v4-flash-latest",
        "provider": "deepinfra/fp8",
        "choices": [{"message": {"content": content}}],
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


PROPOSAL_JSON = json.dumps(
    {
        "summary": "parseador implementado",
        "changed_files": ["parser.py"],
        "tests_pass": True,
        "acceptance_criteria_met": True,
        "notes": [],
    },
    ensure_ascii=False,
)

CRITIC_JSON = json.dumps(
    {
        "verdict": "accept",
        "reason": "critérios atendidos",
        "risk_notes": [],
    },
    ensure_ascii=False,
)


class TestExecutorReal:
    def test_json_direto_vira_proposta_com_uso(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        with patch(
            "ai_dlc_orchestrator.chat",
            return_value=_chat_return(PROPOSAL_JSON, usage),
        ):
            proposal = call_executor_llm_real(CTX, 1, PROFILE, api_key="sk-1")

        assert isinstance(proposal, ExecutorProposal)
        assert proposal.stub is False
        assert proposal.summary == "parseador implementado"
        assert proposal.tests_pass is True
        assert proposal.acceptance_criteria_met is True
        assert proposal.usage == usage
        assert proposal.model == "~deepseek/deepseek-v4-flash-latest"
        assert proposal.provider == "deepinfra/fp8"

    def test_json_em_bloco_cercado_e_parseado(self):
        cercado = f"```json\n{PROPOSAL_JSON}\n```"
        with patch("ai_dlc_orchestrator.chat", return_value=_chat_return(cercado)):
            proposal = call_executor_llm_real(CTX, 1, PROFILE, api_key="sk-1")
        assert proposal.tests_pass is True

    def test_json_com_prosa_ao_redor_e_parseado(self):
        com_prosa = f"Claro! Aqui está:\n{PROPOSAL_JSON}\nQualquer dúvida, avise."
        with patch("ai_dlc_orchestrator.chat", return_value=_chat_return(com_prosa)):
            proposal = call_executor_llm_real(CTX, 1, PROFILE, api_key="sk-1")
        assert proposal.changed_files == ["parser.py"]

    def test_resposta_malformada_vira_proposta_falha(self):
        with patch("ai_dlc_orchestrator.chat", return_value=_chat_return("não é json {")):
            proposal = call_executor_llm_real(CTX, 1, PROFILE, api_key="sk-1")
        assert proposal.tests_pass is False
        assert proposal.acceptance_criteria_met is False
        assert any("JSON" in note or "parse" in note.lower() for note in proposal.notes)

    def test_erro_de_rede_vira_proposta_falha_informativa(self):
        from openrouter_client import OpenRouterError

        with patch("ai_dlc_orchestrator.chat", side_effect=OpenRouterError("HTTP 502: bad gateway")):
            proposal = call_executor_llm_real(CTX, 1, PROFILE, api_key="sk-1")
        assert proposal.tests_pass is False
        assert any("HTTP 502" in note for note in proposal.notes)

    def test_campos_de_uso_tem_default_none(self):
        proposal = ExecutorProposal(summary="s", tests_pass=True, acceptance_criteria_met=True)
        assert proposal.model is None and proposal.provider is None and proposal.usage is None


class TestCriticReal:
    def test_veredito_json_vira_critic_review(self):
        usage = {"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38}
        with patch(
            "ai_dlc_orchestrator.chat",
            return_value=_chat_return(CRITIC_JSON, usage),
        ):
            review = call_independent_critic_real(
                ExecutorProposal(summary="s", tests_pass=True, acceptance_criteria_met=True),
                api_key="sk-1",
            )

        assert isinstance(review, CriticReview)
        assert review.stub is False
        assert review.verdict == "accept"
        assert review.reason == "critérios atendidos"
        assert review.usage == usage

    def test_resposta_malformada_vira_repair(self):
        with patch("ai_dlc_orchestrator.chat", return_value=_chat_return("ops")):
            review = call_independent_critic_real(
                ExecutorProposal(summary="s", tests_pass=False, acceptance_criteria_met=False),
                api_key="sk-1",
            )
        assert review.verdict == "repair"
        assert "malformada" in review.reason.lower() or "não é json" in review.reason.lower()

    def test_erro_de_rede_vira_blocked(self):
        from openrouter_client import OpenRouterError

        with patch("ai_dlc_orchestrator.chat", side_effect=OpenRouterError("timeout")):
            review = call_independent_critic_real(
                ExecutorProposal(summary="s", tests_pass=True, acceptance_criteria_met=True),
                api_key="sk-1",
            )
        assert review.verdict == "blocked"


class TestWiringNoLoop:
    def test_real_functions_entrega_fns_com_assinaturas_do_loop(self):
        fns = real_functions(api_key="sk-1")
        executor_fn, critic_fn = fns["executor_fn"], fns["critic_fn"]

        with patch(
            "ai_dlc_orchestrator.chat",
            return_value=_chat_return(PROPOSAL_JSON),
        ):
            proposal = executor_fn(CTX, 1, PROFILE)
        assert proposal.tests_pass is True

        with patch("ai_dlc_orchestrator.chat", return_value=_chat_return(CRITIC_JSON)):
            review = critic_fn(proposal)
        assert review.verdict == "accept"

    def test_loop_com_fns_reais_injetadas_termina_sucesso(self):
        from ai_dlc_orchestrator import run_loop

        fns = real_functions(api_key="sk-1")
        respostas = [
            _chat_return(PROPOSAL_JSON),
            _chat_return(CRITIC_JSON),
        ]

        def fake_chat(profile, messages, **kwargs):
            return respostas.pop(0)

        with patch("ai_dlc_orchestrator.chat", side_effect=fake_chat):
            result = run_loop(CTX, executor_fn=fns["executor_fn"], critic_fn=fns["critic_fn"])

        assert result.status == "success"
        assert result.records[-1].executor.usage is None  # resposta sem usage → None
