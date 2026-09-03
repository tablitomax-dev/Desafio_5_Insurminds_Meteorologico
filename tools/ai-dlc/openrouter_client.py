"""Cliente OpenRouter (fase 2) — urllib stdlib, sem SDK.

Transporte único do executor e do crítico reais. Reutiliza o padrão
validado pelo smoke_binding.py (binding conferido na API viva):
model slug (alias `~`), reasoning.effort, provider.only (whitelist de
endpoint tags) e quantizations.

Key: OPENROUTER_API_KEY do process env ou do registro do usuário
Windows (HKCU\\Environment via `setx`). NUNCA é impressa nem gravada.

Falha sem key → OpenRouterError (e `missing_credentials_decision()`
fornece o CapacityDecision correspondente ao contrato de capacidade).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from contracts import BlockerType, CapacityDecision, ModelProfile

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT = 120


class OpenRouterError(RuntimeError):
    """Falha de transporte/autenticação na chamada ao OpenRouter."""


def read_api_key(use_registry: bool = True) -> str:
    """Lê a key do env; opcionalmente do registro Windows (HKCU)."""
    value = os.getenv("OPENROUTER_API_KEY", "").strip()
    if value:
        return value
    if not use_registry:
        return ""
    try:  # Windows: `setx` grava em HKCU\Environment
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            saved, _ = winreg.QueryValueEx(key, "OPENROUTER_API_KEY")
            return str(saved).strip()
    except (OSError, ImportError):
        return ""


def chat(
    profile: ModelProfile,
    messages: list[dict],
    *,
    api_key: "str | None" = None,
    max_tokens: "int | None" = None,
    timeout: int = DEFAULT_TIMEOUT,
    use_registry_key: bool = True,
) -> dict:
    """1 chamada de chat/completions; retorna a resposta JSON crua."""
    key = api_key if api_key is not None else read_api_key(use_registry_key)
    if not key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY ausente (env ou registro HKCU) — "
            "use missing_credentials_decision() para o gate humano"
        )

    body: dict = {
        "model": profile.resolve_model(),
        "messages": list(messages),
        "temperature": profile.temperature,
        "max_tokens": max_tokens if max_tokens is not None else profile.max_tokens,
    }
    if profile.reasoning_effort:
        body["reasoning"] = {"effort": profile.reasoning_effort}
    policy = profile.provider_policy()
    if policy:
        body["provider"] = policy

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode("utf-8")).get("error", {})
            detail = message.get("message", message) if isinstance(message, dict) else message
        except Exception:  # noqa: BLE001 — corpo ilegível: mantém só o código
            detail = ""
        raise OpenRouterError(f"HTTP {exc.code}: {detail}".rstrip()) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OpenRouterError(f"{type(exc).__name__}: {exc}") from exc


def missing_credentials_decision(evidence: "list[str] | None" = None) -> CapacityDecision:
    """CapacityDecision canônica para key ausente (contrato de capacidade)."""
    return CapacityDecision(
        status="blocked",
        confidence=1.0,
        can_continue_autonomously=False,
        blocker_type=BlockerType.missing_credentials,
        evidence=evidence or ["OPENROUTER_API_KEY não configurada no ambiente"],
        required_human_input=[
            "definir a key: `setx OPENROUTER_API_KEY \"sk-or-...\"` em um "
            "PowerShell próprio (ou export no shell do processo) e reabrir o terminal"
        ],
        safe_next_actions=[
            "validar o binding com `python tools/ai-dlc/smoke_binding.py` após configurar"
        ],
    )
