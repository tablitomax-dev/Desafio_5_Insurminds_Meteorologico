r"""Smoke REAL da fase 2 — loop completo com executor e crítico via OpenRouter.

Valida ponta a ponta: classify → executor real (code_fast, JSON) →
verify → crítico real (openai/gpt-5.6-luna-pro, endpoint openai/flex)
→ stop rule. Custo mínimo (task trivial, 1 iteração esperada).

Uso: python smoke_phase2.py
Key: OPENROUTER_API_KEY (env) ou registro Windows HKCU\Environment.
NUNCA é impressa nem gravada.
"""

from __future__ import annotations

import sys

from ai_dlc_orchestrator import TaskContext, real_functions, run_loop
from openrouter_client import missing_credentials_decision, read_api_key


def main() -> int:
    if not read_api_key():
        print("ERRO: OPENROUTER_API_KEY ausente (env ou registro HKCU).")
        print(missing_credentials_decision().model_dump_json(indent=2))
        return 2

    ctx = TaskContext(
        task_id="smoke-fase2",
        objective="Confirmar pipeline real respondendo ao contrato JSON do executor",
        acceptance_criteria=["JSON válido com tests_pass=true"],
    )
    fns = real_functions()  # key lida de env/registro; nunca impressa
    result = run_loop(
        ctx, executor_fn=fns["executor_fn"], critic_fn=fns["critic_fn"]
    )

    print(
        f"status={result.status} iterations={result.iterations} "
        f"level=N{int(result.level)} profile={result.profile}"
    )
    for record in result.records:
        print(f"  it={record.iteration} outcome={record.outcome}")
        if record.executor is not None:
            print(
                f"    executor: model={record.executor.model} "
                f"provider={record.executor.provider} usage={record.executor.usage}"
            )
        if record.critic is not None:
            print(
                f"    critic:   verdict={record.critic.verdict} "
                f"model={record.critic.model} provider={record.critic.provider} "
                f"usage={record.critic.usage}"
            )

    print("\nSMOKE OK" if result.status == "success" else "\nSMOKE FAIL")
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
