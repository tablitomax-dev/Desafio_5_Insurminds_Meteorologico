"""Relatório de custo/tokens (fase 2) — agrega `usage` dos records.

Fonte: records de LoopResult (executor = perfil do run; crítico =
perfil `critic`). Campos numéricos padrão do OpenRouter: prompt_tokens,
completion_tokens, total_tokens, cost (quando disponível).
"""

from __future__ import annotations

from collections.abc import Iterable

from contracts import LoopResult

_EMPTY_BUCKET: dict = {
    "calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "cost": 0.0,
}


def _accumulate(bucket: dict, usage: dict) -> None:
    bucket["calls"] += 1
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key, 0)
        bucket[key] += int(value) if isinstance(value, (int, float)) else 0
    cost = usage.get("cost", 0)
    bucket["cost"] += float(cost) if isinstance(cost, (int, float)) else 0.0


def generate_cost_report(results: Iterable[LoopResult]) -> dict[str, dict]:
    """Agrega tokens/custo por perfil; {} quando nenhum usage presente."""
    stats: dict[str, dict] = {}
    for result in results:
        for record in result.records:
            if record.executor is not None and record.executor.usage:
                _accumulate(
                    stats.setdefault(record.profile, dict(_EMPTY_BUCKET)),
                    record.executor.usage,
                )
            if record.critic is not None and record.critic.usage:
                _accumulate(
                    stats.setdefault("critic", dict(_EMPTY_BUCKET)),
                    record.critic.usage,
                )
    return dict(sorted(stats.items()))


def report_markdown(report: dict[str, dict]) -> str:
    """Renderiza a tabela markdown do relatório (com linha TOTAL)."""
    lines = [
        "# Relatório de custo (tokens por perfil)",
        "",
        "| perfil | chamadas | prompt | completion | total | custo |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    total_calls, total_tokens, total_cost = 0, 0, 0.0
    for name, row in report.items():
        lines.append(
            f"| {name} | {row['calls']} | {row['prompt_tokens']} | "
            f"{row['completion_tokens']} | {row['total_tokens']} | {row['cost']:.6f} |"
        )
        total_calls += row["calls"]
        total_tokens += row["total_tokens"]
        total_cost += row["cost"]
    lines.append(
        f"| **TOTAL** | {total_calls} | — | — | {total_tokens} | {total_cost:.6f} |"
    )
    return "\n".join(lines) + "\n"
