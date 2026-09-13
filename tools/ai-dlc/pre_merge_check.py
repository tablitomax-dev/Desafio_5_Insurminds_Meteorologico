"""Step ``pre_merge_quality_repair`` — Fase 1 (modo read_only_assess).

Valida os gates obrigatórios de qualidade da branch de um PR e emite uma
decisão auditável: ``approved_for_merge`` ou ``blocked``. Implementa a Fase 1
da spec (sem loop de reparo): observa, classifica e decide.

- Checks rodam localmente na working tree: ``ruff check .``, ``mypy app``,
  ``pytest`` — a fonte da verdade é o gate canônico do repo (``ruff.toml``,
  ``pytest.ini`` e ``.github/workflows/ci.yml``), não um provedor de CI externo.
- Artefatos por ``run_id`` em ``tools/ai-dlc/runs/pre-merge-quality-repair/``
  (locais, não versionados — mesmo padrão do ``runs.jsonl``).
- Exit: 0 = ``approved_for_merge``; 1 = ``blocked``.
- Escopo somente-leitura: nada é alterado na working tree; sem push e sem merge.

Spec de referência: tools/ai-dlc/spec_pre_merge_quality_repair.md

Uso:

    python tools/ai-dlc/pre_merge_check.py --base origin/main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# --- Contratos da Fase 1 -----------------------------------------------------

READ_ONLY_ASSESS = "read_only_assess"
STATE_TRANSITIONS = ("prepare_context -> validate_quality", "validate_quality -> decide")
MAIN_ALIASES = frozenset({"main", "origin/main"})
TAIL_LINES = 15
CHECK_TIMEOUT_S = 900.0

@dataclass(frozen=True)
class CheckCommand:
    """Um gate obrigatório: nome canônico + comando a executar."""

    name: str
    args: tuple[str, ...]

DEFAULT_CHECKS: tuple[CheckCommand, ...] = (
    CheckCommand("lint", (sys.executable, "-m", "ruff", "check", ".")),
    CheckCommand("type_check", (sys.executable, "-m", "mypy", "app")),
    CheckCommand("unit_tests", (sys.executable, "-m", "pytest")),
)

# Mapa canônico check -> (categoria, severidade) — spec, seção "Classificação de falhas".
CHECK_CATEGORIES: Mapping[str, tuple[str, str]] = {
    "lint": ("lint_format", "S1"),
    "type_check": ("type_error", "S1"),
    "unit_tests": ("unit_test_failure", "S1"),
}

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    exit_code: int
    tail: str

@dataclass(frozen=True)
class PRContext:
    repository: str
    head_branch: str
    base_branch: str
    head_sha: str
    base_sha: str
    changed_files: tuple[str, ...]
    expected_checks: tuple[str, ...]
    is_stacked_pr: bool
    parent_branch: str | None

# --- Contexto do PR (prepare_context) -----------------------------------------

GitFn = Callable[[Path, Sequence[str]], str]

def _git(root: Path, args: Sequence[str]) -> str:
    proc = subprocess.run(
        ("git", *args), cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} falhou (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout.strip()

def load_context(
    root: Path, base_branch: str, *, git_fn: GitFn | None = None
) -> PRContext:
    """Monta o contexto operacional do PR a partir do repositório local."""
    git = git_fn if git_fn is not None else _git
    head_branch = git(root, ("rev-parse", "--abbrev-ref", "HEAD"))
    head_sha = git(root, ("rev-parse", "HEAD"))
    base_sha = git(root, ("rev-parse", base_branch))
    changed_raw = git(root, ("diff", "--name-only", f"{base_sha}...{head_sha}"))
    try:
        remote = git(root, ("remote", "get-url", "origin"))
        repository = remote.rstrip("/").rsplit("/", 1)[-1]
        if repository.endswith(".git"):
            repository = repository[: -len(".git")]
    except RuntimeError:
        repository = "unknown"
    is_stacked = base_branch not in MAIN_ALIASES
    return PRContext(
        repository=repository,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        base_sha=base_sha,
        changed_files=tuple(line for line in changed_raw.splitlines() if line),
        expected_checks=tuple(check.name for check in DEFAULT_CHECKS),
        is_stacked_pr=is_stacked,
        parent_branch=base_branch if is_stacked else None,
    )

# --- Validação de qualidade (validate_quality) ----------------------------------

def run_check(command: CheckCommand, root: Path) -> CheckResult:
    """Executa um check obrigatório e captura evidência (cauda da saída)."""
    try:
        proc = subprocess.run(
            command.args,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CHECK_TIMEOUT_S,
        )
        output = f"{proc.stdout}\n{proc.stderr}"
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=command.name,
            passed=False,
            exit_code=-1,
            tail=f"check {command.name} excedeu {CHECK_TIMEOUT_S:.0f}s",
        )
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    return CheckResult(
        name=command.name,
        passed=exit_code == 0,
        exit_code=exit_code,
        tail="\n".join(lines[-TAIL_LINES:]),
    )

def run_quality_gate(
    root: Path,
    checks: Sequence[CheckCommand] = DEFAULT_CHECKS,
    *,
    runner: Callable[[CheckCommand, Path], CheckResult] = run_check,
) -> tuple[dict[str, str], tuple[CheckResult, ...]]:
    """Roda TODOS os gates obrigatórios (nunca só o que falhou na rodada anterior)."""
    results = tuple(runner(check, root) for check in checks)
    status_map = {result.name: "passed" if result.passed else "failed" for result in results}
    return status_map, results

def build_failure_report(results: Sequence[CheckResult]) -> list[dict[str, object]]:
    """Classifica falhas por categoria/severidade com evidência diagnosticável."""
    failures: list[dict[str, object]] = []
    for result in results:
        if result.passed:
            continue
        category, severity = CHECK_CATEGORIES.get(result.name, ("unknown", "S1"))
        failures.append(
            {
                "name": result.name,
                "category": category,
                "severity": severity,
                "diagnostic_confidence": "high",
                "summary": f"check {result.name} falhou (exit {result.exit_code})",
                "evidence": [result.tail] if result.tail else [],
            }
        )
    return failures

# --- Decisão (decide) ------------------------------------------------------------

def decide(status_map: Mapping[str, str]) -> dict[str, object]:
    """Decisão estruturada: aprovado somente com TODOS os gates verdes."""
    failed = sorted(name for name, status in status_map.items() if status != "passed")
    if not failed:
        return {
            "status": "approved_for_merge",
            "reason": "all_required_checks_green",
            "failed_checks": [],
        }
    return {"status": "blocked", "reason": "required_checks_failed", "failed_checks": failed}

# --- Persistência de artefatos (Audit Logger) --------------------------------------

def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def _write_log(
    path: Path,
    run_id: str,
    context: PRContext,
    status_map: Mapping[str, str],
    verdict: Mapping[str, object],
) -> None:
    checks_md = "; ".join(f"{name}={status}" for name, status in sorted(status_map.items()))
    stacked_md = f"{context.is_stacked_pr}"
    if context.parent_branch:
        stacked_md += f" (parent: {context.parent_branch})"
    lines = [
        "# Step pre_merge_quality_repair — Fase 1 (read_only_assess)",
        "",
        f"- run_id: `{run_id}`",
        f"- gerado em: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- repositório: {context.repository}",
        f"- head: {context.head_branch} ({context.head_sha[:7]})",
        f"- base: {context.base_branch} ({context.base_sha[:7]})",
        f"- stacked PR: {stacked_md}",
        f"- arquivos alterados: {len(context.changed_files)}",
        "- transições: prepare_context -> validate_quality -> decide",
        f"- checks: {checks_md}",
        f"- decisão: **{verdict['status']}** ({verdict['reason']})",
        "- invariantes: execução read-only; nenhuma alteração na working tree; sem push/merge.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

def write_artifacts(
    root: Path,
    run_id: str,
    context: PRContext,
    status_map: Mapping[str, str],
    results: Sequence[CheckResult],
    verdict: Mapping[str, object],
) -> Path:
    """Persiste a trilha completa da execução — 1 diretório por run_id."""
    run_dir = root / "tools" / "ai-dlc" / "runs" / "pre-merge-quality-repair" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "pr_context.json", asdict(context))
    failures = build_failure_report(results)
    all_green = verdict["status"] == "approved_for_merge"
    _write_json(
        run_dir / "quality_report.initial.json",
        {
            "head_sha": context.head_sha,
            "checks": dict(status_map),
            "failures": failures,
            "all_required_green": all_green,
        },
    )
    if failures:
        _write_json(
            run_dir / "failure_report.attempt-1.json",
            {
                "attempt": 1,
                "head_sha": context.head_sha,
                "failed_checks": failures,
                "global_assessment": "read_only_phase1_no_repair",
            },
        )
    final = {
        "step": "pre_merge_quality_repair",
        "execution_mode": READ_ONLY_ASSESS,
        "status": verdict["status"],
        "reason": verdict["reason"],
        "attempt_count": 0,
        "head_sha": context.head_sha,
        "checks": dict(status_map),
        "critic_final_verdict": "not_applicable_read_only",
        "merge_recommendation": {"allowed": verdict["status"] == "approved_for_merge"},
    }
    _write_json(run_dir / "final_decision.json", final)
    _write_log(run_dir / "execution_log.md", run_id, context, status_map, verdict)
    return run_dir

# --- CLI -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Step pre_merge_quality_repair — Fase 1 (read_only_assess): "
            "valida os gates obrigatórios de qualidade e emite decisão auditável."
        )
    )
    parser.add_argument(
        "--base",
        default="origin/main",
        help="branch base do PR (para PR stacked, usar a branch pai)",
    )
    parser.add_argument("--root", default=".", help="raiz do repositório (default: .)")
    parser.add_argument(
        "--run-id", default=None, help="run_id explícito (default: pmqr-<UTC>-<head_sha7>)"
    )
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    context = load_context(root, args.base)
    status_map, results = run_quality_gate(root)
    verdict = decide(status_map)
    run_id = args.run_id or (
        f"pmqr-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{context.head_sha[:7]}"
    )
    run_dir = write_artifacts(root, run_id, context, status_map, results, verdict)
    failed = ", ".join(str(item) for item in verdict["failed_checks"]) or "nenhum"
    print(f"[pre_merge_check] run={run_id} status={verdict['status']} failed_checks={failed}")
    print(f"[pre_merge_check] artefatos em: {run_dir}")
    return 0 if verdict["status"] == "approved_for_merge" else 1

if __name__ == "__main__":
    raise SystemExit(main())