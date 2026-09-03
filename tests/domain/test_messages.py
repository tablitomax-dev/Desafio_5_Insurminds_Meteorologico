"""Testes do TemplateGenerator — story 05 (mensagem por template paramétrico)."""

import pytest

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import MAX_MESSAGE_CHARS, GeneratedMessage, TemplateGenerator
from app.domain.risk import RiskKind, Severity
from app.domain.weather import GeoLocation

MAX_MESSAGE_CHARS_ASSERT = 480


def make_holder(name: str = "Maria Silva") -> PolicyHolder:
    return PolicyHolder(
        id="h-001",
        name=name,
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
    )


@pytest.fixture
def generator() -> TemplateGenerator:
    return TemplateGenerator()


class TestTemplateGenerator:
    def test_chuva_para_residencial_tem_saudacao_evento_e_recomendacoes(self, generator):
        """Given RiskAlert de chuva para segurada Maria (RESIDENTIAL), when
        TemplateGenerator gera, then mensagem tem saudação pelo nome, o
        evento, e ≥ 2 recomendações específicas."""
        from app.domain.risk import RiskAlert

        alert = RiskAlert(
            kind=RiskKind.HEAVY_RAIN,
            severity=Severity.MEDIUM,
            reason="precipitação de 12.0 mm/h",
            holder_id="h-001",
        )
        message = generator.generate(make_holder("Maria Silva"), alert)

        assert isinstance(message, GeneratedMessage)
        assert message.holder_id == "h-001"
        assert message.alert_kind is RiskKind.HEAVY_RAIN
        assert "Maria Silva" in message.text
        assert message.text.count("•") >= 2

    def test_mensagem_respeita_limite_de_480_chars(self, generator):
        """Given qualquer alerta, when gerada, then mensagem ≤ 480 chars."""
        from app.domain.risk import RiskAlert

        for kind in RiskKind:
            alert = RiskAlert(
                kind=kind,
                severity=Severity.MEDIUM,
                reason="motivo razoavelmente descritivo do alerta emitido",
                holder_id="h-001",
            )
            message = generator.generate(make_holder(), alert)
            assert len(message.text) <= MAX_MESSAGE_CHARS
            assert len(message.text) <= MAX_MESSAGE_CHARS_ASSERT

    def test_mensagem_nao_vaza_telefone_do_segurado(self, generator):
        """Sem dados sensíveis além do necessário: telefone fora do texto."""
        from app.domain.risk import RiskAlert

        alert = RiskAlert(
            kind=RiskKind.HEAVY_RAIN,
            severity=Severity.MEDIUM,
            reason="chuva intensa",
            holder_id="h-001",
        )
        message = generator.generate(make_holder(), alert)
        assert "+5511999990001" not in message.text

    @pytest.mark.parametrize(
        ("kind", "snippet"),
        [
            (RiskKind.HEAVY_RAIN, "chuva"),
            (RiskKind.HAIL, "granizo"),
            (RiskKind.STRONG_WIND, "vento"),
        ],
    )
    def test_cada_tipo_de_alerta_cita_o_evento(self, generator, kind, snippet):
        from app.domain.risk import RiskAlert

        alert = RiskAlert(
            kind=kind,
            severity=Severity.MEDIUM,
            reason="motivo",
            holder_id="h-001",
        )
        message = generator.generate(make_holder(), alert)
        assert snippet in message.text.lower()

    def test_recomendacoes_sao_especificas_por_tipo(self, generator):
        """Granizo (auto) e vento (litoral) trazem recomendações distintas."""
        from app.domain.risk import RiskAlert

        hail = RiskAlert(
            kind=RiskKind.HAIL, severity=Severity.HIGH, reason="granizo", holder_id="h-001"
        )
        wind = RiskAlert(
            kind=RiskKind.STRONG_WIND,
            severity=Severity.MEDIUM,
            reason="vento",
            holder_id="h-001",
        )
        hail_text = generator.generate(make_holder(), hail).text
        wind_text = generator.generate(make_holder(), wind).text
        assert hail_text != wind_text

    def test_constante_de_limite_de_acordo_com_story(self):
        assert MAX_MESSAGE_CHARS == 480
