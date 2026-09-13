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
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.domain.holders import PolicyHolder
from app.domain.messages import (
    EVENT_BY_KIND,
    EVENT_NAME_BY_KIND,
    MAX_MESSAGE_CHARS,
    GeneratedMessage,
    MessageGenerator,
    TemplateGenerator,
)
from app.domain.risk import RiskAlert, RiskKind, Severity
from app.domain.risk_battery import (
    BRANCH_LABELS,
    EMERGENCY_PHONES,
    RISK_BATTERY,
    cells_for,
    level_for,
    phases_for,
)

# Mesmo binding do executor do ai-dlc (OpenRouter; key em OPENROUTER_API_KEY).
DEFAULT_MODEL: str = "openrouter:z-ai/glm-5.3-flash"

# Base da API (duplicada aqui para passar o AsyncOpenAI já configurado).
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# A rodada emite N mensagens em sequência; provedores limitam taxa por
# minuto → retry curto com backoff evita fallback por 429 transitório.
RETRY_ATTEMPTS: int = 2  # 1 tentativa + 1 retry (pior caso ~3 min/mensagem)
RETRY_DELAY_S: float = 1.0

# Teto por tentativa (2026-09-13, decisão do dono: "garantir que a LLM
# sempre faça as mensagens"). O fallback só assume com FALHA REAL do
# provedor (sem chave, 429/5xx, resposta vazia) — lentidão NÃO cai mais
# no template: o teto de parede cobre fila + geração (medição: ~31 s por
# chamada com o provedor lento; 90 s dá folga).
LLM_TIMEOUT_S: float = 90.0

_TONE_RULES = (
    "Você é um assistente de comunicação proativa de uma seguradora."
    " Reescreva o aviso para o segurado em português brasileiro, no tom"
    " claro, empático e acionável, pronto para SMS/push. Inclua o nome do"
    " segurado, o evento previsto e TODAS as recomendações preventivas"
    f" informadas. Limite rígido: {MAX_MESSAGE_CHARS} caracteres."
    " Responda APENAS o texto final, sem títulos, aspas ou emojis."
)


# Regras transversais da bateria de negócio (tabela-alertas-preventiva.md):
# 1 ramos contratados; 2 severidade INMET; 3 telefones só em laranja+;
# 4 fases Antes/Durante; 5 NUNCA pós-sinistro; 6 perfis vulneráveis.
_TRANSVERSAL_RULES = (
    "Regras transversais da bateria (OBRIGATÓRIAS):\n"
    "1. Use APENAS as células dos ramos contratados informadas; não"
    " invente precauções de outro ramo.\n"
    "2. Tom e urgência seguem o nível INMET: amarelo=monitorar,"
    " laranja=prevenir, vermelho=agir hoje, preto=agir imediatamente.\n"
    "3. Telefones de emergência (Defesa Civil 199, Bombeiros 193, SAMU"
    " 192) SOMENTE em nível laranja ou superior, quando indicados.\n"
    "4. Fase: amarelo usa só as diretrizes [Antes]; laranja ou superior"
    " usa [Antes] e [Durante].\n"
    "5. NUNCA inclua instruções pós-sinistro (documentação de danos,"
    " vistoria, acionamento do seguro), mesmo que o evento esteja em"
    " andamento — o alerta é preventivo.\n"
    "6. Perfis vulneráveis: se houver dados de idosos, crianças ou"
    " animais, reforce hidratação no calor e aquecimento seguro no frio."
)


def _join(items: tuple[str, ...]) -> str:
    return "; ".join(items)


_SEV_RANK: dict[Severity, int] = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.VERY_HIGH: 3,
}


def _phones_line(has_phones: bool) -> str:
    if has_phones:
        return (
            "Telefones de emergência para incluir no texto:"
            f" {EMERGENCY_PHONES}"
        )
    return "Não inclua telefones de emergência (nível abaixo de laranja)."


def _battery_lines(
    kind: RiskKind,
    insurance_types: frozenset,
    severity: Severity,
) -> str:
    """Células do risco para os ramos CONTRATADOS (regra 1), com
    impacto material e recomendações por fase (regra 4). Se o risco não
    tem célula para nenhum ramo do segurado (defensivo), usa todas."""
    cells = cells_for(kind, insurance_types) or RISK_BATTERY.get(kind, {})
    fases = phases_for(severity)
    linhas: list[str] = []
    for branch, cell in cells.items():
        label = BRANCH_LABELS[branch]
        linhas.append(f"- [{label}] impacto possível: {_join(cell.impacts)}")
        if "before" in fases:
            linhas.extend(f"- [{label}][Antes] {rec}" for rec in cell.before)
        if "during" in fases:
            linhas.extend(f"- [{label}][Durante] {rec}" for rec in cell.during)
    return "\n".join(linhas)


def build_prompt(holder: PolicyHolder, alert: RiskAlert) -> str:
    """Monta o prompt com o contexto do segurado + CÉLULAS DA BATERIA
    (intent 008): impactos e recomendações por fase dos ramos
    contratados, nível INMET e as regras transversais do negócio."""
    event = EVENT_BY_KIND[alert.kind]
    level = level_for(alert.severity)
    insurance = (
        ", ".join(sorted(t.value for t in holder.insurance_types)) or "n/d"
    )
    return (
        f"{_TONE_RULES}\n\n{_TRANSVERSAL_RULES}\n"
        f"Segurado: {holder.name} (seguros: {insurance})\n"
        f"Evento: {event}; severidade: {alert.severity.value} →"
        f" nível {level.label} ({level.action}, {level.window})"
        f" ({alert.reason})\n"
        "Células da bateria (Risco × Ramo contratado, fases"
        " Antes/Durante):\n"
        f"{_battery_lines(alert.kind, holder.insurance_types, alert.severity)}"
        f"\n{_phones_line(level.phones)}"
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
    """Prompt da mensagem consolidada (intent 007 + bateria 008): TODOS
    os eventos simultâneos, cada um com as células da bateria dos ramos
    contratados; nível INMET global (evento mais severo)."""
    individuals = [
        a for a in alerts if a.kind is not RiskKind.MULTIPLE_RISKS
    ]
    level = level_for(
        max(individuals, key=lambda a: _SEV_RANK[a.severity]).severity
    )
    blocos: list[str] = []
    for indice, alert in enumerate(individuals, start=1):
        nome = EVENT_NAME_BY_KIND[alert.kind]
        level_evento = level_for(alert.severity)
        blocos.append(
            f"Evento {indice}: {nome} — severidade: {alert.severity.value}"
            f" → nível {level_evento.label} ({level_evento.action})"
            f" ({alert.reason})\n"
            f"{_battery_lines(alert.kind, holder.insurance_types, alert.severity)}"
        )
    insurance = (
        ", ".join(sorted(t.value for t in holder.insurance_types)) or "n/d"
    )
    return (
        f"{_TONE_RULES_MULTI}\n\n{_TRANSVERSAL_RULES}\n"
        f"Segurado: {holder.name} (seguros: {insurance})\n"
        f"Eventos simultâneos ({len(individuals)}) — nível global"
        f" {level.label} ({level.action}):\n"
        + "\n\n".join(blocos)
        + f"\n{_phones_line(level.phones)}"
    )


@dataclass
class LlmGenerator:
    """Implementação opcional da port reescrevendo via LLM (Pydantic AI).

    `agent` injectável para testes (protocol mínimo: `run_sync(prompt)`
    → objeto com `.output`). Sem agente injetado, cria um agente real
    POR TENTATIVA (import lazy do pydantic-ai) — cada tentativa roda em
    event loop próprio (`asyncio.run`): o `httpx.AsyncClient` não pode
    ser compartilhado entre event loops. Cada tentativa tem TETO DE
    PAREDE (`LLM_TIMEOUT_S` via `asyncio.wait_for`) — o read timeout do
    httpx não protege contra streaming lento (chunks chegando com gaps
    menores que o teto esticaram UMA mensagem a 125,7 s em 2026-09-13).
    Se a criação ou a chamada falharem, cai no fallback silencioso.
    """

    model: str = DEFAULT_MODEL
    fallback: MessageGenerator | None = None
    agent: Any | None = None
    retry_attempts: int = field(default_factory=lambda: RETRY_ATTEMPTS)
    retry_delay_s: float = field(default_factory=lambda: RETRY_DELAY_S)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.fallback is None:
            self.fallback = TemplateGenerator()
        self.llm_calls: int = 0
        self.fallbacks: int = 0

    def _create_agent(self) -> Any:
        # Import lazy: modo template não exige o SDK instalado. Para
        # openrouter:, o timeout vai NO CONSTRUTOR do AsyncOpenAI: o SDK
        # da openai aplica o PRÓPRIO timeout (default 600 s) por
        # requisição e sobrescreve o de qualquer http_client. Teto de
        # parede (asyncio.wait_for) por tentativa garante o corte mesmo
        # com streaming lento. max_retries=0 no SDK: o retry externo
        # (RETRY_ATTEMPTS) é o único mecanismo de retry. A chave vem do
        # env; ausente → ValueError → fallback silencioso.
        from pydantic_ai import Agent  # noqa: PLC0415 (lazy)

        if self.model.startswith("openrouter:"):
            from openai import AsyncOpenAI  # noqa: PLC0415 (lazy)
            from pydantic_ai.models.openai import OpenAIModel  # noqa: PLC0415
            from pydantic_ai.providers.openrouter import (  # noqa: PLC0415
                OpenRouterProvider,
            )

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY ausente")
            provider = OpenRouterProvider(
                openai_client=AsyncOpenAI(
                    base_url=OPENROUTER_BASE_URL,
                    api_key=api_key,
                    timeout=LLM_TIMEOUT_S,
                    max_retries=0,
                )
            )
            model = OpenAIModel(
                self.model.removeprefix("openrouter:"), provider=provider
            )
            return Agent(model, instructions=_TONE_RULES, output_type=str)
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
        """Agente POR TENTATIVA (event loop próprio por tentativa) com
        teto de parede + retries + truncamento."""
        text = self._llm_text(prompt)
        if len(text) > MAX_MESSAGE_CHARS:
            text = text[: MAX_MESSAGE_CHARS - 1].rstrip() + "…"
        with self.lock:
            self.llm_calls += 1
        return GeneratedMessage(
            holder_id=holder.id, alert_kind=alert_kind, text=text
        )

    def _fallback_text(
        self, delegate: Any
    ) -> GeneratedMessage:
        """Fallback silencioso: contabiliza e delega ao TemplateGenerator."""
        with self.lock:
            self.fallbacks += 1
        fallback = self.fallback
        assert fallback is not None  # garantido em __post_init__
        return delegate(fallback)

    def _agent_da_tentativa(self) -> Any:
        """Agente da tentativa: o injetado (testes) ou um real novo
        (event loop próprio — não compartilhar httpx entre loops)."""
        if self.agent is not None:
            return self.agent
        return self._create_agent()

    def _llm_text(self, prompt: str) -> str:
        """Chamada com teto de parede + retries para falhas transitórias
        (429/5xx/timeout). Resposta vazia também força retry. Esgotadas
        as tentativas, propaga para o fallback silencioso do `generate`."""
        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts):
            try:
                text = str(
                    self._run_com_teto(self._agent_da_tentativa(), prompt)
                ).strip()
                if text:
                    return text
            except Exception as exc:  # noqa: BLE001 (transiente)
                last_exc = exc
            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay_s * (attempt + 1))
        raise RuntimeError("LLM indisponível após retries") from last_exc

    def _run_com_teto(self, agent: Any, prompt: str) -> Any:
        """Uma tentativa com TETO DE PAREDE (`LLM_TIMEOUT_S`):
        `asyncio.wait_for` cancela a requisição de verdade — o read
        timeout do httpx não protege contra streaming lento (chunks
        chegando com gaps menores que o teto). Agentes de teste (sync,
        `run_sync`) rodam em thread; agentes reais (async, `run`) rodam
        no loop da tentativa."""
        import asyncio

        async def _executar() -> Any:
            run = getattr(agent, "run", None)
            if run is not None and asyncio.iscoroutinefunction(run):
                return (await run(prompt)).output
            return (await asyncio.to_thread(agent.run_sync, prompt)).output

        return asyncio.run(asyncio.wait_for(_executar(), timeout=LLM_TIMEOUT_S))

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
