"""Motor de regras de risco — unit risk-detection (NÚCLEO TDD).

Regras puras, declarativas e sem I/O (criterio de aceite 3 do intent):
dado WeatherSnapshot + PolicyHolder → list[RiskAlert].

V2 (intent 005 / ADR-009): preserva as stories 02–04 como tier base e
acrescenta tiers de severidade (chuva ≥20 HIGH / ≥35 VERY_HIGH; vento
≥80 VERY_HIGH), regras compostas (tempestade, ressaca) e novos tipos
(calor, onda de calor, frio, neblina). Com ≥2 riscos simultâneos, o
engine acrescenta UM resumo MULTIPLE_RISKS (severidade = máxima)
DEPOIS dos alertas individuais.

BATERIA PREVENTIVA (intent 008 / ADR-011, supersedes ADR-009): cada
regra dispara para os ramos COM EXPOSIÇÃO MATERIAL — chuva intensa e
granizo agora atingem AMBOS os ramos (casa e veículo têm danos típicos
próprios), vento atinge os dois ramos em QUALQUER região (emenda do
dono, 2026-09-13 — vendavais causam dano material fora do litoral) e a
ressaca segue restrita ao litoral; neblina permanece AUTO. Novas regras: tempo seco (umidade < 30%, LOW/MEDIUM) e
geada (≤ 0 °C, HIGH; ≤ −2 °C VERY_HIGH). O CONTEÚDO das mensagens vem
da bateria (`app.domain.risk_battery`, derivada de
`memory-bank/standards/tabela-alertas-preventiva.md`). O fallback por
perfil estatístico da planilha FICA FORA deste módulo (material de
referência em `analise/`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.weather import WeatherCondition, WeatherSnapshot

# Limiares das stories (tier base, configuráveis por regra no __init__).
HEAVY_RAIN_MM_H: float = 10.0  # story 02: ex.: 10 mm/h
STRONG_WIND_KMH: float = 60.0  # story 04: ex.: 60 km/h

# Tiers de escalonamento da V2 (intent 005).
HEAVY_RAIN_HIGH_MM_H: float = 20.0
VERY_HEAVY_RAIN_MM_H: float = 35.0
VERY_STRONG_WIND_KMH: float = 80.0
HEAT_C: float = 35.0
HEAT_WAVE_C: float = 38.0
EXTREME_COLD_C: float = 10.0
EXTREME_COLD_VERY_HIGH_C: float = 5.0
FOG_HUMIDITY_PCT: float = 95.0
FOG_HIGH_HUMIDITY_PCT: float = 98.0
FOG_MAX_WIND_KMH: float = 15.0
FOG_MAX_RAIN_MM_H: float = 10.0
STORM_RAIN_MM_H: float = 30.0
STORM_WIND_KMH: float = STRONG_WIND_KMH
ROUGH_SEA_WIND_KMH: float = VERY_STRONG_WIND_KMH
ROUGH_SEA_RAIN_MM_H: float = 30.0
# Bateria preventiva (intent 008 — tabela-alertas-preventiva.md).
LOW_HUMIDITY_PCT: float = 30.0
LOW_HUMIDITY_MEDIUM_PCT: float = 20.0
FROST_C: float = 0.0
FROST_VERY_HIGH_C: float = -2.0


class RiskKind(str, Enum):
    """Tipo de risco detectado (stories 02–04 + extensões da V2)."""

    HEAVY_RAIN = "heavy_rain"
    HAIL = "hail"
    STRONG_WIND = "strong_wind"
    HEAT = "heat"
    HEAT_WAVE = "heat_wave"
    EXTREME_COLD = "extreme_cold"
    FOG = "fog"
    STORM = "storm"
    ROUGH_SEA = "rough_sea"
    LOW_HUMIDITY = "low_humidity"
    FROST = "frost"
    MULTIPLE_RISKS = "multiple_risks"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.VERY_HIGH: 4,
}

# Escopo por ramo (ADRs 009 e 011): cada regra dispara para os ramos
# COM EXPOSIÇÃO MATERIAL ao risco. Bateria preventiva (intent 008):
# chuva intensa e granizo atingem AMBOS os ramos (casa e veículo têm
# danos típicos próprios); neblina permanece AUTO (risco do condutor);
# vento atinge os dois ramos em qualquer região (emenda do dono,
# 2026-09-13); a ressaca permanece geográfica (litoral).
_AUTO_OR_RESIDENTIAL: frozenset[InsuranceType] = frozenset(
    {InsuranceType.RESIDENTIAL, InsuranceType.AUTO}
)


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
    """Story 02 (tier base): precipitação ≥ limiar → RESIDENTIAL **ou**
    AUTO (bateria 008: alagamento/infiltração na casa; vias alagadas e
    garagens baixas no veículo). Escala com a chuva: ≥20 HIGH,
    ≥35 VERY_HIGH."""

    def __init__(self, threshold_mm_h: float = HEAVY_RAIN_MM_H):
        self.threshold_mm_h = threshold_mm_h

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.precipitation_mm_h < self.threshold_mm_h:
            return None
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.precipitation_mm_h >= VERY_HEAVY_RAIN_MM_H:
            severity = Severity.VERY_HIGH
        elif snapshot.precipitation_mm_h >= HEAVY_RAIN_HIGH_MM_H:
            severity = Severity.HIGH
        else:
            severity = Severity.MEDIUM
        return RiskAlert(
            kind=RiskKind.HEAVY_RAIN,
            severity=severity,
            reason=(
                f"precipitação de {snapshot.precipitation_mm_h:.1f} mm/h "
                f"(limiar {self.threshold_mm_h:.1f} mm/h)"
            ),
            holder_id=holder.id,
        )


class HailRule:
    """Story 03: weathercode de granizo → AUTO **ou** RESIDENTIAL
    (bateria 008: lataria/vidros no veículo; telhado, janelas e vidros
    na casa)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.condition is not WeatherCondition.HAIL:
            return None
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        return RiskAlert(
            kind=RiskKind.HAIL,
            severity=Severity.HIGH,
            reason=f"granizo previsto (weathercode {snapshot.weathercode})",
            holder_id=holder.id,
        )


class StrongWindRule:
    """Story 04 (tier base): vento ≥ limiar → RESIDENTIAL ou AUTO.
    EMENDA do dono (2026-09-13, ADR-011): o gate geográfico da story 04
    foi removido — vendavais causam dano material em qualquer região; o
    litoral segue como sinal exclusivo da RessacaRule. Escala:
    ≥80 km/h → VERY_HIGH (bateria 008: cobertura/objetos na casa;
    galhos e projeções no veículo)."""

    def __init__(self, threshold_kmh: float = STRONG_WIND_KMH):
        self.threshold_kmh = threshold_kmh

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if snapshot.wind_kmh < self.threshold_kmh:
            return None
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        severity = (
            Severity.VERY_HIGH
            if snapshot.wind_kmh >= VERY_STRONG_WIND_KMH
            else Severity.MEDIUM
        )
        return RiskAlert(
            kind=RiskKind.STRONG_WIND,
            severity=severity,
            reason=f"ventos de {snapshot.wind_kmh:.0f} km/h",
            holder_id=holder.id,
        )


class HeatRule:
    """V2: calor ≥35 °C → HIGH; ≥38 °C vira onda de calor (VERY_HIGH).
    Escopado a RESIDENTIAL/AUTO (exposição material: veículo e
    sobrecarga elétrica da residência — o viés pessoal/saúde fica fora
    do escopo do desafio)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.temperature_c < HEAT_C:
            return None
        if snapshot.temperature_c >= HEAT_WAVE_C:
            return RiskAlert(
                kind=RiskKind.HEAT_WAVE,
                severity=Severity.VERY_HIGH,
                reason=(
                    f"onda de calor: {snapshot.temperature_c:.1f} °C "
                    f"(limiar {HEAT_WAVE_C:.0f} °C)"
                ),
                holder_id=holder.id,
            )
        return RiskAlert(
            kind=RiskKind.HEAT,
            severity=Severity.HIGH,
            reason=f"calor intenso: {snapshot.temperature_c:.1f} °C",
            holder_id=holder.id,
        )


class ExtremeColdRule:
    """V2: frio ≤10 °C → HIGH; ≤5 °C → VERY_HIGH. Escopado a
    RESIDENTIAL/AUTO (tubulações/aquecedores e bateria/partida)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.temperature_c > EXTREME_COLD_C:
            return None
        severity = (
            Severity.VERY_HIGH
            if snapshot.temperature_c <= EXTREME_COLD_VERY_HIGH_C
            else Severity.HIGH
        )
        return RiskAlert(
            kind=RiskKind.EXTREME_COLD,
            severity=severity,
            reason=f"frio intenso: {snapshot.temperature_c:.1f} °C",
            holder_id=holder.id,
        )


class FogRule:
    """V2: neblina — umidade ≥95% com pouco vento (≤15 km/h) e pouca
    chuva (≤10 mm/h). PULA quando a umidade é desconhecida (None).
    Escopado a AUTO (visibilidade/colisões são risco do condutor)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if InsuranceType.AUTO not in holder.insurance_types:
            return None
        humidity = snapshot.humidity_pct
        if humidity is None:
            return None
        if humidity < FOG_HUMIDITY_PCT:
            return None
        if snapshot.wind_kmh > FOG_MAX_WIND_KMH:
            return None
        if snapshot.precipitation_mm_h > FOG_MAX_RAIN_MM_H:
            return None
        severity = (
            Severity.HIGH if humidity >= FOG_HIGH_HUMIDITY_PCT else Severity.MEDIUM
        )
        return RiskAlert(
            kind=RiskKind.FOG,
            severity=severity,
            reason=(
                f"neblina: umidade de {humidity:.0f}% com vento de "
                f"{snapshot.wind_kmh:.0f} km/h"
            ),
            holder_id=holder.id,
        )


class StormRule:
    """V2: tempestade — chuva ≥30 mm/h COM vento ≥60 km/h. Escala:
    chuva ≥35 e vento ≥80 → VERY_HIGH. Escopado a RESIDENTIAL/AUTO
    (cobertura/alagamento e veículos)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.precipitation_mm_h < STORM_RAIN_MM_H:
            return None
        if snapshot.wind_kmh < STORM_WIND_KMH:
            return None
        very_high = (
            snapshot.precipitation_mm_h >= VERY_HEAVY_RAIN_MM_H
            and snapshot.wind_kmh >= VERY_STRONG_WIND_KMH
        )
        severity = Severity.VERY_HIGH if very_high else Severity.HIGH
        return RiskAlert(
            kind=RiskKind.STORM,
            severity=severity,
            reason=(
                f"tempestade: chuva de {snapshot.precipitation_mm_h:.1f} mm/h "
                f"com ventos de {snapshot.wind_kmh:.0f} km/h"
            ),
            holder_id=holder.id,
        )


class RoughSeaRule:
    """V2: ressaca — região costeira com vento ≥80 km/h E chuva
    ≥30 mm/h (VERY_HIGH). Restrita ao litoral, nos DOIS ramos (bateria
    008: maré/invasão de água na casa; veículos na orla e
    estacionamentos baixos)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.is_coastal:
            return None
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.wind_kmh < ROUGH_SEA_WIND_KMH:
            return None
        if snapshot.precipitation_mm_h < ROUGH_SEA_RAIN_MM_H:
            return None
        return RiskAlert(
            kind=RiskKind.ROUGH_SEA,
            severity=Severity.VERY_HIGH,
            reason=(
                f"ressaca: ventos de {snapshot.wind_kmh:.0f} km/h e chuva de "
                f"{snapshot.precipitation_mm_h:.1f} mm/h no litoral"
            ),
            holder_id=holder.id,
        )


class LowHumidityRule:
    """Bateria 008: tempo seco — umidade < 30% (LOW; < 20% → MEDIUM).
    PULA quando a umidade é desconhecida (None). Escopado a
    RESIDENTIAL/AUTO (respiratório/incêndio na casa; poeira e rotas com
    fogo no veículo)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        humidity = snapshot.humidity_pct
        if humidity is None:
            return None
        if humidity >= LOW_HUMIDITY_PCT:
            return None
        severity = (
            Severity.MEDIUM
            if humidity < LOW_HUMIDITY_MEDIUM_PCT
            else Severity.LOW
        )
        return RiskAlert(
            kind=RiskKind.LOW_HUMIDITY,
            severity=severity,
            reason=f"tempo seco: umidade de {humidity:.0f}%",
            holder_id=holder.id,
        )


class FrostRule:
    """Bateria 008: geada — temperatura ≤ 0 °C (HIGH; ≤ −2 °C →
    VERY_HIGH). Escopado a RESIDENTIAL/AUTO (tubulações; gelo no
    asfalto e vidros)."""

    def evaluate(
        self, snapshot: WeatherSnapshot, holder: PolicyHolder
    ) -> RiskAlert | None:
        if not holder.insurance_types & _AUTO_OR_RESIDENTIAL:
            return None
        if snapshot.temperature_c > FROST_C:
            return None
        severity = (
            Severity.VERY_HIGH
            if snapshot.temperature_c <= FROST_VERY_HIGH_C
            else Severity.HIGH
        )
        return RiskAlert(
            kind=RiskKind.FROST,
            severity=severity,
            reason=f"geada: temperatura de {snapshot.temperature_c:.1f} °C",
            holder_id=holder.id,
        )


class RiskEngine:
    """Aplica todas as regras, deduplica por (holder_id, kind) e, com
    ≥2 riscos simultâneos, acrescenta UM resumo MULTIPLE_RISKS por último
    (severidade = máxima entre os individuais)."""

    def __init__(
        self,
        rules: Sequence[RiskRule] = (
            HeavyRainRule(),
            HailRule(),
            StrongWindRule(),
            HeatRule(),
            ExtremeColdRule(),
            FogRule(),
            StormRule(),
            RoughSeaRule(),
            LowHumidityRule(),
            FrostRule(),
        ),
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

        if len(alerts) >= 2:
            top = max(alerts, key=lambda a: _SEVERITY_RANK[a.severity])
            kinds = ", ".join(a.kind.value for a in alerts)
            alerts.append(
                RiskAlert(
                    kind=RiskKind.MULTIPLE_RISKS,
                    severity=top.severity,
                    reason=f"riscos simultâneos detectados: {kinds}",
                    holder_id=holder.id,
                )
            )
        return alerts
