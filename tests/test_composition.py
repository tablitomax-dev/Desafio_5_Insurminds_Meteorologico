"""Testes do composition root compartilhado — intent 003 (UI Streamlit).

CLI e demo visual devem montar o MESMO grafo ports→adapters: fonte
offline/online, modo template/LLM explícito (botões da UI) e env como
fallback quando os parâmetros são omitidos (contrato da story 06).
"""

import json
from pathlib import Path

from app.adapters.fixtures import FixtureWeatherProvider
from app.adapters.open_meteo import OpenMeteoProvider
from app.composition import build_weather_provider, run_proactive_round

_SP = {"weathercode": 96, "precipitation_mm_h": 1.0, "wind_kmh": 10.0,
       "temperature_c": 22.0}


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output


class _FakeAgent:
    def __init__(self, output: str, error: Exception | None = None) -> None:
        self._output = output
        self._error = error

    def run_sync(self, prompt: str, **kwargs: object):  # noqa: ANN201
        if self._error is not None:
            raise self._error
        return _FakeResult(self._output)


def _write_data_dir(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "policy_holders.json").write_text(
        json.dumps(
            [
                {
                    "id": "H001",
                    "name": "Maria Silva",
                    "phone": "+5511999990001",
                    "latitude": -23.55,
                    "longitude": -46.63,
                    "insurance_types": ["auto"],
                    "is_coastal": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    (data / "weather_fixtures.json").write_text(
        json.dumps({"-23.55|-46.63": _SP}), encoding="utf-8"
    )
    return data


def _limpar_env(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_build_weather_provider_offline_e_online():
    """Given o par offline, then fixtures; caso contrario Open-Meteo."""
    assert isinstance(
        build_weather_provider(offline=True, data_dir=Path("data")),
        FixtureWeatherProvider,
    )
    assert isinstance(
        build_weather_provider(offline=False, data_dir=Path("data")),
        OpenMeteoProvider,
    )


def test_rodada_offline_template_default(tmp_path, monkeypatch):
    """Given env limpa, when rodada offline sem opções LLM, then relatório
    completo: granizo → alerta auto (high), mensagem e envio simulado."""
    _limpar_env(monkeypatch)
    data = _write_data_dir(tmp_path)

    report, mode = run_proactive_round(offline=True, data_dir=data)

    assert report.holders_consulted == 1
    assert len(report.alerts) == 1
    assert report.alerts[0].kind.value == "hail"
    assert report.alerts[0].severity.value == "high"
    assert len(report.messages) == 1
    assert len(report.sends) == 1
    assert report.sends[0].status == "simulated"
    assert mode == "template"
    # intent 003 (UI da banca): snapshot de cada segurado consultado
    assert len(report.snapshots) == 1
    holder_id, snapshot = report.snapshots[0]
    assert holder_id == "H001"
    assert snapshot.condition.value == "hail"  # fixture: weathercode 96
    assert snapshot.temperature_c == 22.0


def test_seeds_da_demo_tem_cidade_para_a_ui():
    """Given seeds versionados (intent 003), when load, then todos os
    segurados têm city preenchida (tabela Segurados monitorados)."""
    from app.adapters.catalog import load_policy_holders

    holders = load_policy_holders(Path("data") / "policy_holders.json")

    assert holders
    assert all(h.city for h in holders)


def test_rodada_com_llm_explicito(tmp_path, monkeypatch):
    """Given provider='llm' explícito, then LlmGenerator na rodada e modo
    'llm' — sem depender de env (botão da UI)."""
    from app.adapters import llm_messages

    _limpar_env(monkeypatch)
    data = _write_data_dir(tmp_path)
    fake = _FakeAgent("Ola Maria! Granizo previsto. Cubra o carro.")
    monkeypatch.setattr(
        llm_messages.LlmGenerator, "_create_agent", lambda self: fake
    )

    report, mode = run_proactive_round(
        offline=True, data_dir=data, llm_provider="llm"
    )

    assert mode == "llm"
    assert report.messages[0].text == "Ola Maria! Granizo previsto. Cubra o carro."


def test_rodada_forca_template_mesmo_com_model(tmp_path, monkeypatch):
    """Given provider='template' e model setados, then template vence
    (mesmo contrato do env LLM_PROVIDER=template, agora explícito)."""
    _limpar_env(monkeypatch)
    data = _write_data_dir(tmp_path)

    report, mode = run_proactive_round(
        offline=True,
        data_dir=data,
        llm_model="openrouter:z-ai/glm-5.3-flash",
        llm_provider="template",
    )

    assert mode == "template"


def test_env_continua_fallback_quando_parametros_omitidos(
    tmp_path, monkeypatch
):
    """Given apenas env LLM_MODEL setada (contrato da story 06), when a
    CLI chama sem opções explícitas, then o modo LLM é preservado."""
    from app.adapters import llm_messages

    data = _write_data_dir(tmp_path)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    fake = _FakeAgent("msg do llm via env")
    monkeypatch.setattr(
        llm_messages.LlmGenerator, "_create_agent", lambda self: fake
    )

    report, mode = run_proactive_round(offline=True, data_dir=data)

    assert mode == "llm"
    assert report.messages[0].text == "msg do llm via env"


def test_rodada_usa_holders_e_tempo_editados_pela_bancada(
    tmp_path, monkeypatch
):
    """Given holders editados (nome/telefone/coords) e tempo custom no
    offline (bancada da UI, intent 003), then a rodada usa os dados
    editados e o alerta sai das regras analisando o tempo informado."""
    _limpar_env(monkeypatch)
    data = _write_data_dir(tmp_path)
    from app.domain.holders import InsuranceType, PolicyHolder
    from app.domain.weather import GeoLocation

    holder = PolicyHolder(
        id="H001",
        name="Nome Editado",
        phone="+5511900000000",
        location=GeoLocation(latitude=-23.55, longitude=-46.63),
        insurance_types=frozenset({InsuranceType.RESIDENTIAL}),
        city="Centro, Campinas/SP",
    )
    tempo_editado = {
        "-23.55|-46.63": {
            "weathercode": 61,
            "precipitation_mm_h": 12.0,
            "wind_kmh": 5.0,
            "temperature_c": 20.0,
        }
    }

    report, mode = run_proactive_round(
        offline=True,
        data_dir=data,
        holders=[holder],
        weather_snapshots=tempo_editado,
    )

    assert report.holders_consulted == 1
    # alerta AUTOMÁTICO analisando o tempo editado: 12 mm/h ≥ 10 → chuva
    assert report.alerts[0].kind.value == "heavy_rain"
    assert report.messages[0].text.startswith("Olá, Nome Editado!")
    assert report.snapshots[0][1].precipitation_mm_h == 12.0
    assert mode == "template"


def test_build_generator_provider_explicito(monkeypatch):
    """Given build_generator com provider explícito, then escolha direta
    sem env (exigência dos botões da UI da intent 003)."""
    from app.adapters.llm_messages import (
        DEFAULT_MODEL,
        LlmGenerator,
        TemplateGenerator,
        build_generator,
    )

    _limpar_env(monkeypatch)
    assert isinstance(build_generator(provider="template"), TemplateGenerator)
    assert isinstance(build_generator(provider="llm"), LlmGenerator)
    generator = build_generator(provider="llm", model="openrouter:outro")
    assert isinstance(generator, LlmGenerator)
    assert generator.model == "openrouter:outro"
    default = build_generator(provider="llm")
    assert isinstance(default, LlmGenerator)
    assert default.model == DEFAULT_MODEL
