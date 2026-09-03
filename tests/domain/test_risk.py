"""Testes do motor de regras de risco — stories 02 (chuva→residencial),
03 (granizo→auto) e 04 (vento→litoral). Núcleo TDD, sem I/O."""

import pytest

from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.risk import (
    HEAVY_RAIN_MM_H,
    STRONG_WIND_KMH,
    HailRule,
    HeavyRainRule,
    RiskEngine,
    RiskKind,
    Severity,
    StrongWindRule,
)
from app.domain.weather import GeoLocation, WeatherSnapshot

# ---------------------------------------------------------------------------
# Builders (given)
# ---------------------------------------------------------------------------


def make_snapshot(
    *, weathercode: int = 0, precipitation: float = 0.0, wind: float = 0.0
) -> WeatherSnapshot:
    return WeatherSnapshot(
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        weathercode=weathercode,
        precipitation_mm_h=precipitation,
        wind_kmh=wind,
        temperature_c=24.0,
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
# Story 02 — chuva intensa → residencial
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

    def test_severidade_medium(self):
        rule = HeavyRainRule()
        alert = rule.evaluate(make_snapshot(precipitation=15.0), make_holder())
        assert alert is not None
        assert alert.severity is Severity.MEDIUM


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
# Story 04 — vento forte → região costeira
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


# ---------------------------------------------------------------------------
# RiskEngine — aplica todas as regras e deduplica por (holder, kind)
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
        assert kinds == {RiskKind.HEAVY_RAIN, RiskKind.HAIL, RiskKind.STRONG_WIND}
        assert all(a.holder_id == "h-multi" for a in alerts)

    def test_sem_condicoes_de_risco_retorna_lista_vazia(self):
        engine = RiskEngine()
        alerts = engine.evaluate(make_snapshot(), make_holder())
        assert alerts == []

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
