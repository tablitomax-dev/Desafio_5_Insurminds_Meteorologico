"""Pipeline de rodada — stories 01 e 07 (unit pipeline-cli).

Orquestra as etapas do enunciado: coleta por segurado → detecção de
risco → mensagem → envio simulado. Sem I/O próprio: recebe ports
prontas (composition root é a CLI). Falha de coleta registra e
continua com os demais (story 01).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.messages import GeneratedMessage, MessageGenerator
from app.domain.notify import NotificationSender
from app.domain.ports import (
    PolicyHolderRepository,
    WeatherProvider,
    WeatherProviderError,
)
from app.domain.risk import RiskAlert, RiskEngine, RiskKind
from app.domain.weather import WeatherSnapshot


@dataclass(frozen=True)
class CollectionFailure:
    """Falha de coleta de um segurado (story 01: registrada, sem crash)."""

    holder_id: str
    reason: str


@dataclass(frozen=True)
class RoundReport:
    """Resultado consolidado de uma rodada (fonte do relatório)."""

    holders_consulted: int
    failures: tuple[CollectionFailure, ...]
    alerts: tuple[RiskAlert, ...]
    messages: tuple[GeneratedMessage, ...]
    sends: tuple  # tuple[NotificationRecord, ...]


def run_round(
    repository: PolicyHolderRepository,
    provider: WeatherProvider,
    engine: RiskEngine,
    generator: MessageGenerator,
    sender: NotificationSender,
) -> RoundReport:
    """Executa uma rodada completa para todos os segurados do catálogo."""
    alerts: list[RiskAlert] = []
    messages: list[GeneratedMessage] = []
    sends: list = []
    failures: list[CollectionFailure] = []
    consulted = 0

    for holder in repository.list_all():
        try:
            snapshot: WeatherSnapshot = provider.current(holder.location)
        except WeatherProviderError as exc:  # story 01: segue com os demais
            failures.append(
                CollectionFailure(holder_id=holder.id, reason=str(exc))
            )
            continue
        consulted += 1
        for alert in engine.evaluate(snapshot, holder):
            alerts.append(alert)
            message = generator.generate(holder, alert)
            messages.append(message)
            sends.append(sender.send(holder, message))

    return RoundReport(
        holders_consulted=consulted,
        failures=tuple(failures),
        alerts=tuple(alerts),
        messages=tuple(messages),
        sends=tuple(sends),
    )


def format_report(report: RoundReport, *, generator_name: str = "template") -> str:
    """Relatório da rodada em 5 seções legíveis para banca (story 07)."""
    lines: list[str] = [
        "=== Relatório da rodada — comunicação proativa com o segurado ===",
        f"1. Segurados consultados: {report.holders_consulted} "
        f"(falhas de coleta: {len(report.failures)})",
    ]
    if report.failures:
        for failure in report.failures:
            lines.append(f"   - FALHA [{failure.holder_id}]: {failure.reason}")

    lines.append(f"2. Eventos detectados: {len(report.alerts)}")
    by_kind: dict[RiskKind, int] = {}
    for alert in report.alerts:
        by_kind[alert.kind] = by_kind.get(alert.kind, 0) + 1
    for kind, count in sorted(by_kind.items()):
        lines.append(f"   - {kind.value}: {count}")

    lines.append("3. Alertas por regra:")
    if not report.alerts:
        lines.append("   - nenhum evento de risco nesta rodada")
    for alert in report.alerts:
        lines.append(
            f"   - [{alert.holder_id}] {alert.kind.value} "
            f"({alert.severity.value}): {alert.reason}"
        )

    lines.append(f"4. Mensagens geradas: {len(report.messages)} (modo {generator_name})")
    lines.append(f"5. Envios simulados: {len(report.sends)}")
    for send in report.sends:
        lines.append(
            f"   [SIMULADO] {send.channel} -> segurado {send.holder_id} "
            f"({send.status})"
        )
    return "\n".join(lines)
