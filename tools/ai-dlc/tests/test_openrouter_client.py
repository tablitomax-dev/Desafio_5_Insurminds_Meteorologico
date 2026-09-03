"""Testes do cliente OpenRouter (fase 2) — sem rede: urlopen é mockado."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from contracts import BlockerType, CapacityDecision, ModelProfile
from openrouter_client import (
    API_URL,
    OpenRouterError,
    chat,
    missing_credentials_decision,
    read_api_key,
)

PROFILE = ModelProfile(
    name="code_fast_test",
    env_var="OPENROUTER_MODEL_TEST",
    default_model="~deepseek/deepseek-v4-flash-latest",
    temperature=0.2,
    reasoning_effort="low",
    max_tokens=1234,
    endpoint_tags=["baidu/fp8", "deepinfra/fp8"],
    quantizations=["fp8"],
)


def _fake_response(payload: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    return resp


def _http_error(code: int, body: dict):
    err = MagicMock()
    err.code = code
    err.read.return_value = json.dumps(body).encode("utf-8")
    return err


class TestReadApiKey:
    def test_env_tem_prioridade(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "  sk-env-123  ")
        assert read_api_key(use_registry=False) == "sk-env-123"

    def test_sem_fontes_retorna_vazio(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert read_api_key(use_registry=False) == ""


class TestChat:
    def test_payload_tem_model_effort_e_provider_policy(self):
        captured = {}

        def fake_urlopen(request, timeout):  # noqa: ANN001
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.get_header("Authorization")
            return _fake_response({"id": "x", "model": "ok", "usage": {}})

        with patch("openrouter_client.urllib.request.urlopen", fake_urlopen):
            data = chat(PROFILE, [{"role": "user", "content": "oi"}], api_key="sk-1")

        assert captured["url"] == API_URL
        assert captured["auth"] == "Bearer sk-1"
        body = captured["body"]
        assert body["model"] == "~deepseek/deepseek-v4-flash-latest"
        assert body["reasoning"] == {"effort": "low"}
        assert body["provider"] == {"only": ["baidu/fp8", "deepinfra/fp8"], "quantizations": ["fp8"]}
        assert body["max_tokens"] == 1234
        assert body["temperature"] == 0.2
        assert data["id"] == "x"

    def test_override_de_max_tokens_para_smoke(self):
        captured = {}

        def fake_urlopen(request, timeout):  # noqa: ANN001
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _fake_response({})

        with patch("openrouter_client.urllib.request.urlopen", fake_urlopen):
            chat(PROFILE, [], api_key="sk-1", max_tokens=64)

        assert captured["body"]["max_tokens"] == 64

    def test_key_ausente_falha_antes_da_rede(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with patch("openrouter_client.urllib.request.urlopen") as mock_open:
            with pytest.raises(OpenRouterError, match="OPENROUTER_API_KEY"):
                chat(PROFILE, [], api_key="", use_registry_key=False)
        mock_open.assert_not_called()

    def test_http_error_ira_open_router_error_com_mensagem(self):
        err_body = json.dumps({"error": {"message": "modelo não encontrado"}}).encode()
        err = urllib.error.HTTPError(API_URL, 404, "Not Found", {}, BytesIO(err_body))

        def fake_urlopen(request, timeout):  # noqa: ANN001
            raise err

        with patch("openrouter_client.urllib.request.urlopen", fake_urlopen):
            with pytest.raises(OpenRouterError, match="HTTP 404.*modelo não encontrado"):
                chat(PROFILE, [], api_key="sk-1")

    def test_erro_de_rede_ira_open_router_error(self):
        def fake_urlopen(request, timeout):  # noqa: ANN001
            raise urllib.error.URLError("connection timed out")

        with patch("openrouter_client.urllib.request.urlopen", fake_urlopen):
            with pytest.raises(OpenRouterError, match="connection timed out"):
                chat(PROFILE, [], api_key="sk-1")


class TestMissingCredentials:
    def test_decisao_bloqueada_e_consistente(self):
        decision = missing_credentials_decision()
        assert decision.status == "blocked"
        assert decision.blocker_type is BlockerType.missing_credentials
        assert decision.can_continue_autonomously is False
        assert decision.required_human_input
        assert decision.evidence

    def test_retorna_capacity_decision_tipada(self):
        assert isinstance(missing_credentials_decision(), CapacityDecision)
