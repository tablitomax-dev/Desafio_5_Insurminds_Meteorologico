"""Testes do step pre_merge_quality_repair — Fase 1 (read_only_assess).

Cobertura: decisão (approved/blocked), classificação de falhas, artefatos
por run_id, detecção de stacked PR e exit codes da CLI.
Checks e git rodam via funções injetáveis — nenhum teste toca rede ou disco
fora de tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pre_merge_check as pmc


def _fake_ctx() -> pmc.PRContext:
    return pmc.PRContext(
        repository="Desafio_5_Insurminds_Meteorologico",
        head_branch="feature/test",
        base_branch="origin/main",
        head_sha="abc123def456789",
        base_sha="def4567890abc12",
        changed_files=("app/pipeline.py", "tests/test_pipeline.py"),
        expected_checks=("lint", "type_check", "unit_tests"),
        is_stacked_pr=False,
        parent_branch=None,
    )


def _runner_all_green(command: pmc.CheckCommand, root: Path) -> pmc.CheckResult:
    return pmc.CheckResult(command.name, True, 0, "ok")


def _runner_lint_fails(command: pmc.CheckCommand, root: Path) -> pmc.CheckResult:
    if command.name == "lint":
        return pmc.CheckResult("lint", False, 1, "F401 unused import 'os'")
    return pmc.CheckResult(command.name, True, 0, "ok")


def _runner_multi_fails(command: pmc.CheckCommand, root: Path) -> pmc.CheckResult:
    if command.name == "lint":
        return pmc.CheckResult("lint", False, 1, "F401 unused import 'os'")
    if command.name == "type_check":
        return pmc.CheckResult(
            "type_check", False, 1, "Incompatible types in assignment"
        )
    return pmc.CheckResult(command.name, True, 0, "ok")


def _fake_git(root: Path, args) -> str:
    if args[0] == "rev-parse" and args[1] == "--abbrev-ref":
        return "feature/test"
    if args[0] == "rev-parse" and args[1] == "HEAD":
        return "abc123def456789"
    if args[0] == "rev-parse":
        return "def4567890abc12"
    if args[0] == "diff":
        return "app/pipeline.py\ntests/test_pipeline.py"
    if args[0] == "remote":
        return "https://github.com/tablitomax-dev/Desafio_5_Insurminds_Meteorologico.git"
    raise AssertionError(f"git args inesperados: {args}")


def test_decide_approved_when_all_checks_pass() -> None:
    verdict = pmc.decide({"lint": "passed", "type_check": "passed", "unit_tests": "passed"})
    assert verdict["status"] == "approved_for_merge"
    assert verdict["reason"] == "all_required_checks_green"
    assert verdict["failed_checks"] == []


def test_decide_blocked_when_check_fails() -> None:
    verdict = pmc.decide({"lint": "failed", "type_check": "passed", "unit_tests": "passed"})
    assert verdict["status"] == "blocked"
    assert verdict["reason"] == "required_checks_failed"
    assert verdict["failed_checks"] == ["lint"]


def test_gate_collects_statuses(tmp_path: Path) -> None:
    status_map, results = pmc.run_quality_gate(tmp_path, runner=_runner_lint_fails)
    assert status_map["lint"] == "failed"
    assert status_map["type_check"] == "passed"
    assert status_map["unit_tests"] == "passed"
    assert len(results) == 3


def test_failure_report_classifies_by_category_and_severity() -> None:
    _, results = pmc.run_quality_gate(Path("."), runner=_runner_multi_fails)
    failures = pmc.build_failure_report(results)
    lint = next(f for f in failures if f["name"] == "lint")
    assert lint["category"] == "lint_format"
    assert lint["severity"] == "S1"
    assert lint["diagnostic_confidence"] == "high"
    assert any("F401" in ev for ev in lint["evidence"])
    type_check = next(f for f in failures if f["name"] == "type_check")
    assert type_check["category"] == "type_error"


def test_artifacts_written_per_run_id(tmp_path: Path) -> None:
    ctx = _fake_ctx()
    status_map, results = pmc.run_quality_gate(tmp_path, runner=_runner_lint_fails)
    verdict = pmc.decide(status_map)
    run_dir = pmc.write_artifacts(tmp_path, "pmqr-test", ctx, status_map, results, verdict)
    assert run_dir == tmp_path / "tools" / "ai-dlc" / "runs" / "pre-merge-quality-repair" / "pmqr-test"
    final = json.loads((run_dir / "final_decision.json").read_text(encoding="utf-8"))
    assert final["status"] == "blocked"
    assert final["head_sha"] == "abc123def456789"
    assert final["execution_mode"] == "read_only_assess"
    assert final["checks"]["lint"] == "failed"
    quality = json.loads((run_dir / "quality_report.initial.json").read_text(encoding="utf-8"))
    assert quality["all_required_green"] is False
    failures = json.loads((run_dir / "failure_report.attempt-1.json").read_text(encoding="utf-8"))
    assert failures["attempt"] == 1
    assert failures["failed_checks"][0]["name"] == "lint"
    ctx_saved = json.loads((run_dir / "pr_context.json").read_text(encoding="utf-8"))
    assert ctx_saved["is_stacked_pr"] is False
    log = (run_dir / "execution_log.md").read_text(encoding="utf-8")
    assert "prepare_context -> validate_quality -> decide" in log
    assert "blocked" in log


def test_no_failure_report_when_approved(tmp_path: Path) -> None:
    ctx = _fake_ctx()
    status_map, results = pmc.run_quality_gate(tmp_path, runner=_runner_all_green)
    verdict = pmc.decide(status_map)
    run_dir = pmc.write_artifacts(tmp_path, "pmqr-ok", ctx, status_map, results, verdict)
    assert not (run_dir / "failure_report.attempt-1.json").exists()
    final = json.loads((run_dir / "final_decision.json").read_text(encoding="utf-8"))
    assert final["status"] == "approved_for_merge"
    assert final["merge_recommendation"]["allowed"] is True


def test_stacked_pr_detection(tmp_path: Path) -> None:
    ctx = pmc.load_context(tmp_path, "feature/002-domain-core", git_fn=_fake_git)
    assert ctx.is_stacked_pr is True
    assert ctx.parent_branch == "feature/002-domain-core"
    ctx_main = pmc.load_context(tmp_path, "origin/main", git_fn=_fake_git)
    assert ctx_main.is_stacked_pr is False
    assert ctx_main.parent_branch is None


def test_load_context_parses_git(tmp_path: Path) -> None:
    ctx = pmc.load_context(tmp_path, "origin/main", git_fn=_fake_git)
    assert ctx.head_branch == "feature/test"
    assert ctx.head_sha == "abc123def456789"
    assert ctx.repository == "Desafio_5_Insurminds_Meteorologico"
    assert ctx.changed_files == ("app/pipeline.py", "tests/test_pipeline.py")
    assert ctx.expected_checks == ("lint", "type_check", "unit_tests")


def test_cli_blocked_returns_one(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pmc, "load_context", lambda root, base, git_fn=None: _fake_ctx())
    status_map, results = pmc.run_quality_gate(tmp_path, runner=_runner_lint_fails)
    monkeypatch.setattr(pmc, "run_quality_gate", lambda root: (status_map, results))
    code = pmc.main(["--root", str(tmp_path), "--run-id", "pmqr-cli-block"])
    assert code == 1


def test_cli_approved_returns_zero(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pmc, "load_context", lambda root, base, git_fn=None: _fake_ctx())
    status_map, results = pmc.run_quality_gate(tmp_path, runner=_runner_all_green)
    monkeypatch.setattr(pmc, "run_quality_gate", lambda root: (status_map, results))
    code = pmc.main(["--root", str(tmp_path), "--run-id", "pmqr-cli-ok"])
    assert code == 0