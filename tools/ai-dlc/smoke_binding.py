"""Smoke test REAL do binding — 1 requisição por perfil via API OpenRouter.

Valida contra a API viva: slug do modelo (incl. alias `~`), reasoning
effort, whitelist de endpoint tags (provider.only) e quantização.

Uso: python smoke_binding.py
Key: lida de OPENROUTER_API_KEY (process env) ou do registro do usuário
Windows (HKCU\\Environment, via `setx`). NUNCA é impressa nem gravada.

Custo: 4 chamadas curtas (~64 tokens de saída cada).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from ai_dlc_orchestrator import CRITIC_PROFILE, MODEL_PROFILES, ModelProfile

API_URL = "https://openrouter.ai/api/v1/chat/completions"
SMOKE_MAX_TOKENS = 64  # custo mínimo; binding real (4096+) só na fase 2


def _read_key() -> str:
    value = __import__("os").getenv("OPENROUTER_API_KEY", "").strip()
    if value:
        return value
    try:  # Windows: `setx` grava em HKCU\Environment
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            saved, _ = winreg.QueryValueEx(key, "OPENROUTER_API_KEY")
            return str(saved).strip()
    except OSError:
        return ""


def _smoke(profile: ModelProfile, api_key: str) -> tuple[bool, str]:
    """Executa 1 chamada de chat e retorna (ok, detalhe)."""
    body = {
        "model": profile.resolve_model(),
        "messages": [{"role": "user", "content": "Responda apenas: ok"}],
        "temperature": profile.temperature,
        "max_tokens": SMOKE_MAX_TOKENS,
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
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        provider = data.get("provider", "?")
        model = data.get("model", "?")
        usage = data.get("usage", {})
        detail = (
            f"provider={provider} model={model} "
            f"tokens={usage.get('total_tokens', '?')}"
        )
        return True, detail
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode("utf-8")).get("error", {})
            detail = f"HTTP {exc.code}: {message.get('message', message)}"
        except Exception:  # noqa: BLE001
            detail = f"HTTP {exc.code}"
        return False, detail
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    api_key = _read_key()
    if not api_key:
        print("ERRO: OPENROUTER_API_KEY ausente (env ou registro HKCU).")
        return 2

    profiles = [*MODEL_PROFILES.values(), CRITIC_PROFILE]
    failures = 0
    for profile in profiles:
        ok, detail = _smoke(profile, api_key)
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {profile.name}: {detail}")
        if not ok:
            failures += 1

    total = len(profiles)
    print(f"\n{total - failures}/{total} perfis validados com chamada real.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
