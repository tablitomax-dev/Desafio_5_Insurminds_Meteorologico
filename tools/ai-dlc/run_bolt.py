r"""Runner de bolt — executa o run_loop do AI-DLC (ADR-006) com estado REAL.

Fase 2+ (uso por bolt): o executor LLM recebe o estado objetivo do
repositório (saída real do pytest, arquivos alterados) e propõe uma
ExecutorProposal FIEL; o `verify` injetado roda a suíte de verdade;
o crítico independente (CRITIC_PROFILE) gateia a proposta. O run é
auditado em runs.jsonl (fonte do dashboard).

O loop não pausa entre iterações: orquestre iteração a iteração
(`--max-iterations 1`, correção humana, novo run) — cada run audita.

Uso (PowerShell):
  python tools/ai-dlc/run_bolt.py `
    --task-id bolt-002-1-domain-core `
    --objective "Implementar o núcleo de domínio..." `
    --criteria "Regras 100% cobertas por testes" --criteria "Núcleo sem I/O" `
    --files 13 --risk low
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ai_dlc_orchestrator import (
    _extract_json,
    _message_content,
    call_independent_critic_real,
    run_loop,
)
from contracts import ExecutorProposal, TaskContext
from cost_report import generate_cost_report, report_markdown
from openrouter_client import (
    OpenRouterError,
    chat,
    missing_credentials_decision,
    read_api_key,
)

DEFAULT_TESTS_CMD = "python -m pytest tests -q --no-header -p no:cacheprovider"


def _run_tests(tests_cmd: str) -> tuple[bool, str]:
    """Roda a suíte de verdade; devolve (verde, tail da saída)."""
    try:
        proc = subprocess.run(
            tests_cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"falha ao executar testes: {exc}"
    combined = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(combined.strip().splitlines()[-30:])
    return proc.returncode == 0, tail


def _repo_state(tests_cmd: str) -> str:
    """Estado objetivo: pytest real + arquivos alterados (git)."""
    green, tail = _run_tests(tests_cmd)
    files = ""
    try:
        status = subprocess.run(
            "git status --porcelain",
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        files = (status.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return (
        "ESTADO REAL DO REPOSITÓRIO (fonte da verdade, não confie em suposições):\n"
        f"pytest verde: {green}\n"
        f"saída do pytest (tail):\n{tail}\n\n"
        f"arquivos alterados (git status --porcelain):\n{files or '(nenhum)'}"
    )


EXECUTOR_BOLT_PROMPT = (
    "Você é o executor do loop AI-DLC (ADR-006) operando um bolt real. "
    "Responda SOMENTE com um objeto JSON válido, sem texto fora do JSON, "
    "com as chaves: summary (string), changed_files (array de strings), "
    "tests_pass (boolean), acceptance_criteria_met (boolean), notes (array "
    "de strings). SEJA FIEL ao estado real fornecido: tests_pass só pode "
    "ser true se o pytest estiver verde; acceptance_criteria_met só pode "
    "ser true se TODOS os critérios estiverem atendidos pelo estado real. "
    "Use notes para evidências (contagem de testes, critérios verificados) "
    "e para listar lacunas."
)


def make_executor_fn(tests_cmd: str, api_key: str | None):
    """Executor real com estado objetivo injetado no prompt."""

    def executor_fn(ctx: TaskContext, iteration: int, profile) -> ExecutorProposal:
        state = _repo_state(tests_cmd)
        prompt_user = (
            f"Tarefa {ctx.task_id}: {ctx.objective}\n"
            "Critérios de aceite:\n- " + "\n- ".join(ctx.acceptance_criteria)
            + f"\n\nIteração {iteration}.\n\n{state}"
        )
        try:
            data = chat(
                profile,
                [
                    {"role": "system", "content": EXECUTOR_BOLT_PROMPT},
                    {"role": "user", "content": prompt_user},
                ],
                api_key=api_key,
            )
        except OpenRouterError as exc:
            return ExecutorProposal(
                stub=False,
                summary=f"[erro de transporte] iteração {iteration} de {ctx.task_id}",
                tests_pass=False,
                acceptance_criteria_met=False,
                notes=[f"OpenRouterError: {exc}"],
            )
        usage, model, provider = (
            data.get("usage"),
            data.get("model"),
            data.get("provider"),
        )
        obj = _extract_json(_message_content(data))
        if obj is None:
            return ExecutorProposal(
                stub=False,
                summary=f"[resposta não-JSON] iteração {iteration} de {ctx.task_id}",
                tests_pass=False,
                acceptance_criteria_met=False,
                notes=["conteúdo sem JSON parseável"],
                model=model,
                provider=provider,
                usage=usage,
            )
        return ExecutorProposal(
            stub=False,
            summary=str(obj.get("summary", "")),
            changed_files=[str(f) for f in obj.get("changed_files", []) if f],
            tests_pass=bool(obj.get("tests_pass", False)),
            acceptance_criteria_met=bool(obj.get("acceptance_criteria_met", False)),
            notes=[str(n) for n in obj.get("notes", []) if n],
            model=model,
            provider=provider,
            usage=usage,
        )

    return executor_fn


def make_verify_fn(tests_cmd: str):
    """Verify real: stop rule ancorada na suíte pytest de verdade."""

    def verify(ctx: TaskContext, proposal: ExecutorProposal) -> bool:
        green, _ = _run_tests(tests_cmd)
        return green and proposal.tests_pass

    return verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runner de bolt do AI-DLC")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--criteria", action="append", required=True)
    parser.add_argument("--files", type=int, default=1)
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--tests-cmd", default=DEFAULT_TESTS_CMD)
    parser.add_argument(
        "--audit",
        default=str(Path(__file__).resolve().parent / "runs.jsonl"),
    )
    args = parser.parse_args(argv)

    api_key = read_api_key()
    if not api_key:
        decision = missing_credentials_decision(
            evidence=["run_bolt: OPENROUTER_API_KEY ausente (env e registro)"]
        )
        print(decision.model_dump_json(indent=2))
        return 2

    ctx = TaskContext(
        task_id=args.task_id,
        objective=args.objective,
        acceptance_criteria=args.criteria,
        files_involved=max(1, args.files),
        risk=args.risk,
    )

    result = run_loop(
        ctx,
        verify=make_verify_fn(args.tests_cmd),
        executor_fn=make_executor_fn(args.tests_cmd, api_key),
        critic_fn=lambda proposal: call_independent_critic_real(
            proposal, api_key=api_key
        ),
        max_iterations=max(1, args.max_iterations),
        audit_path=args.audit,
    )

    print(
        f"status={result.status} iterations={result.iterations} "
        f"level={result.level.name} profile={result.profile} "
        f"blocker={result.blocker_type.value if result.blocker_type else 'none'}"
    )
    for record in result.records:
        if record.executor is not None:
            print(f"  it={record.iteration} outcome={record.outcome}")
            print(f"    summary: {record.executor.summary}")
            for note in record.executor.notes[:6]:
                print(f"    note: {note}")
        if record.critic is not None:
            print(
                f"    critic: {record.critic.verdict} — {record.critic.reason}"
            )
            for risk_note in record.critic.risk_notes[:6]:
                print(f"    risk: {risk_note}")
    print(report_markdown(generate_cost_report([result])))
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
