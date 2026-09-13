"""Testes do adaptador LLM — story 06 (LLM opcional com fallback)."""

import pytest

from app.adapters.llm_messages import (
    DEFAULT_MODEL,
    LLM_TIMEOUT_S,
    LlmGenerator,
    build_generator,
    describe_mode,
)
from app.domain.holders import GeoLocation, InsuranceType, PolicyHolder
from app.domain.messages import MAX_MESSAGE_CHARS, TemplateGenerator
from app.domain.risk import RiskAlert, RiskKind, Severity


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output


class _FakeAgent:
    """Agente fake: captura prompts, devolve saída fixa ou levanta erro.

    `fail_first > 0` levanta `error` apenas nas N primeiras chamadas
    (útil para simular recuperação após falha — caso híbrido).
    """

    def __init__(
        self,
        outputs: list[str] | str = "",
        error: Exception | None = None,
        fail_first: int = 0,
    ) -> None:
        self._outputs = (
            [outputs] if isinstance(outputs, str) else list(outputs)
        )
        self._error = error
        self._fail_first = fail_first
        self._calls = 0
        self.prompts: list[str] = []

    def run_sync(self, prompt: str, **kwargs: object):  # noqa: ANN201
        self.prompts.append(prompt)
        self._calls += 1
        if self._error is None:
            return _FakeResult(
                self._outputs.pop(0) if self._outputs else ""
            )
        if self._calls <= self._fail_first:
            raise self._error
        if self._fail_first == 0:
            raise self._error
        return _FakeResult(self._outputs.pop(0) if self._outputs else "")


def _holder() -> PolicyHolder:
    return PolicyHolder(
        id="H001",
        name="Maria Silva",
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.AUTO}),
        is_coastal=False,
    )


def _hail_alert() -> RiskAlert:
    return RiskAlert(
        kind=RiskKind.HAIL,
        severity=Severity.HIGH,
        reason="granizo previsto (weathercode 96)",
        holder_id="H001",
    )


def _heat_wave_alert() -> RiskAlert:
    return RiskAlert(
        kind=RiskKind.HEAT_WAVE,
        severity=Severity.VERY_HIGH,
        reason="temperatura de 50.0 °C (limiar de onda de calor: 38 °C)",
        holder_id="H001",
    )


def test_default_model_e_glm_53_flash_via_openrouter() -> None:
    """Binding definido pelo dono do repo: mesmo modelo do ai-dlc."""
    assert DEFAULT_MODEL == "openrouter:z-ai/glm-5.3-flash"


def test_llm_output_usado_quando_agente_ok() -> None:
    """Given env LLM ok, when gera, then texto vem do LLM com metadados."""
    agent = _FakeAgent("Olá, Maria! Há risco de granizo. Proteja o carro.")
    gen = LlmGenerator(agent=agent)

    msg = gen.generate(_holder(), _hail_alert())

    assert msg.text == "Olá, Maria! Há risco de granizo. Proteja o carro."
    assert msg.holder_id == "H001"
    assert msg.alert_kind is RiskKind.HAIL
    assert gen.llm_calls == 1
    assert gen.fallbacks == 0


def test_fallback_silencioso_quando_agente_falha() -> None:
    """Given erro de LLM, when gera, then fallback silencioso para o
    template (demo não quebra — story 06)."""
    agent = _FakeAgent(error=RuntimeError("503 upstream"))
    gen = LlmGenerator(agent=agent, retry_delay_s=0.0)

    msg = gen.generate(_holder(), _hail_alert())

    esperado = TemplateGenerator().generate(_holder(), _hail_alert())
    assert msg == esperado
    assert gen.fallbacks == 1
    assert gen.llm_calls == 0


def test_fallback_quando_resposta_vazia() -> None:
    """Given LLM responde vazio, when gera, then fallback."""
    alerts = _hail_alert()
    agent = _FakeAgent("   \n  ")
    gen = LlmGenerator(agent=agent, retry_delay_s=0.0)

    msg = gen.generate(_holder(), alerts)

    assert msg == TemplateGenerator().generate(_holder(), alerts)
    assert gen.fallbacks == 1


def test_saida_longa_truncada_para_limite() -> None:
    """Given LLM excede o limite, when gera, then truncado a 600 chars."""
    agent = _FakeAgent("x" * 700)
    gen = LlmGenerator(agent=agent)

    msg = gen.generate(_holder(), _hail_alert())

    assert len(msg.text) == MAX_MESSAGE_CHARS
    assert msg.text.endswith("…")


def test_prompt_traz_contexto_e_regras_de_tom() -> None:
    """Given rodada, when gera, then prompt tem nome, seguro, evento,
    recomendações e as regras de tom (claro/empático/acionável/600)."""
    agent = _FakeAgent("ok")
    gen = LlmGenerator(agent=agent)
    gen.generate(_holder(), _hail_alert())

    prompt = agent.prompts[0]
    assert "Maria Silva" in prompt
    assert "granizo" in prompt.lower()
    assert "auto" in prompt.lower()
    assert "empátic" in prompt.lower()
    assert "acionável" in prompt.lower()
    assert str(MAX_MESSAGE_CHARS) in prompt
    # Bateria (intent 008): célula do ramo contratado com impactos,
    # fases e regras transversais (incl. proibição de pós-sinistro).
    assert "local coberto" in prompt  # rec da célula Auto do granizo
    assert "impacto possível" in prompt
    assert "[Carro]" in prompt  # ramo contratado do segurado
    assert "[Carro][Antes]" in prompt
    assert "pós-sinistro" in prompt  # regra transversal 5
    assert "199" in prompt  # hail HIGH → vermelho → telefones (regra 3)


def test_mode_label_llm_quando_sem_fallback() -> None:
    gen = LlmGenerator(agent=_FakeAgent("msg ok"))
    gen.generate(_holder(), _hail_alert())

    assert gen.mode_label() == "llm"


def test_retry_recupera_falha_transitoria() -> None:
    """Given falha na 1ª chamada (ex.: 429) e sucesso depois, then o
    retry recupera e a mensagem sai do LLM (sem fallback)."""
    agent = _FakeAgent(
        outputs=["msg veio no retry"],
        error=RuntimeError("429 rate limited"),
        fail_first=1,
    )
    gen = LlmGenerator(agent=agent, retry_delay_s=0.0)

    msg = gen.generate(_holder(), _hail_alert())

    assert gen.llm_calls == 1
    assert gen.fallbacks == 0
    assert msg.text == "msg veio no retry"


def test_retries_esgotados_caim_no_fallback() -> None:
    """Given falha persistente, then fallback silencioso após retries."""
    agent = _FakeAgent(error=RuntimeError("fora do ar"))
    gen = LlmGenerator(
        agent=agent, retry_attempts=2, retry_delay_s=0.0
    )

    msg = gen.generate(_holder(), _hail_alert())

    esperado = TemplateGenerator().generate(_holder(), _hail_alert())
    assert msg == esperado
    assert gen.fallbacks == 1
    assert gen.llm_calls == 0


def test_mode_label_template_quando_llm_indisponivel() -> None:
    gen = LlmGenerator(
        agent=_FakeAgent(error=RuntimeError("chave ausente")),
        retry_delay_s=0.0,
    )
    gen.generate(_holder(), _hail_alert())

    label = gen.mode_label()
    assert "template" in label
    assert "fallback" in label


def test_mode_label_hibrido() -> None:
    """Given retries da 1ª mensagem esgotados e 2ª com sucesso, then
    híbrido (1 fallback + 1 do LLM)."""
    agent = _FakeAgent(
        outputs=["segunda veio do LLM"],
        error=RuntimeError("falha momentanea"),
        fail_first=3,  # esgota os 3 attempts da 1ª mensagem
    )
    gen = LlmGenerator(agent=agent, retry_delay_s=0.0)
    gen.generate(_holder(), _hail_alert())
    gen.generate(_holder(), _hail_alert())

    assert gen.llm_calls == 1
    assert gen.fallbacks == 1
    label = gen.mode_label()
    assert "híbrido" in label
    assert "llm" in label.lower()
    assert "template" in label.lower()


def test_lazy_agent_sem_sdk_delega_para_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given pydantic-ai ausente na criação lazy, when gera, then
    fallback silencioso (sem crash — CI sem rede)."""
    gen = LlmGenerator()

    def _boom() -> object:
        raise ImportError("pydantic_ai not installed")

    monkeypatch.setattr(gen, "_create_agent", _boom)

    msg = gen.generate(_holder(), _hail_alert())

    assert gen.fallbacks == 1
    assert gen.llm_calls == 0
    assert msg == TemplateGenerator().generate(_holder(), _hail_alert())


def test_agente_openrouter_nasce_com_timeout_curto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Revisão de desempenho (008): o agente OpenRouter real nasce com
    timeout curto (LLM_TIMEOUT_S) — o default do SDK (600 s) pendurava a
    rodada inteira quando a rede travava. EMENDA (2026-09-13): o timeout
    tem de estar NO CONSTRUTOR do AsyncOpenAI — o SDK aplica o próprio
    timeout por requisição e sobrescreve o do http_client."""
    pydantic_ai = pytest.importorskip("pydantic_ai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "123456:chave-de-teste")

    agente = LlmGenerator()._create_agent()  # noqa: SLF001 (teste)

    modelo = agente.model
    assert isinstance(modelo, pydantic_ai.models.openai.OpenAIModel)
    assert modelo.model_name == "z-ai/glm-5.3-flash"
    # Timeout EFETIVO: o do AsyncOpenAI (aplicado por requisição).
    cliente = modelo.provider.client  # noqa: SLF001 (SDK)
    assert cliente.timeout == LLM_TIMEOUT_S
    assert cliente.max_retries == 0
    # O httpx client também carrega o teto (defesa em profundidade).
    http_client = cliente._client  # noqa: SLF001 (SDK)
    assert http_client.timeout.connect == LLM_TIMEOUT_S
    assert http_client.timeout.read == LLM_TIMEOUT_S


def test_sem_api_key_cai_no_fallback_sem_rede(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given OPENROUTER_API_KEY ausente, when gera com agente real, then
    o provider falha na criação e o fallback silencioso assume."""
    pytest.importorskip("pydantic_ai")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    gen = LlmGenerator(retry_delay_s=0.0)
    msg = gen.generate(_holder(), _hail_alert())

    assert gen.fallbacks == 1
    assert gen.llm_calls == 0
    assert msg == TemplateGenerator().generate(_holder(), _hail_alert())


# --- intent 007: mensagem consolidada (≥2 riscos → UM aviso) ---


class TestLlmGeneratorConsolidated:
    def test_consolidado_llm_com_todos_os_eventos_no_prompt(self) -> None:
        """Given 2 alertas, when generate_consolidated, then prompt lista
        os 2 eventos + recomendações de cada um e a saída sai do LLM."""
        agent = _FakeAgent("Ola Maria! Granizo e onda de calor. Proteja-se.")
        gen = LlmGenerator(agent=agent)

        msg = gen.generate_consolidated(
            _holder(), [_hail_alert(), _heat_wave_alert()]
        )

        assert msg.holder_id == "H001"
        assert msg.alert_kind is RiskKind.MULTIPLE_RISKS
        assert msg.text == "Ola Maria! Granizo e onda de calor. Proteja-se."
        assert gen.llm_calls == 1
        assert gen.fallbacks == 0
        prompt = agent.prompts[0]
        assert "Maria Silva" in prompt
        assert "granizo" in prompt.lower()
        assert "onda de calor" in prompt.lower()
        assert "local coberto" in prompt  # rec da célula Auto do granizo
        assert "pneus" in prompt  # rec da célula Auto da onda de calor
        assert "nível global" in prompt  # INMET global (evento mais severo)

    def test_consolidado_fallback_silencioso_para_template(self) -> None:
        """Given erro de LLM, when generate_consolidated, then fallback
        para o template consolidado (mesma mensagem do Template)."""
        agent = _FakeAgent(error=RuntimeError("503 upstream"))
        gen = LlmGenerator(agent=agent, retry_delay_s=0.0)
        alerts = [_hail_alert(), _heat_wave_alert()]

        msg = gen.generate_consolidated(_holder(), alerts)

        esperado = TemplateGenerator().generate_consolidated(
            _holder(), alerts
        )
        assert msg == esperado
        assert gen.fallbacks == 1
        assert gen.llm_calls == 0

    def test_consolidado_saida_longa_truncada_para_limite(self) -> None:
        agent = _FakeAgent("x" * 700)
        gen = LlmGenerator(agent=agent)

        msg = gen.generate_consolidated(
            _holder(), [_hail_alert(), _heat_wave_alert()]
        )

        assert len(msg.text) == MAX_MESSAGE_CHARS
        assert msg.text.endswith("…")


def test_factory_padrao_e_template(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given envs ausentes, when build, then TemplateGenerator (default)."""
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    gen = build_generator()

    assert not isinstance(gen, LlmGenerator)
    assert describe_mode(gen) == "template"


def test_factory_llm_quando_llm_model_setado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    gen = build_generator()

    assert isinstance(gen, LlmGenerator)
    assert gen.model == "openrouter:z-ai/glm-5.3-flash"


def test_factory_provider_llm_usa_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "llm")

    gen = build_generator()

    assert isinstance(gen, LlmGenerator)
    assert gen.model == DEFAULT_MODEL


def test_factory_provider_template_forca_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given LLM_PROVIDER=template, then força template mesmo com model."""
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    monkeypatch.setenv("LLM_PROVIDER", "template")

    gen = build_generator()

    assert not isinstance(gen, LlmGenerator)
    assert describe_mode(gen) == "template"
