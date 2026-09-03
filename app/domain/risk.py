"""Motor de regras de risco — unit risk-detection (NÚCLEO TDD).

Regras puras, declarativas e sem I/O (criterio de aceite 3 do intent):
dado WeatherSnapshot + PolicyHolder → Optional[RiskAlert].
Limiares em constantes configuráveis para casar com as stories 02–04.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.weather import WeatherCondition, WeatherSnapshot

# Limiares das stories (configuráveis por regra no __init__).
HEAVY_RAIN_MM_H: float = 10.0  # story 02: ex.: 10 mm/h
STRONG_WIND_KMH: float = 60.0  # story 04: ex.: 60 km/h


class RiskKind(str, Enum):
    """Tipo de risco detectado (espelha as regras do desafio)."""

    HEAVY_RAIN = "heavy_rain"
    HAIL = "hail"
    STRONG_WIND = "strong_wind"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RiskAlert:
    """Alerta de risco para um segurado, com tipo, severidade e motivo."""

    kind: RiskKind
    severity: Severity
    reason: str
    holder_id: str


class RiskRule(Protocol):
    """Port de regra: snapshot + segurado → alerta (ou nada)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None: ...


class HeavyRainRule:
    """Story 02: precipitação ≥ limiar → segurados RESIDENTIAL."""

    def __init__(self, threshold_mm_h: float = HEAVY_RAIN_MM_H):
        self.threshold_mm_h = threshold_mm_h

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.precipitation_mm_h < self.threshold_mm_h:
            return None
        if InsuranceType.RESIDENTIAL not in holder.insurance_types:
            return None
        return RiskAlert(
            kind=RiskKind.HEAVY_RAIN,
            severity=Severity.MEDIUM,
            reason=(
                f"precipitação de {snapshot.precipitation_mm_h:.1f} mm/h "
                f"(limiar {self.threshold_mm_h:.1f} mm/h)"
            ),
            holder_id=holder.id,
        )


class HailRule:
    """Story 03: weathercode de granizo → segurados AUTO."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.condition is not WeatherCondition.HAIL:
            return None
        if InsuranceType.AUTO not in holder.insurance_types:
            return None
        return RiskAlert(
            kind=RiskKind.HAIL,
            severity=Severity.HIGH,
            reason=f"granizo previsto (weathercode {snapshot.weathercode})",
            holder_id=holder.id,
        )


class StrongWindRule:
    """Story 04: vento ≥ limiar → segurados em região costeira."""

    def __init__(self, threshold_kmh: float = STRONG_WIND_KMH):
        self.threshold_kmh = threshold_kmh

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.wind_kmh < self.threshold_kmh:
            return None
        if not holder.is_coastal:
            return None
        return RiskAlert(
            kind=RiskKind.STRONG_WIND,
            severity=Severity.MEDIUM,
            reason=f"ventos de {snapshot.wind_kmh:.0f} km/h na região costeira",
            holder_id=holder.id,
        )


class RiskEngine:
    """Aplica todas as regras e deduplica por (holder_id, kind)."""

    def __init__(
        self,
        rules: Sequence[RiskRule] = (HeavyRainRule(), HailRule(), StrongWindRule()),
    ):
        self.rules: tuple[RiskRule, ...] = tuple(rules)

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> list[RiskAlert]:
        alerts: list[RiskAlert] = []
        seen: set[tuple[str, RiskKind]] = set()
        for rule in self.rules:
            alert = rule.evaluate(snapshot, holder)
            if alert is None:
                continue
            key = (alert.holder_id, alert.kind)
            if key in seen:
                continue
            seen.add(key)
            alerts.append(alert)
        return alerts
