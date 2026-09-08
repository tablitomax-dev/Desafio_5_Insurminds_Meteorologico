"""Adaptador LLM da port MessageGenerator — story 06 (unit message-generation).

`LlmGenerator` reescreve a mensagem com um LLM via Pydantic AI
(model-agnostic). O import do SDK é LAZY: o modo template (default da
demo) nunca exige `pydantic-ai` instalado. Falhas transitórias (429/5xx/
timeout) recebem retry curto com backoff; qualquer falha definitiva —
env ausente, SDK ausente, erro de API, resposta vazia — cai em fallback
silencioso para o `TemplateGenerator` (a demo nunca quebra), e o modo é
reportado no relatório da rodada (`mode_label` + `describe_mode`).

Binding default do repositório (decisão do dono): o mesmo executor do
ai-dlc — `openrouter:z-ai/glm-5.3-flash`, usando `OPENROUTER_API_KEY`.

Contrato de env (resolvido no composition root, `build_generator`):
- `LLM_MODEL` setado (identificador pydantic-ai, ex.:
  `openrouter:z-ai/glm-5.3-flash`) → modo LLM;
- `LLM_PROVIDER=llm` → modo LLM com `DEFAULT_MODEL`;
- `LLM_PROVIDER=template` → força template mesmo com `LLM_MODEL` setado;
- nenhuma das acima → `TemplateGenerator` (default).
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.domain.holders import PolicyHolder
from app.domain.messages import (
    EVENT_BY_KIND,
    EVENT_NAME_BY_KIND,
    MAX_MESSAGE_CHARS,
    RECOMMENDATIONS_BY_KIND,
    GeneratedMessage,
    MessageGenerator,
    TemplateGenerator,
)
from app.domain.risk import RiskAlert, RiskKind

# Mesmo binding do executor do ai-dlc (OpenRouter; key em OPENROUTER_API_KEY).
DEFAULT_MODEL: str = "openrouter:z-ai/glm-5.3-flash"

# A rodada emite N mensagens em sequência; provedores limitam taxa por
# minuto → retry curto com backoff evita fallback por 429 transitório.
RETRY_ATTEMPTS: int = 3  # 1 tentativa + 2 retries
RETRY_DELAY_S: float = 1.0

_TONE_RULES = (
    "Você é um assistente de comunicação proativa de uma seguradora."
    " Reescreva o aviso para o segurado em português brasileiro, no tom"
    " claro, empático e acionável, pronto para SMS/push. Inclua o nome do"
    " segurado, o evento previsto e TODAS as recomendações preventivas"
    f" informadas. Limite rígido: {MAX_MESSAGE_CHARS} caracteres."
    " Responda APENAS o texto final, sem títulos, aspas ou emojis."
)


def build_prompt(holder: PolicyHolder, alert: RiskAlert) -> str:
    """Monta o prompt com contexto do segurado + evento + recomendações."""
    event = EVENT_BY_KIND[alert.kind]
    recommendations = "\n".join(
        f"- {rec}" for rec in RECOMMENDATIONS_BY_KIND[alert.kind]
    )
    insurance = (
        ", ".join(sorted(t.value for t in holder.insurance_types)) or "n/d"
    )
    return (
        f"{_TONE_RULES}\n\n"
        f"Segurado: {holder.name} (seguros: {insurance})\n"
        f"Evento: {event}; severidade: {alert.severity.value}"
        f" ({alert.reason})\n"
        f"Recomendações preventivas:\n{recommendations}"
    )


_TONE_RULES_MULTI = (
    "Você é um assistente de comunicação proativa de uma seguradora."
    " Reescreva o aviso para o segurado em português brasileiro, no tom"
    " claro, empático e acionável, pronto para SMS/push. Inclua o nome do"
    " segurado, TODOS os eventos previstos listados e as recomendações de"
    " cada um, em um único aviso consolidado. Limite rígido:"
    f" {MAX_MESSAGE_CHARS} caracteres."
    " Responda APENAS o texto final, sem títulos, aspas ou emojis."
)


def build_prompt_consolidated(
    holder: PolicyHolder, alerts: Sequence[RiskAlert]
) -> str:
    """Prompt da mensagem consolidada (intent 007): TODOS os eventos
    simultâneos do segurado + recomendações específicas (dedup)."""
    individuals = [
        a for a in alerts if a.kind is not RiskKind.MULTIPLE_RISKS
    ]
    eventos: list[str] = []
    usadas: set[str] = set()
    recomendacoes: list[str] = []
    for alert in individuals:
        nome = EVENT_NAME_BY_KIND[alert.kind]
        eventos.append(
            f"- {nome}; severidade: {alert.severity.value} ({alert.reason})"
        )
        for rec in RECOMMENDATIONS_BY_KIND[alert.kind]:
            if rec not in usadas:
                usadas.add(rec)
                recomendacoes.append(f"- {rec} [{nome}]")
    insurance = (
        ", ".join(sorted(t.value for t in holder.insurance_types)) or "n/d"
    )
    return (
        f"{_TONE_RULES_MULTI}\n\n"
        f"Segurado: {holder.name} (seguros: {insurance})\n"
        f"Eventos simultâneos ({len(individuals)}):\n"
        + "\n".join(eventos)
        + "\nRecomendações preventivas por evento:\n"
        + "\n".join(recomendacoes)
    )


@dataclass
class LlmGenerator:
    """Implementação opcional da port reescrevendo via LLM (Pydantic AI).

    `agent` injectável para testes (protocol mínimo: `run_sync(prompt)`
    → objeto com `.output`). Sem agente injetado, cria o real de forma
    LAZY na primeira geração (import do pydantic-ai); se a criação ou a
    chamada falharem, cai no fallback silencioso.
    """

    model: str = DEFAULT_MODEL
    fallback: MessageGenerator | None = None
    agent: Any | None = None
    retry_attempts: int = field(default_factory=lambda: RETRY_ATTEMPTS)
    retry_delay_s: float = field(default_factory=lambda: RETRY_DELAY_S)

    def __post_init__(self) -> None:
        if self.fallback is None:
            self.fallback = TemplateGenerator()
        self.llm_calls: int = 0
        self.fallbacks: int = 0

    def _create_agent(self) -> Any:
        # Import lazy: modo template não exige o SDK instalado.
        from pydantic_ai import Agent  # noqa: PLC0415 (lazy)

        return Agent(self.model, instructions=_TONE_RULES, output_type=str)

    def generate(
        self, holder: PolicyHolder, alert: RiskAlert
    ) -> GeneratedMessage:
        try:
            return self._rewrite(
                build_prompt(holder, alert), holder, alert.kind
            )
        except Exception:  # noqa: BLE001 (fronteira com serviço externo)
            return self._fallback_text(
                lambda fallback: fallback.generate(holder, alert)
            )

    def generate_consolidated(
        self, holder: PolicyHolder, alerts: Sequence[RiskAlert]
    ) -> GeneratedMessage:
        """Reescrita LLM da mensagem consolidada (intent 007): todos os
        eventos + recomendações em UM aviso; fallback silencioso para o
        template consolidado (demo nunca quebra)."""
        try:
            return self._rewrite(
                build_prompt_consolidated(holder, alerts),
                holder,
                RiskKind.MULTIPLE_RISKS,
            )
        except Exception:  # noqa: BLE001 (fronteira com serviço externo)
            return self._fallback_text(
                lambda fallback: fallback.generate_consolidated(holder, alerts)
            )

    def _rewrite(
        self,
        prompt: str,
        holder: PolicyHolder,
        alert_kind: RiskKind,
    ) -> GeneratedMessage:
        """Criação lazy do agente + chamada com retries + truncamento."""
        if self.agent is None:
            self.agent = self._create_agent()
        text = self._llm_text(prompt)
        if len(text) > MAX_MESSAGE_CHARS:
            text = text[: MAX_MESSAGE_CHARS - 1].rstrip() + "…"
        self.llm_calls += 1
        return GeneratedMessage(
            holder_id=holder.id, alert_kind=alert_kind, text=text
        )

    def _fallback_text(
        self, delegate: Any
    ) -> GeneratedMessage:
        """Fallback silencioso: contabiliza e delega ao TemplateGenerator."""
        self.fallbacks += 1
        fallback = self.fallback
        assert fallback is not None  # garantido em __post_init__
        return delegate(fallback)

    def _llm_text(self, prompt: str) -> str:
        """Chamada com retries para falhas transitórias (429/5xx/timeout).

        Resposta vazia também força retry. Esgotadas as tentativas,
        propaga para o fallback silencioso do `generate`.
        """
        last_exc: Exception | None = None
        agent = self.agent
        assert agent is not None  # garantido pelo generate (criação lazy)
        for attempt in range(self.retry_attempts):
            try:
                result = agent.run_sync(prompt)
                text = str(result.output).strip()
                if text:
                    return text
            except Exception as exc:  # noqa: BLE001 (transiente)
                last_exc = exc
            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay_s * (attempt + 1))
        raise RuntimeError("LLM indisponível após retries") from last_exc

    def mode_label(self) -> str:
        """Modo exercitado na rodada, para o relatório (story 06)."""
        if self.fallbacks == 0:
            return "llm"
        if self.llm_calls == 0:
            return "template (fallback: LLM indisponível)"
        return "híbrido (LLM + template no fallback)"


def build_generator(
    *, model: str | None = None, provider: str | None = None
) -> MessageGenerator:
    """Composition-root helper: opções explícitas OU env decidem (story 06).

    `model`/`provider` passados (UI da intent 003) vencem; `None` cai no
    env (`LLM_MODEL`/`LLM_PROVIDER`).
    """
    model_id = model if model is not None else os.getenv("LLM_MODEL", "")
    provider_id = (
        provider if provider is not None else os.getenv("LLM_PROVIDER", "")
    ).strip().lower()
    provider_wants_llm = provider_id == "llm"
    provider_forces_template = provider_id == "template"

    if provider_wants_llm or (model_id.strip() and not provider_forces_template):
        return LlmGenerator(model=model_id.strip() or DEFAULT_MODEL)
    return TemplateGenerator()


def describe_mode(generator: MessageGenerator) -> str:
    """Rótulo do gerador para o relatório (template por default)."""
    label = getattr(generator, "mode_label", None)
    if callable(label):
        return str(label())
    return "template"
