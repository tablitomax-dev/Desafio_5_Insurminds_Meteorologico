"""Testes do motor de regras de risco — stories 02 (chuva→residencial),
03 (granizo→auto) e 04 (vento→litoral) + V2 (intent 005: tiers de
severidade, calor/frio/neblina/tempestade/ressaca, MULTIPLE_RISKS).
Núcleo TDD, sem I/O."""

import pytest

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.risk import (
    HEAVY_RAIN_MM_H,
    STRONG_WIND_KMH,
    ExtremeColdRule,
    FogRule,
    HailRule,
    HeatRule,
    HeavyRainRule,
    RiskEngine,
    RiskKind,
    RoughSeaRule,
    Severity,
    StormRule,
    StrongWindRule,
)
from app.domain.weather import GeoLocation, WeatherSnapshot

# ---------------------------------------------------------------------------
# Builders (given)
# ---------------------------------------------------------------------------


def make_snapshot(
    *,
    weathercode: int = 0,
    precipitation: float = 0.0,
    wind: float = 0.0,
    temperature: float = 24.0,
    humidity: float | None = None,
) -> WeatherSnapshot:
    return WeatherSnapshot(
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        weathercode=weathercode,
        precipitation_mm_h=precipitation,
        wind_kmh=wind,
        temperature_c=temperature,
        humidity_pct=humidity,
    )


def make_holder(
    *,
    id: str = "h-001",
    name: str = "Maria Silva",
    types: frozenset[InsuranceType] = frozenset({InsuranceType.RESIDENTIAL}),
    is_coastal: bool = False,
) -> PolicyHolder:
    return PolicyHolder(
        id=id,
        name=name,
        phone="+5511999990001",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=types,
        is_coastal=is_coastal,
    )


# ---------------------------------------------------------------------------
# Story 02 — chuva intensa → residencial (tier base + escalonamento V2)
# ---------------------------------------------------------------------------


class TestHeavyRainRule:
    def test_precipitacao_acima_do_limiar_residencial_gera_alerta(self):
        """Given snapshot com precipitação ≥ limiar (10 mm/h), when avalia
        segurado RESIDENTIAL, then RiskAlert de chuva é gerado."""
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=12.0), make_holder())
        assert alert is not None
        assert alert.kind is RiskKind.HEAVY_RAIN
        assert alert.holder_id == "h-001"

    def test_segurado_apenas_auto_nao_recebe_alerta_de_chuva(self):
        """Given mesmo snapshot, when avaliado segurado apenas AUTO,
        then nenhum alerta."""
        rule = HeavyRainRule()
        holder_auto = make_holder(
            types=frozenset({InsuranceType.AUTO}), id="h-auto"
        )
        assert rule.evaluate(make_snapshot(precipitation=12.0), holder_auto) is None

    def test_precipitacao_abaixo_do_limiar_nao_gera_alerta(self):
        """Given precipitação abaixo do limiar, when avaliado,
        then nenhum alerta."""
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=HEAVY_RAIN_MM_H - 0.5), make_holder())
        assert alert is None

    def test_precipitacao_exatamente_no_limiar_gera_alerta(self):
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=HEAVY_RAIN_MM_H), make_holder())
        assert alert is not None

    def test_limiar_e_configuravel(self):
        rule = HeavyRainRule(threshold_mm_h=5.0)
        alert = rule.evaluate(make_snapshot(precipitation=6.0), make_holder())
        assert alert is not None

    def test_severidade_medium_no_tier_base(self):
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=15.0), make_holder())
        assert alert is not None
        assert alert.severity is Severity.MEDIUM

    def test_chuva_20_mm_escala_para_high(self):
        """V2: chuva ≥20 mm/h → HIGH."""
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=25.0), make_holder())
        assert alert is not None
        assert alert.severity is Severity.HIGH

    def test_chuva_35_mm_escala_para_very_high(self):
        """V2: chuva ≥35 mm/h → VERY_HIGH."""
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=40.0), make_holder())
        assert alert is not None
        assert alert.severity is Severity.VERY_HIGH


# ---------------------------------------------------------------------------
# Story 03 — granizo → automóvel
# ---------------------------------------------------------------------------


class TestHailRule:
    @pytest.mark.parametrize("code", [96, 99])
    def test_weathercode_de_granizo_auto_gera_alerta(self, code):
        """Given snapshot com weathercode de granizo (Open-Meteo), when
        HailRule avalia segurado AUTO, then RiskAlert de granizo é gerado."""
        rule = HailRule()
        holder = make_holder(types=frozenset({InsuranceType.AUTO}), id="h-auto")
        alert = rule.evaluate(make_snapshot(weathercode=code), holder)
        assert alert is not None
        assert alert.kind is RiskKind.HAIL
        assert alert.holder_id == "h-auto"

    def test_chuva_simples_nao_gera_alerta_de_granizo(self):
        """Given weathercode de chuva simples, when avaliado segurado AUTO,
        then nenhum alerta de granizo."""
        rule = HailRule()
        holder = make_holder(types=frozenset({InsuranceType.AUTO}), id="h-auto")
        assert rule.evaluate(make_snapshot(weathercode=61), holder) is None

    def test_granizo_sem_seguro_auto_nao_gera_alerta(self):
        rule = HailRule()
        holder = make_holder(types=frozenset({InsuranceType.RESIDENTIAL}))
        assert rule.evaluate(make_snapshot(weathercode=99), holder) is None

    def test_severidade_high(self):
        rule = HailRule()
        holder = make_holder(types=frozenset({InsuranceType.AUTO}))
        alert = rule.evaluate(make_snapshot(weathercode=96), holder)
        assert alert is not None
        assert alert.severity is Severity.HIGH


# ---------------------------------------------------------------------------
# Story 04 — vento forte → região costeira (tier base + escalonamento V2)
# ---------------------------------------------------------------------------


class TestStrongWindRule:
    def test_vento_acima_do_limiar_costeiro_gera_alerta(self):
        """Given snapshot com vento ≥ limiar (60 km/h), when StrongWindRule
        avalia segurado marcado região costeira, then alerta gerado."""
        rule = StrongWindRule()
        holder = make_holder(is_coastal=True, id="h-costa")
        alert = rule.evaluate(make_snapshot(wind=65.0), holder)
        assert alert is not None
        assert alert.kind is RiskKind.STRONG_WIND
        assert alert.holder_id == "h-costa"

    def test_segurado_nao_costeiro_com_mesmo_vento_nao_recebe_alerta(self):
        """Given segurado não-costeiro com mesmo vento, when avaliado,
        then nenhum alerta (regra restrita à costa)."""
        rule = StrongWindRule()
        holder = make_holder(is_coastal=False)
        assert rule.evaluate(make_snapshot(wind=65.0), holder) is None

    def test_vento_abaixo_do_limiar_nao_gera_alerta(self):
        rule = StrongWindRule()
        holder = make_holder(is_coastal=True)
        alert = rule.evaluate(make_snapshot(wind=STRONG_WIND_KMH - 1.0), holder)
        assert alert is None

    def test_limiar_e_configuravel(self):
        rule = StrongWindRule(threshold_kmh=40.0)
        holder = make_holder(is_coastal=True)
        alert = rule.evaluate(make_snapshot(wind=45.0), holder)
        assert alert is not None

    def test_vento_80_km_escala_para_very_high(self):
        """V2: vento ≥80 km/h → VERY_HIGH (ainda restrito ao litoral)."""
        rule = StrongWindRule()
        holder = make_holder(is_coastal=True)
        alert = rule.evaluate(make_snapshot(wind=85.0), holder)
        assert alert is not None
        assert alert.severity is Severity.VERY_HIGH

    def test_vento_80_km_nao_costeiro_nao_gera_alerta(self):
        rule = StrongWindRule()
        holder = make_holder(is_coastal=False)
        assert rule.evaluate(make_snapshot(wind=85.0), holder) is None


# ---------------------------------------------------------------------------
# V2 — calor, onda de calor, frio (intent 005)
# ---------------------------------------------------------------------------


class TestHeatRule:
    def test_35_graus_gera_calor_high(self):
        rule = HeatRule()
        alert = rule.evaluate(make_snapshot(temperature=36.0), make_holder())
        assert alert is not None
        assert alert.kind is RiskKind.HEAT
        assert alert.severity is Severity.HIGH

    def test_segurado_auto_tambem_recebe_calor(self):
        """Escopo por ramo: AUTO tem exposição material (pneus, bateria)."""
        rule = HeatRule()
        holder = make_holder(
            types=frozenset({InsuranceType.AUTO}), id="h-auto"
        )
        alert = rule.evaluate(make_snapshot(temperature=36.0), holder)
        assert alert is not None
        assert alert.kind is RiskKind.HEAT

    def test_segurado_sem_ramo_com_exposicao_nao_recebe_calor(self):
        """Classificação do dono: calor só para RESIDENTIAL/AUTO."""
        rule = HeatRule()
        holder = make_holder(types=frozenset(), id="h-vazio")
        assert rule.evaluate(make_snapshot(temperature=40.0), holder) is None

    def test_38_graus_vira_onda_de_calor_very_high(self):
        rule = HeatRule()
        alert = rule.evaluate(make_snapshot(temperature=39.0), make_holder())
        assert alert is not None
        assert alert.kind is RiskKind.HEAT_WAVE
        assert alert.severity is Severity.VERY_HIGH

    def test_abaixo_de_35_nao_gera_alerta(self):
        rule = HeatRule()
        assert rule.evaluate(make_snapshot(temperature=34.9), make_holder()) is None


class TestExtremeColdRule:
    def test_10_graus_gera_frio_high(self):
        rule = ExtremeColdRule()
        alert = rule.evaluate(make_snapshot(temperature=8.0), make_holder())
        assert alert is not None
        assert alert.kind is RiskKind.EXTREME_COLD
        assert alert.severity is Severity.HIGH

    def test_segurado_sem_ramo_com_exposicao_nao_recebe_frio(self):
        rule = ExtremeColdRule()
        holder = make_holder(types=frozenset(), id="h-vazio")
        assert rule.evaluate(make_snapshot(temperature=2.0), holder) is None

    def test_5_graus_escala_para_very_high(self):
        rule = ExtremeColdRule()
        alert = rule.evaluate(make_snapshot(temperature=4.0), make_holder())
        assert alert is not None
        assert alert.severity is Severity.VERY_HIGH

    def test_acima_de_10_nao_gera_alerta(self):
        rule = ExtremeColdRule()
        assert rule.evaluate(make_snapshot(temperature=10.1), make_holder()) is None


# ---------------------------------------------------------------------------
# V2 — neblina (depende de umidade; pula quando desconhecida)
# ---------------------------------------------------------------------------


class TestFogRule:
    def test_umidade_95_pouco_vento_gera_neblina_medium(self):
        rule = FogRule()
        alert = rule.evaluate(
            make_snapshot(temperature=16.0, humidity=96.0, wind=10.0),
            make_holder(types=frozenset({InsuranceType.AUTO})),
        )
        assert alert is not None
        assert alert.kind is RiskKind.FOG
        assert alert.severity is Severity.MEDIUM

    def test_segurado_apenas_residencial_nao_recebe_neblina(self):
        """Escopo por ramo: visibilidade/colisões são risco do condutor."""
        rule = FogRule()
        assert (
            rule.evaluate(
                make_snapshot(humidity=97.0, wind=10.0), make_holder()
            )
            is None
        )

    def test_umidade_98_escala_para_high(self):
        rule = FogRule()
        alert = rule.evaluate(
            make_snapshot(temperature=16.0, humidity=98.5, wind=8.0),
            make_holder(types=frozenset({InsuranceType.AUTO})),
        )
        assert alert is not None
        assert alert.severity is Severity.HIGH

    def test_umidade_abaixo_de_95_nao_gera_alerta(self):
        rule = FogRule()
        assert (
            rule.evaluate(
                make_snapshot(humidity=90.0, wind=10.0),
                make_holder(types=frozenset({InsuranceType.AUTO})),
            )
            is None
        )

    def test_vento_forte_nao_e_neblina(self):
        rule = FogRule()
        assert (
            rule.evaluate(
                make_snapshot(humidity=97.0, wind=20.0),
                make_holder(types=frozenset({InsuranceType.AUTO})),
            )
            is None
        )

    def test_chuva_forte_nao_e_neblina(self):
        rule = FogRule()
        assert (
            rule.evaluate(
                make_snapshot(precipitation=15.0, humidity=97.0, wind=10.0),
                make_holder(types=frozenset({InsuranceType.AUTO})),
            )
            is None
        )

    def test_umidade_desconhecida_pula_a_avaliacao(self):
        """Degradação graciosa: sem umidade (None), a regra não dispara."""
        rule = FogRule()
        assert (
            rule.evaluate(
                make_snapshot(humidity=None, wind=5.0),
                make_holder(types=frozenset({InsuranceType.AUTO})),
            )
            is None
        )


# ---------------------------------------------------------------------------
# V2 — tempestade e ressaca (regras compostas)
# ---------------------------------------------------------------------------


class TestStormRule:
    def test_chuva_30_com_vento_60_gera_tempestade_high(self):
        rule = StormRule()
        alert = rule.evaluate(
            make_snapshot(precipitation=32.0, wind=65.0), make_holder()
        )
        assert alert is not None
        assert alert.kind is RiskKind.STORM
        assert alert.severity is Severity.HIGH

    def test_segurado_auto_tambem_recebe_tempestade(self):
        rule = StormRule()
        holder = make_holder(
            types=frozenset({InsuranceType.AUTO}), id="h-auto"
        )
        alert = rule.evaluate(
            make_snapshot(precipitation=32.0, wind=65.0), holder
        )
        assert alert is not None
        assert alert.kind is RiskKind.STORM

    def test_segurado_sem_ramo_com_exposicao_nao_recebe_tempestade(self):
        rule = StormRule()
        holder = make_holder(types=frozenset(), id="h-vazio")
        assert (
            rule.evaluate(
                make_snapshot(precipitation=40.0, wind=90.0), holder
            )
            is None
        )

    def test_chuva_35_com_vento_80_escala_para_very_high(self):
        rule = StormRule()
        alert = rule.evaluate(
            make_snapshot(precipitation=36.0, wind=85.0), make_holder()
        )
        assert alert is not None
        assert alert.severity is Severity.VERY_HIGH

    def test_chuva_forte_sem_vento_nao_e_tempestade(self):
        rule = StormRule()
        assert (
            rule.evaluate(make_snapshot(precipitation=40.0, wind=30.0), make_holder())
            is None
        )

    def test_vento_forte_sem_chuva_nao_e_tempestade(self):
        rule = StormRule()
        assert (
            rule.evaluate(make_snapshot(precipitation=10.0, wind=90.0), make_holder())
            is None
        )


class TestRoughSeaRule:
    def test_litoral_vento_80_e_chuva_30_gera_ressaca(self):
        rule = RoughSeaRule()
        holder = make_holder(is_coastal=True, id="h-costa")
        alert = rule.evaluate(
            make_snapshot(precipitation=32.0, wind=85.0), holder
        )
        assert alert is not None
        assert alert.kind is RiskKind.ROUGH_SEA
        assert alert.severity is Severity.VERY_HIGH

    def test_litoral_apenas_auto_nao_recebe_ressaca(self):
        """Escopo por ramo: imóvel litorâneo é a exposição da ressaca."""
        rule = RoughSeaRule()
        holder = make_holder(
            types=frozenset({InsuranceType.AUTO}),
            is_coastal=True,
            id="h-costa-auto",
        )
        assert (
            rule.evaluate(make_snapshot(precipitation=40.0, wind=90.0), holder)
            is None
        )

    def test_nao_costeiro_nao_recebe_ressaca(self):
        rule = RoughSeaRule()
        holder = make_holder(is_coastal=False)
        assert (
            rule.evaluate(make_snapshot(precipitation=40.0, wind=90.0), holder)
            is None
        )

    def test_litoral_com_vento_abaixo_de_80_nao_gera_ressaca(self):
        rule = RoughSeaRule()
        holder = make_holder(is_coastal=True)
        assert (
            rule.evaluate(make_snapshot(precipitation=40.0, wind=70.0), holder)
            is None
        )


# ---------------------------------------------------------------------------
# RiskEngine — aplica todas as regras, deduplica e consolida (V2)
# ---------------------------------------------------------------------------


class TestRiskEngine:
    def test_aplica_todas_as_regras_e_coleta_alertas(self):
        engine = RiskEngine()
        holder = make_holder(
            types=frozenset({InsuranceType.RESIDENTIAL, InsuranceType.AUTO}),
            is_coastal=True,
            id="h-multi",
        )
        # chuva intensa + granizo + vento forte de uma vez
        snapshot = make_snapshot(
            weathercode=99, precipitation=15.0, wind=70.0
        )
        alerts = engine.evaluate(snapshot, holder)
        kinds = {a.kind for a in alerts}
        # V2: os 3 individuais + resumo MULTIPLE_RISKS (atualização
        # deliberada — consolidação aditiva aprovada no intent 005).
        assert kinds == {
            RiskKind.HEAVY_RAIN,
            RiskKind.HAIL,
            RiskKind.STRONG_WIND,
            RiskKind.MULTIPLE_RISKS,
        }
        assert all(a.holder_id == "h-multi" for a in alerts)
        # resumo vem por ÚLTIMO e carrega a severidade máxima (HIGH).
        assert alerts[-1].kind is RiskKind.MULTIPLE_RISKS
        assert alerts[-1].severity is Severity.HIGH

    def test_sem_condicoes_de_risco_retorna_lista_vazia(self):
        engine = RiskEngine()
        alerts = engine.evaluate(make_snapshot(), make_holder())
        assert alerts == []

    def test_um_risco_so_nao_gera_resumo(self):
        """V2: consolidação só acontece com ≥2 riscos simultâneos."""
        engine = RiskEngine()
        alerts = engine.evaluate(make_snapshot(precipitation=15.0), make_holder())
        assert len(alerts) == 1
        assert alerts[0].kind is RiskKind.HEAVY_RAIN

    def test_cenario_de_tempestade_no_litoral_consolida_very_high(self):
        """Chuva 36 + vento 85 no litoral: chuva, vento, tempestade e
        ressaca + resumo VERY_HIGH (máxima entre os individuais)."""
        engine = RiskEngine()
        holder = make_holder(
            types=frozenset({InsuranceType.RESIDENTIAL}),
            is_coastal=True,
            id="h-costa",
        )
        alerts = engine.evaluate(
            make_snapshot(precipitation=36.0, wind=85.0, temperature=26.0),
            holder,
        )
        kinds = [a.kind for a in alerts]
        assert kinds == [
            RiskKind.HEAVY_RAIN,
            RiskKind.STRONG_WIND,
            RiskKind.STORM,
            RiskKind.ROUGH_SEA,
            RiskKind.MULTIPLE_RISKS,
        ]
        assert alerts[-1].severity is Severity.VERY_HIGH

    def test_dedup_por_holder_e_kind(self):
        """Duas regras do mesmo kind não duplicam o alerta."""

        class RainRuleExtra:
            def evaluate(self, snapshot, holder):
                return HeavyRainRule().evaluate(snapshot, holder)

        engine = RiskEngine(rules=(HeavyRainRule(), RainRuleExtra()))
        alerts = engine.evaluate(make_snapshot(precipitation=20.0), make_holder())
        assert len(alerts) == 1
        assert alerts[0].kind is RiskKind.HEAVY_RAIN

    def test_aceita_regras_que_cumprem_o_protocolo(self):
        class RuleFake:
            def evaluate(self, snapshot, holder):
                return None

        # Duck typing: qualquer objeto com evaluate(snapshot, holder) é regra.
        engine = RiskEngine(rules=(RuleFake(),))
        assert engine.evaluate(make_snapshot(), make_holder()) == []
