"""Testes do pipeline de rodada — story 07 (relatório) + story 01 (falha)."""

from app.adapters.fixtures import FixtureWeatherProvider
from app.domain.holders import InsuranceType, PolicyHolder
from app.domain.messages import TemplateGenerator
from app.domain.notify import SimulatedSender
from app.domain.ports import WeatherProviderError
from app.domain.risk import RiskEngine, RiskKind
from app.domain.weather import GeoLocation
from app.pipeline import run_round

_SP = {"weathercode": 96, "precipitation_mm_h": 1.0, "wind_kmh": 10.0,
       "temperature_c": 22.0}  # granizo
_RAIN = {"weathercode": 65, "precipitation_mm_h": 12.0, "wind_kmh": 10.0,
         "temperature_c": 18.0}  # chuva intensa


def _holder(id_, name, types, coastal=False, lat=-23.55, lon=-46.63):
    return PolicyHolder(
        id=id_,
        name=name,
        phone=f"+55119999900{id_[-1]}",
        location=GeoLocation(latitude=lat, longitude=lon),
        insurance_types=frozenset(types),
        is_coastal=coastal,
    )


class _MapRepository:
    """Fake do PolicyHolderRepository com lista em memória."""

    def __init__(self, holders):
        self._holders = list(holders)

    def list_all(self):
        return list(self._holders)


def test_rodada_completa_offline_end_to_end(capsys):
    """Given 2 segurados (residencial em chuva, auto em granizo), when
    run_round, then alertas/mensagens/envios corretos e [SIMULADO] no console."""
    repository = _MapRepository(
        [
            _holder("H001", "Maria Silva", {InsuranceType.RESIDENTIAL},
                    lat=-23.55, lon=-46.63),
            _holder("H002", "João Souza", {InsuranceType.AUTO},
                    lat=-23.53, lon=-46.64),
        ]
    )
    provider = FixtureWeatherProvider(
        snapshots={
            "-23.55|-46.63": _RAIN,
            "-23.53|-46.64": _SP,
        }
    )

    report = run_round(
        repository=repository,
        provider=provider,
        engine=RiskEngine(),
        generator=TemplateGenerator(),
        sender=SimulatedSender(),
    )

    kinds = {a.kind for a in report.alerts}
    assert kinds == {RiskKind.HEAVY_RAIN, RiskKind.HAIL}
    assert report.holders_consulted == 2
    assert report.failures == ()
    assert len(report.messages) == 2
    assert len(report.sends) == 2
    assert all(r.status == "simulated" for r in report.sends)
    out = capsys.readouterr().out
    assert "[SIMULADO]" in out


def test_falha_de_coleta_nao_derruba_a_rodada(capsys):
    """Story 01: given falha de rede para 1 segurado, when pipeline
    executa, then falha registrada e demais continuam processados."""
    repository = _MapRepository(
        [
            _holder("H001", "Maria Silva", {InsuranceType.RESIDENTIAL},
                    lat=-23.55, lon=-46.63),
            _holder("H002", "João Souza", {InsuranceType.AUTO},
                    lat=-23.53, lon=-46.64),
        ]
    )

    class _FailFirstProvider(FixtureWeatherProvider):
        def current(self, location):
            if location.latitude == -23.53:  # H002: erro de "rede"
                raise WeatherProviderError("timeout simulado")
            return super().current(location)

    report = run_round(
        repository=repository,
        provider=_FailFirstProvider(
            snapshots={"-23.55|-46.63": _RAIN}
        ),
        engine=RiskEngine(),
        generator=TemplateGenerator(),
        sender=SimulatedSender(),
    )

    assert report.holders_consulted == 1
    assert len(report.failures) == 1
    assert report.failures[0].holder_id == "H002"
    assert "timeout" in report.failures[0].reason
    assert len(report.alerts) == 1  # H001 processado normalmente
    assert report.alerts[0].holder_id == "H001"


def test_holder_sem_eventos_nao_gera_mensagem_nem_envio():
    """Given segurado com clima neutro, when rodada, then nenhum alerta,
    mensagem ou envio para ele."""
    repository = _MapRepository(
        [_holder("H010", "Neutro Silva", {InsuranceType.RESIDENTIAL})]
    )
    provider = FixtureWeatherProvider(
        snapshots={
            "-23.55|-46.63": {
                "weathercode": 0,
                "precipitation_mm_h": 0.0,
                "wind_kmh": 5.0,
                "temperature_c": 25.0,
            }
        }
    )

    report = run_round(
        repository=repository,
        provider=provider,
        engine=RiskEngine(),
        generator=TemplateGenerator(),
        sender=SimulatedSender(),
    )

    assert report.alerts == ()
    assert report.messages == ()
    assert report.sends == ()
    assert report.holders_consulted == 1
