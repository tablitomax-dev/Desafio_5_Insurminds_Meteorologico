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
            # V2 (intent 005): novos kinds também têm mensagem mapeada.
            (RiskKind.HEAT, "calor"),
            (RiskKind.HEAT_WAVE, "onda de calor"),
            (RiskKind.EXTREME_COLD, "frio"),
            (RiskKind.FOG, "neblina"),
            (RiskKind.STORM, "tempestade"),
            (RiskKind.ROUGH_SEA, "ressaca"),
            (RiskKind.MULTIPLE_RISKS, "riscos meteorológicos"),
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


class TestTemplateGeneratorConsolidated:
    """Mensagem consolidada (intent 007): ≥2 riscos → UMA mensagem."""

    @staticmethod
    def _alert(kind, severity, reason="motivo"):
        from app.domain.risk import RiskAlert

        return RiskAlert(
            kind=kind, severity=severity, reason=reason, holder_id="h-001"
        )

    def test_dois_riscos_geram_uma_mensagem_com_os_dois_eventos(self, generator):
        """Granizo + onda de calor → texto cita os 2 eventos e ao menos
        uma recomendação específica de cada, dentro do limite da story."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)
        wave = self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH)

        msg = generator.generate_consolidated(make_holder("Pablo"), [hail, wave])

        assert msg.holder_id == "h-001"
        assert msg.alert_kind is RiskKind.MULTIPLE_RISKS
        assert "Pablo" in msg.text
        assert "granizo" in msg.text.lower()
        assert "onda de calor" in msg.text.lower()
        assert "estacionamento coberto" in msg.text.lower()  # rec do granizo
        assert "hidrata" in msg.text.lower()  # rec da onda de calor
        assert len(msg.text) <= MAX_MESSAGE_CHARS

    def test_evento_mais_severo_vem_primeiro(self, generator):
        """VERY_HIGH antes de HIGH no texto consolidado."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)
        wave = self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH)

        msg = generator.generate_consolidated(make_holder(), [hail, wave])

        texto = msg.text.lower()
        assert texto.index("onda de calor") < texto.index("granizo")

    def test_resumo_multiple_risks_nao_duplica_no_texto(self, generator):
        """O alerta-resumo MULTIPLE_RISKS não entra na lista de eventos
        (recomendações genéricas viriam duplicadas) — define só o kind."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)
        resumo = self._alert(RiskKind.MULTIPLE_RISKS, Severity.HIGH)

        msg = generator.generate_consolidated(make_holder(), [hail, resumo])

        assert msg.text.lower().count("granizo") == 1
        assert "alertas simultâneos" in msg.text

    def test_tres_riscos_citam_os_tres_e_cabem_no_limite(self, generator):
        from app.domain.risk import Severity

        alerts = [
            self._alert(RiskKind.HEAVY_RAIN, Severity.MEDIUM),
            self._alert(RiskKind.HAIL, Severity.HIGH),
            self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH),
        ]

        msg = generator.generate_consolidated(make_holder(), alerts)

        texto = msg.text.lower()
        assert "chuva intensa" in texto
        assert "granizo" in texto
        assert "onda de calor" in texto
        assert len(msg.text) <= MAX_MESSAGE_CHARS

    def test_recomendacoes_repetidas_entre_eventos_sao_dedupadas(self, generator):
        """Chuva intensa e tempestade compartilham a recomendação de
        raios — no consolidado ela aparece uma única vez."""
        from app.domain.risk import Severity

        rain = self._alert(RiskKind.HEAVY_RAIN, Severity.MEDIUM)
        storm = self._alert(RiskKind.STORM, Severity.HIGH)

        msg = generator.generate_consolidated(make_holder(), [rain, storm])

        assert (
            msg.text.lower().count("desligue aparelhos eletrônicos") == 1
        )

    def test_um_risco_so_nao_deveria_usar_consolidado(self, generator):
        """Com 1 alerta a port individual é a correta — mas o consolidado
        também funciona (documento de comportamento defensável)."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)

        msg = generator.generate_consolidated(make_holder(), [hail])

        assert msg.alert_kind is RiskKind.MULTIPLE_RISKS
        assert "granizo" in msg.text.lower()
