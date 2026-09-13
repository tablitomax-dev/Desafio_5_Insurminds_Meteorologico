"""Geração de mensagens — unit message-generation (stories 05/06 + 008).

Port `MessageGenerator` com a implementação determinística
`TemplateGenerator` (f-strings nativas, sem dependências). A
implementação LLM opcional (story 06) vive em `app.adapters.llm_messages`
e faz fallback silencioso para este template.

Intent 008: o conteúdo preventivo vem da BATERIA
(`app.domain.risk_battery`), derivada da tabela de negócio
`memory-bank/standards/tabela-alertas-preventiva.md`: células por
(risco, ramo) com fases Antes/Durante, nível INMET por severidade e
telefones de emergência em laranja+ (regras transversais 1–4). Nada de
conteúdo pós-sinistro (regra 5).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.risk import RiskAlert, RiskKind, Severity
from app.domain.risk_battery import (
    BRANCH_LABELS,
    EMERGENCY_PHONES,
    RISK_BATTERY,
    BatteryCell,
    cells_for,
    level_for,
    phases_for,
)

# Story 05: mensagem ≤ 480 chars — elevado para 600 a pedido do dono
# (2026-09-08; Telegram aceita 4096).
MAX_MESSAGE_CHARS: int = 600

EVENT_BY_KIND: dict[RiskKind, str] = {
    RiskKind.HEAVY_RAIN: "chuva intensa prevista para a sua região",
    RiskKind.HAIL: "granizo previsto para a sua região",
    RiskKind.STRONG_WIND: "ventos fortes previstos para a sua região",
    # V2 (intent 005) — todo kind exige entrada (o teste de limite de
    # chars itera RiskKind inteiro).
    RiskKind.HEAT: "calor intenso previsto para a sua região",
    RiskKind.HEAT_WAVE: "onda de calor prevista para a sua região",
    RiskKind.EXTREME_COLD: "frio intenso previsto para a sua região",
    RiskKind.FOG: "neblina prevista para a sua região",
    RiskKind.STORM: "tempestade prevista para a sua região",
    RiskKind.ROUGH_SEA: "condições de ressaca previstas no litoral da sua região",
    # Bateria preventiva (intent 008).
    RiskKind.LOW_HUMIDITY: "tempo seco com baixa umidade na sua região",
    RiskKind.FROST: "geada prevista para a sua região",
    RiskKind.MULTIPLE_RISKS: (
        "múltiplos riscos meteorológicos simultâneos na sua região"
    ),
}

# Nomes curtos da mensagem consolidada (intent 007 / evento por bloco).
EVENT_NAME_BY_KIND: dict[RiskKind, str] = {
    RiskKind.HEAVY_RAIN: "chuva intensa",
    RiskKind.HAIL: "granizo",
    RiskKind.STRONG_WIND: "vento forte",
    RiskKind.HEAT: "calor intenso",
    RiskKind.HEAT_WAVE: "onda de calor",
    RiskKind.EXTREME_COLD: "frio intenso",
    RiskKind.FOG: "neblina",
    RiskKind.STORM: "tempestade",
    RiskKind.ROUGH_SEA: "ressaca",
    RiskKind.LOW_HUMIDITY: "tempo seco",
    RiskKind.FROST: "geada",
}

SEVERITY_LABEL_BY_SEVERITY: dict[Severity, str] = {
    Severity.LOW: "leve",
    Severity.MEDIUM: "moderada",
    Severity.HIGH: "alta",
    Severity.VERY_HIGH: "muito alta",
}

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.VERY_HIGH: 3,
}


@dataclass(frozen=True)
class GeneratedMessage:
    """Mensagem personalizada pronta para envio."""

    holder_id: str
    alert_kind: RiskKind
    text: str


class MessageGenerator(Protocol):
    """Port: (segurado, alerta) → mensagem personalizada; com ≥2 alertas
    simultâneos, `generate_consolidated` produz UMA mensagem com todos
    os eventos e precauções (intent 007)."""

    def generate(
        self, holder: PolicyHolder, alert: RiskAlert
    ) -> GeneratedMessage: ...

    def generate_consolidated(
        self, holder: PolicyHolder, alerts: Sequence[RiskAlert]
    ) -> GeneratedMessage: ...


def _cells_fallback(
    kind: RiskKind, insurance_types: frozenset[InsuranceType]
) -> dict[InsuranceType, BatteryCell]:
    """Células dos ramos CONTRATADOS (regra 1). Se o risco não tem
    célula para nenhum ramo do segurado (defensivo — o engine nunca
    emitiria), usa TODAS as células do risco para não degradar a
    mensagem."""
    return cells_for(kind, insurance_types) or RISK_BATTERY.get(kind, {})


def _cell_recs(cell: BatteryCell, severity: Severity) -> tuple[str, ...]:
    """Recomendações da célula nas fases da severidade (regra 4):
    ANTES sempre; ANTES + DURANTE quando o nível não é amarelo."""
    recs = list(cell.before)
    if "during" in phases_for(severity):
        recs.extend(cell.during)
    return tuple(recs)


# Degraus de encaixe (intent 008): preferência para telefones de
# emergência (regra 3) — as quantidades de recomendação e os rótulos
# de severidade somem ANTES deles.
_FIT_MODES: tuple[tuple[bool, int, bool], ...] = (
    # (com telefones, recs por ramo, rótulos de severidade por evento)
    (True, 3, True),
    (True, 2, True),
    (True, 1, True),
    (True, 1, False),
    (False, 2, True),
    (False, 1, True),
)


def _fit(render) -> str:
    """Encaixa o texto render(with_phones, per_branch, show_sev) no
    limite da story 05; último recurso é a salvaguarda de truncamento."""
    for with_phones, per_branch, show_sev in _FIT_MODES:
        text = render(with_phones, per_branch, show_sev)
        if len(text) <= MAX_MESSAGE_CHARS:
            return text
    return render(True, 1, False)[: MAX_MESSAGE_CHARS - 1].rstrip() + "…"


class TemplateGenerator:
    """Implementação determinística da port — SEMPRE disponível.

    Conteúdo pela bateria preventiva (intent 008): células dos ramos
    contratados (regra 1), fases pela severidade (regra 4), nível INMET
    na abertura e telefones de emergência em laranja+ (regra 3). A LLM
    recebe as MESMAS células com os impactos no prompt (consistência da
    story 06). Nada de pós-sinistro (regra 5 — nem existe na bateria).
    """

    def generate(
        self, holder: PolicyHolder, alert: RiskAlert
    ) -> GeneratedMessage:
        event = EVENT_BY_KIND[alert.kind]
        severity = alert.severity
        level = level_for(severity)
        cells = _cells_fallback(alert.kind, holder.insurance_types)

        def render(with_phones: bool, per_branch: int, show_sev: bool) -> str:
            # (individual: `show_sev` não se aplica — o nível INMET sai
            # na abertura; assinatura alinhada ao _fit.)
            blocos: list[str] = []
            for branch, cell in cells.items():
                recs = _cell_recs(cell, severity)[:per_branch] or (
                    _cell_recs(cell, severity)[:1]
                )
                lista = " ".join(f"{rec}." for rec in recs)
                blocos.append(f"{BRANCH_LABELS[branch]}: {lista}")
            if with_phones and level.phones:
                blocos.append(EMERGENCY_PHONES)
            abertura = (
                f"Olá, {holder.name}! {event} — nível {level.label}"
                f" ({level.action}, {level.window})."
            )
            return f"{abertura} " + " ".join(blocos)

        text = _fit(render)  # telefones primeiro; recs cedem depois
        return GeneratedMessage(
            holder_id=holder.id, alert_kind=alert.kind, text=text
        )

    def generate_consolidated(
        self, holder: PolicyHolder, alerts: Sequence[RiskAlert]
    ) -> GeneratedMessage:
        """UMA mensagem para ≥2 riscos simultâneos (intent 007): lista
        cada evento — do mais severo ao menos — com as células da
        bateria dos ramos contratados (regra 1), fases pela severidade
        (regra 4), nível INMET do evento mais severo na abertura e
        telefones em laranja+ (regra 3). Dedup entre eventos; o
        alerta-resumo MULTIPLE_RISKS não entra na lista (define apenas
        o `alert_kind`)."""
        individuals = [
            a for a in alerts if a.kind is not RiskKind.MULTIPLE_RISKS
        ]
        ordered = sorted(
            individuals,
            key=lambda a: _SEVERITY_ORDER[a.severity],
            reverse=True,
        )
        level = level_for(ordered[0].severity)

        def render(with_phones: bool, per_branch: int, show_sev: bool) -> str:
            usadas: set[str] = set()
            eventos: list[str] = []
            for alert in ordered:
                nome = EVENT_NAME_BY_KIND[alert.kind]
                if show_sev:
                    sev = f" ({SEVERITY_LABEL_BY_SEVERITY[alert.severity]})"
                else:
                    sev = ""
                blocos: list[str] = []
                for branch, cell in _cells_fallback(
                    alert.kind, holder.insurance_types
                ).items():
                    recs = [
                        r
                        for r in _cell_recs(cell, alert.severity)
                        if r not in usadas
                    ][:per_branch] or [_cell_recs(cell, alert.severity)[0]]
                    usadas.update(recs)
                    lista = " ".join(f"{rec}." for rec in recs)
                    blocos.append(f"{BRANCH_LABELS[branch]}: {lista}")
                eventos.append(f"{nome.capitalize()}{sev}: " + " ".join(blocos))
            trechos = eventos
            if with_phones and level.phones:
                # Telefones logo APÓS o nível (regra 3): emergência em
                # cima, antes do detalhamento dos eventos.
                trechos.insert(0, EMERGENCY_PHONES)
            abertura = (
                f"Olá, {holder.name}! {len(ordered)} alertas na sua"
                f" região — nível {level.label}"
                f" ({level.action}). "
            )
            return abertura + " ".join(trechos)

        text = _fit(render)  # telefones primeiro; recs cedem depois
        return GeneratedMessage(
            holder_id=holder.id, alert_kind=RiskKind.MULTIPLE_RISKS, text=text
        )
