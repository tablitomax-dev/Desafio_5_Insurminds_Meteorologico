"""Testes do loader PyYAML da spec (fase 2).

A spec (ai-dlc-spec.yaml) é a fonte da verdade declarativa; o código
(ai_dlc_orchestrator) valida consistência a cada carga. Divergência =
lista de strings legíveis (vazia = consistente).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ai_dlc_orchestrator import CRITIC_PROFILE, MODEL_PROFILES, PROFILE_BY_LEVEL
from contracts import DifficultyLevel
from spec_loader import check_consistency, load_spec, verify_spec_consistency

SPEC_PATH = Path(__file__).resolve().parents[1] / "ai-dlc-spec.yaml"


class TestLoadSpec:
    def test_carrega_yaml_da_raiz_do_pacote(self):
        spec = load_spec()
        assert isinstance(spec, dict)
        assert re.fullmatch(r"\d+\.\d+\.\d+", spec["version"])

    def test_caminho_customizado(self, tmp_path: Path):
        custom = tmp_path / "spec.yaml"
        custom.write_text("version: '9.9.9'\nname: teste\n", encoding="utf-8")
        spec = load_spec(custom)
        assert spec["version"] == "9.9.9"

    def test_arquivo_ausente_levanta_erro_claro(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_spec(tmp_path / "nao-existe.yaml")

    def test_yaml_invalido_levanta_erro_claro(self, tmp_path: Path):
        bad = tmp_path / "spec.yaml"
        bad.write_text("version: [quebrado\n  - sem fim", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML"):
            load_spec(bad)

    def test_secao_fase_2_sem_todo(self):
        """Fase 2: backlog resolvido — spec não pode ter TODO/FIXME."""
        spec = load_spec()
        texto = SPEC_PATH.read_text(encoding="utf-8")
        assert "TODO" not in texto and "FIXME" not in texto
        assert spec["secondary_orchestrator"]["enabled"] is True


class TestCheckConsistency:
    def test_spec_consistente_com_codigo(self):
        spec = load_spec()
        assert check_consistency(spec) == []

    def test_divergencia_de_modelo_e_detectada(self):
        spec = load_spec()
        spec["model_profiles"]["code_fast"]["default_model"] = "outro/modelo"
        mismatches = check_consistency(spec)
        assert any("code_fast" in m and "default_model" in m for m in mismatches)

    def test_divergencia_de_esforco_e_detectada(self):
        spec = load_spec()
        spec["model_profiles"]["code_balanced"]["reasoning_effort"] = "max"
        mismatches = check_consistency(spec)
        assert any("reasoning_effort" in m for m in mismatches)

    def test_divergencia_de_endpoint_tags_e_detectada(self):
        spec = load_spec()
        spec["model_profiles"]["critic"]["endpoint_tags"] = ["outra/tag"]
        mismatches = check_consistency(spec)
        assert any("endpoint_tags" in m for m in mismatches)

    def test_perfil_ausente_na_spec_e_detectado(self):
        spec = load_spec()
        del spec["model_profiles"]["code_deep"]
        mismatches = check_consistency(spec)
        assert any("code_deep" in m for m in mismatches)

    def test_divergencia_de_max_tokens_e_detectada(self):
        spec = load_spec()
        spec["model_profiles"]["code_fast"]["max_tokens"] = 1
        mismatches = check_consistency(spec)
        assert any("max_tokens" in m for m in mismatches)

    def test_verificar_arquivo_real_vazio(self):
        assert verify_spec_consistency() == []


class TestRoutingDaSpec:
    """level_mapping da spec deve espelhar PROFILE_BY_LEVEL e DifficultyLevel."""

    def test_mapeamento_de_perfis(self):
        spec = load_spec()
        mapping = spec["routing"]["level_mapping"]
        for level, perfil in PROFILE_BY_LEVEL.items():
            # YAML parseia chave numérica como int
            assert mapping[level]["model_profile"] == perfil

    def test_max_iterations_da_spec_bate_com_contrato(self):
        spec = load_spec()
        mapping = spec["routing"]["level_mapping"]
        for level in DifficultyLevel:
            assert mapping[int(level)]["max_iterations"] == level.max_iterations

    def test_todos_os_perfis_da_spec_existem_no_codigo(self):
        spec = load_spec()
        nomes = set(MODEL_PROFILES) | {"critic"}
        assert set(spec["model_profiles"]) == nomes
        assert CRITIC_PROFILE.name == "critic"
