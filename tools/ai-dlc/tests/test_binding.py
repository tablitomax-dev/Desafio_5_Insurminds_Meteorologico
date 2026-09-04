"""TDD — binding definitivo validado na API do OpenRouter (2026-09-01).

Fatos verificados contra /api/v1/models e /endpoints:
- modelo fast é o alias "~deepseek/deepseek-v4-flash-latest" (com til);
- GLM aceita apenas max/high/low (reasoning mandatory);
- tags de endpoint: z-ai/fp8, openai/flex, baidu/fp8 etc.
"""

from __future__ import annotations

import pytest as pytest_monkeypatch
from ai_dlc_orchestrator import CRITIC_PROFILE, MODEL_PROFILES, profile_for
from contracts import DifficultyLevel


class TestBindingDefinitivo:
    def test_code_fast(self) -> None:
        p = MODEL_PROFILES["code_fast"]
        assert p.default_model == "~deepseek/deepseek-v4-flash-latest"
        assert p.reasoning_effort == "low"
        assert p.temperature == 0.2
        assert p.max_tokens == 4096
        assert p.endpoint_tags == ["baidu/fp8", "deepinfra/fp8", "open-inference/fp8"]
        assert p.quantizations == ["fp8"]

    def test_code_balanced(self) -> None:
        p = MODEL_PROFILES["code_balanced"]
        assert p.default_model == "z-ai/glm-5.3-flash"
        # GLM: supported_efforts=[max, high, low] — xhigh não é suportado.
        assert p.reasoning_effort == "high"
        assert p.temperature == 0.3
        assert p.max_tokens == 8192
        assert p.endpoint_tags == ["z-ai/fp8", "novita/fp8", "gmicloud/fp8"]
        assert p.quantizations == ["fp8"]

    def test_code_deep(self) -> None:
        p = MODEL_PROFILES["code_deep"]
        assert p.default_model == "z-ai/glm-5.3-flash"
        assert p.reasoning_effort == "max"
        assert p.temperature == 0.5
        assert p.max_tokens == 16384
        assert p.endpoint_tags == ["z-ai/fp8", "novita/fp8", "gmicloud/fp8"]
        assert p.quantizations == ["fp8"]

    def test_critic_profile(self) -> None:
        p = CRITIC_PROFILE
        assert p.name == "critic"
        assert p.env_var == "OPENROUTER_MODEL_CRITIC"
        assert p.default_model == "openai/gpt-5.6-luna-pro"
        assert p.reasoning_effort == "max"
        assert p.temperature == 0.2
        assert p.max_tokens == 20000
        assert p.endpoint_tags == ["openai/flex"]
        assert p.quantizations == []  # openai/flex: quant unknown — não filtrar

    def test_env_override_continua_funcionando(
        self, monkeypatch: pytest_monkeypatch
    ) -> None:
        monkeypatch.setenv("OPENROUTER_MODEL_CRITIC", "outro/critico")
        assert CRITIC_PROFILE.resolve_model() == "outro/critico"

    def test_perfis_ligados_aos_niveis(self) -> None:
        assert profile_for(DifficultyLevel.N1).name == "code_fast"
        assert profile_for(DifficultyLevel.N2).name == "code_balanced"
        assert profile_for(DifficultyLevel.N3).name == "code_deep"
