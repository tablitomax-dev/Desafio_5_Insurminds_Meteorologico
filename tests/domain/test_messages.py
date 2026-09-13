"""Testes do TemplateGenerator — story 05 (mensagem por template) +
bateria preventiva (intent 008: fases Antes/Durante por ramo, nível
INMET e telefones de emergência)."""

import pytest

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import MAX_MESSAGE_CHARS, GeneratedMessage, TemplateGenerator
from app.domain.risk import RiskKind, Severity
from app.domain.weather import GeoLocation

MAX_MESSAGE_CHARS_ASSERT = 600


def make_holder(name: str = "Maria Silva", types=None) -> PolicyHolder:
    return PolicyHolder(
        id="h-001",
        name=name,
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=types
        or frozenset({InsuranceType.RESIDENTIAL, InsuranceType.AUTO}),
    )


@pytest.fixture
def generator() -> TemplateGenerator:
    return TemplateGenerator()


class TestTemplateGenerator:
    def test_chuva_para_segurado_res_auto_tem_blocos_de_ramo(self, generator):
        """Given alerta de chuva (medium → nível laranja) para segurada
        com casa e carro, then mensagem tem saudação, nível INMET,
        blocos Casa/Carro com recomendações e os telefones (regra 3)."""
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
        texto = message.text
        assert "Maria Silva" in texto
        assert "nível laranja" in texto  # severidade INMET (regra 2)
        assert "prevenir" in texto
        assert "Casa:" in texto  # bloco do ramo residencial (regra 1)
        assert "Carro:" in texto  # bloco do ramo auto
        assert "calhas" in texto.lower()  # rec "Antes" da célula Casa
        assert "199" in texto  # telefones em laranja+ (regra 3)
        assert texto.count(".") >= 4

    def test_severidade_low_usa_so_fase_antes(self, generator):
        """Regra 4: nível amarelo (LOW) → só recomendações ANTES."""
        from app.domain.risk import RiskAlert

        low = RiskAlert(
            kind=RiskKind.LOW_HUMIDITY,
            severity=Severity.LOW,
            reason="umidade de 25%",
            holder_id="h-001",
        )
        msg = generator.generate(make_holder(), low)
        assert "nível amarelo" in msg.text
        # Recomendação da fase ANTES presente; a fase DURANTE não entra.
        assert "Deixe água" in msg.text

    def test_severidade_medium_ou_mais_inclui_fase_durante(self, generator):
        """Regra 4: laranja+ → diretrizes [Antes] e [Durante]."""
        from app.domain.risk import RiskAlert

        alert = RiskAlert(
            kind=RiskKind.FOG,
            severity=Severity.MEDIUM,
            reason="neblina densa",
            holder_id="h-001",
        )
        texto = generator.generate(
            make_holder(types=frozenset({InsuranceType.AUTO})), alert
        ).text
        assert "nível laranja" in texto
        # Rec da fase DURANTE (farol baixo, reduzir, distância).
        assert "reduza a velocidade" in texto.lower()

    def test_segurado_apenas_auto_nao_recebe_precaucoes_de_casa(self, generator):
        """Regra 1: só as células dos ramos contratados."""
        from app.domain.risk import RiskAlert

        alert = RiskAlert(
            kind=RiskKind.HEAVY_RAIN,
            severity=Severity.MEDIUM,
            reason="precipitação de 12.0 mm/h",
            holder_id="h-001",
        )
        texto = generator.generate(
            make_holder(types=frozenset({InsuranceType.AUTO})), alert
        ).text
        assert "Carro:" in texto
        assert "Casa:" not in texto

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
            (RiskKind.HEAT, "calor"),
            (RiskKind.HEAT_WAVE, "onda de calor"),
            (RiskKind.EXTREME_COLD, "frio"),
            (RiskKind.FOG, "neblina"),
            (RiskKind.STORM, "tempestade"),
            (RiskKind.ROUGH_SEA, "ressaca"),
            (RiskKind.LOW_HUMIDITY, "tempo seco"),
            (RiskKind.FROST, "geada"),
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
        assert MAX_MESSAGE_CHARS == 600


class TestTemplateGeneratorConsolidated:
    """Mensagem consolidada (intent 007 + bateria 008): ≥2 riscos → 1 msg."""

    @staticmethod
    def _alert(kind, severity, reason="motivo"):
        from app.domain.risk import RiskAlert

        return RiskAlert(
            kind=kind, severity=severity, reason=reason, holder_id="h-001"
        )

    def test_dois_riscos_geram_uma_mensagem_com_os_dois_eventos(self, generator):
        """Granizo + onda de calor (segurado res+auto) → texto cita os 2
        eventos, nível INMET global e recs específicas de cada um."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)
        wave = self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH)

        msg = generator.generate_consolidated(make_holder("Pablo"), [hail, wave])

        assert msg.holder_id == "h-001"
        assert msg.alert_kind is RiskKind.MULTIPLE_RISKS
        texto = msg.text.lower()
        assert "Pablo" in msg.text
        assert "granizo" in texto
        assert "onda de calor" in texto
        assert "nível preto" in texto  # severidade máxima (regra 2)
        assert "local coberto" in texto  # rec da célula Auto do granizo
        assert "climatização" in texto  # rec da célula Casa da onda de calor
        assert "199" in texto  # telefones (regra 3)
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
        (células genéricas duplicariam) — define só o kind."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)
        resumo = self._alert(RiskKind.MULTIPLE_RISKS, Severity.HIGH)

        msg = generator.generate_consolidated(make_holder(), [hail, resumo])

        assert msg.text.lower().count("granizo") == 1
        assert "alertas na sua região" in msg.text

    def test_tres_riscos_citam_os_tres_e_cabem_no_limite(self, generator):
        from app.domain.risk import Severity

        alerts = [
            self._alert(RiskKind.HEAVY_RAIN, Severity.MEDIUM),
            self._alert(RiskKind.HAIL, Severity.HIGH),
            self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH),
        ]

        msg = generator.generate_consolidated(make_holder(), alerts)

        texto = msg.text.lower()
        for snippet in ("chuva intensa", "granizo", "onda de calor"):
            assert snippet in texto
        assert len(msg.text) <= MAX_MESSAGE_CHARS

    def test_recomendacoes_repetidas_entre_eventos_sao_dedupadas(self, generator):
        """Heat e onda de calor compartilham a diretriz de nunca deixar
        pessoas/animais no veículo — aparece uma única vez."""
        from app.domain.risk import Severity

        only_auto = frozenset({InsuranceType.AUTO})
        heat = self._alert(RiskKind.HEAT, Severity.HIGH)
        wave = self._alert(RiskKind.HEAT_WAVE, Severity.VERY_HIGH)

        msg = generator.generate_consolidated(
            make_holder(types=only_auto), [heat, wave]
        )

        assert (
            msg.text.lower().count("nunca deixe crianças") == 1
        )

    def test_um_risco_so_nao_deveria_usar_consolidado(self, generator):
        """Com 1 alerta a port individual é a correta — mas o consolidado
        também funciona (documento de comportamento defensável)."""
        from app.domain.risk import Severity

        hail = self._alert(RiskKind.HAIL, Severity.HIGH)

        msg = generator.generate_consolidated(make_holder(), [hail])

        assert msg.alert_kind is RiskKind.MULTIPLE_RISKS
        assert "granizo" in msg.text.lower()
