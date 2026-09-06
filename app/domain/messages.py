"""Geração de mensagens — unit message-generation (stories 05 e 06).

Port `MessageGenerator` com a implementação determinística
`TemplateGenerator` (f-strings nativas, sem dependências). A
implementação LLM opcional (story 06) vive em `app.adapters.llm_messages`
e faz fallback silencioso para este template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.holders import PolicyHolder
from app.domain.risk import RiskAlert, RiskKind

# Story 05: mensagem ≤ 480 chars.
MAX_MESSAGE_CHARS: int = 480

EVENT_BY_KIND: dict[RiskKind, str] = {
    RiskKind.HEAVY_RAIN: "chuva intensa prevista para a sua região",
    RiskKind.HAIL: "granizo previsto para a sua região",
    RiskKind.STRONG_WIND: "ventos fortes previstos para a sua região",
    # V2 (intent 005) — todo kind exige entrada (o teste de 480 chars
    # itera RiskKind inteiro).
    RiskKind.HEAT: "calor intenso previsto para a sua região",
    RiskKind.HEAT_WAVE: "onda de calor prevista para a sua região",
    RiskKind.EXTREME_COLD: "frio intenso previsto para a sua região",
    RiskKind.FOG: "neblina prevista para a sua região",
    RiskKind.STORM: "tempestade prevista para a sua região",
    RiskKind.ROUGH_SEA: "condições de ressaca previstas no litoral da sua região",
    RiskKind.MULTIPLE_RISKS: (
        "múltiplos riscos meteorológicos simultâneos na sua região"
    ),
}

# ≥ 2 recomendações preventivas específicas por tipo de evento (story 05).
# Públicos: o adaptador LLM (story 06) reusa as mesmas recomendações no
# prompt para manter consistência entre template e reescrita do LLM.
RECOMMENDATIONS_BY_KIND: dict[RiskKind, tuple[str, ...]] = {
    RiskKind.HEAVY_RAIN: (
        "Verifique a drenagem e as calhas da residência.",
        "Retire veículos de garagens alagáveis e áreas baixas.",
        "Desligue aparelhos eletrônicos em caso de raios.",
    ),
    RiskKind.HAIL: (
        "Proteja o veículo em estacionamento coberto ou garagem.",
        "Evite estacionar sob árvores e estruturas frágeis.",
        "Reforce janelas e coberturas de vidro.",
    ),
    RiskKind.STRONG_WIND: (
        "Reforce telhados, toldos e estruturas leves.",
        "Guarde objetos soltos da área externa (vasos, mobiliário).",
        "Evite o litoral e árvores durante as rajadas.",
    ),
    # V2 (intent 005).
    RiskKind.HEAT: (
        "Hidrate-se e evite exposição ao sol entre 10h e 16h.",
        "Confira a climatização do veículo e a carga elétrica da residência.",
    ),
    RiskKind.HEAT_WAVE: (
        "Evite atividades ao ar livre nas horas mais quentes.",
        "Redobre a hidratação e proteja crianças e idosos.",
        "Confira a ventilação de ambientes fechados.",
    ),
    RiskKind.EXTREME_COLD: (
        "Abrigue-se com roupas adequadas e proteja crianças e idosos.",
        "Ventile ambientes com aquecedores para evitar acidentes.",
    ),
    RiskKind.FOG: (
        "Reduza a velocidade e aumente a distância do veículo à frente.",
        "Use faróis baixos e lanternas; evite ultrapassagens.",
    ),
    RiskKind.STORM: (
        "Evite deslocamentos desnecessários durante a tempestade.",
        "Afaste-se de janelas, árvores e estruturas metálicas.",
        "Desligue aparelhos eletrônicos em caso de raios.",
    ),
    RiskKind.ROUGH_SEA: (
        "Evite o litoral e atividades náuticas durante a ressaca.",
        "Retire veículos de áreas sujeitas a marés e ondas.",
    ),
    RiskKind.MULTIPLE_RISKS: (
        "Acompanhe os alertas oficiais e evite deslocamentos desnecessários.",
        "Proteja veículos em local coberto e reforce estruturas externas.",
        "Mantenha contatos de emergência acessíveis.",
    ),
}


@dataclass(frozen=True)
class GeneratedMessage:
    """Mensagem personalizada pronta para envio."""

    holder_id: str
    alert_kind: RiskKind
    text: str


class MessageGenerator(Protocol):
    """Port: (segurado, alerta) → mensagem personalizada."""

    def generate(
        self, holder: PolicyHolder, alert: RiskAlert
    ) -> GeneratedMessage: ...


class TemplateGenerator:
    """Implementação determinística da port — SEMPRE disponível."""

    def generate(
        self, holder: PolicyHolder, alert: RiskAlert
    ) -> GeneratedMessage:
        event = EVENT_BY_KIND[alert.kind]
        recommendations = RECOMMENDATIONS_BY_KIND[alert.kind]
        parts = [f"Olá, {holder.name}! {event}."]
        parts.extend(f"• {rec}" for rec in recommendations)
        text = " ".join(parts)
        if len(text) > MAX_MESSAGE_CHARS:  # salvaguarda da story 05
            text = text[: MAX_MESSAGE_CHARS - 1].rstrip() + "…"
        return GeneratedMessage(
            holder_id=holder.id, alert_kind=alert.kind, text=text
        )
