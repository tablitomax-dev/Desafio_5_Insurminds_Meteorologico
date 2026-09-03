"""Loader PyYAML da spec executável do orquestrador (ADR-006, fase 2).

A spec (`ai-dlc-spec.yaml`) é a fonte da verdade declarativa dos perfis
de modelo e do roteamento; este módulo carrega o YAML e valida que o
código (`ai_dlc_orchestrator`) está em consistência com ela. Qualquer
divergência vira item legível na lista retornada por
`check_consistency()` (vazia = consistente).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_dlc_orchestrator import CRITIC_PROFILE, MODEL_PROFILES, PROFILE_BY_LEVEL
from contracts import DifficultyLevel

SPEC_PATH = Path(__file__).resolve().parent / "ai-dlc-spec.yaml"

# campo na spec -> atributo do ModelProfile
_PROFILE_FIELDS: dict[str, str] = {
    "env_binding": "env_var",
    "default_model": "default_model",
    "temperature": "temperature",
    "reasoning_effort": "reasoning_effort",
    "max_tokens": "max_tokens",
    "endpoint_tags": "endpoint_tags",
    "quantizations": "quantizations",
}

_LIST_FIELDS = {"endpoint_tags", "quantizations"}


def load_spec(path: "str | Path | None" = None) -> dict:
    """Carrega a spec YAML (padrão: ai-dlc-spec.yaml do pacote)."""
    target = Path(path) if path is not None else SPEC_PATH
    if not target.exists():
        raise FileNotFoundError(f"spec não encontrada: {target}")
    try:
        with target.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML inválido em {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"spec deve ser um mapeamento YAML: {target}")
    return data


def check_consistency(spec: dict) -> list[str]:
    """Compara perfis e roteamento da spec contra o código do pacote.

    Retorna lista de divergências legíveis; lista vazia = consistente.
    Campos de lista ausentes na spec são tratados como [] (ex.: critic
    não declara quantizations).
    """
    mismatches: list[str] = []
    code_profiles: dict = {**MODEL_PROFILES, "critic": CRITIC_PROFILE}
    spec_profiles = spec.get("model_profiles") or {}

    for name, profile in code_profiles.items():
        sp = spec_profiles.get(name)
        if not isinstance(sp, dict):
            mismatches.append(f"perfil '{name}' ausente na spec")
            continue
        for spec_field, attr in _PROFILE_FIELDS.items():
            spec_value = sp.get(spec_field)
            code_value = getattr(profile, attr)
            if spec_field in _LIST_FIELDS and spec_value is None:
                spec_value = []
            if spec_value != code_value:
                mismatches.append(
                    f"{name}.{spec_field}: spec={spec_value!r} != código={code_value!r}"
                )

    routing = (spec.get("routing") or {}).get("level_mapping") or {}
    for level in DifficultyLevel:
        entry = routing.get(int(level))
        if not isinstance(entry, dict):
            mismatches.append(f"routing.level_mapping[{int(level)}] ausente na spec")
            continue
        expected_profile = PROFILE_BY_LEVEL[int(level)]
        if entry.get("model_profile") != expected_profile:
            mismatches.append(
                f"routing.level_mapping[{int(level)}].model_profile: "
                f"spec={entry.get('model_profile')!r} != código={expected_profile!r}"
            )
        if entry.get("max_iterations") != level.max_iterations:
            mismatches.append(
                f"routing.level_mapping[{int(level)}].max_iterations: "
                f"spec={entry.get('max_iterations')!r} != código={level.max_iterations!r}"
            )
    return mismatches


def verify_spec_consistency(path: "str | Path | None" = None) -> list[str]:
    """Carrega a spec e valida consistência (atalho load + check)."""
    return check_consistency(load_spec(path))
