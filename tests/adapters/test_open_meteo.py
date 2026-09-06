"""Testes do adapter Open-Meteo — story 01 (coleta por segurado).

Contrato testado contra fixture gravada (sem rede), retry simples e
erro de domínio tipado (WeatherProviderError — sem stack trace cru).
"""

import json
from pathlib import Path
from urllib.error import URLError

import pytest

from app.adapters.open_meteo import OpenMeteoProvider
from app.domain.ports import WeatherProviderError
from app.domain.weather import GeoLocation

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "open_meteo"
    / "current_response.json"
)

LOCATION = GeoLocation(latitude=-23.55, longitude=-46.63)


def test_parse_da_resposta_gravada():
    """Given resposta real gravada do endpoint `current`, when parse,
    then WeatherSnapshot com weathercode/precip/vento/temperatura/umidade."""
    payload = FIXTURE.read_bytes()

    provider = OpenMeteoProvider(fetch=lambda url, timeout: payload)

    snapshot = provider.current(LOCATION)

    assert snapshot.location == LOCATION
    assert snapshot.weathercode == 65
    assert snapshot.precipitation_mm_h == 12.4
    assert snapshot.wind_kmh == 18.2
    assert snapshot.temperature_c == 21.5
    assert snapshot.humidity_pct == 87.0


def test_umidade_ausente_ou_nula_vira_none_sem_quebrar_parse():
    """V2 (intent 005): degradação graciosa — `relative_humidity_2m`
    ausente ou null → humidity_pct None (não é erro de parse)."""
    sem_humidade = json.dumps(
        {
            "current": {
                "weather_code": 0,
                "temperature_2m": 25.0,
                "precipitation": 0.0,
                "wind_speed_10m": 5.0,
            }
        }
    ).encode()
    com_null = json.dumps(
        {
            "current": {
                "weather_code": 0,
                "temperature_2m": 25.0,
                "precipitation": 0.0,
                "wind_speed_10m": 5.0,
                "relative_humidity_2m": None,
            }
        }
    ).encode()

    snapshot_sem = OpenMeteoProvider(fetch=lambda url, t: sem_humidade).current(
        LOCATION
    )
    snapshot_null = OpenMeteoProvider(fetch=lambda url, t: com_null).current(
        LOCATION
    )

    assert snapshot_sem.humidity_pct is None
    assert snapshot_null.humidity_pct is None


def test_url_montada_com_parametros_da_api():
    """Given segurado com GeoLocation, when coleta, then URL contém
    lat/lon com 4 casas decimais (recomendação Open-Meteo), campos
    `current` e unidades kmh/mm."""
    captured: dict[str, str] = {}

    def fake_fetch(url: str, timeout: float) -> bytes:
        captured["url"] = url
        return FIXTURE.read_bytes()

    OpenMeteoProvider(fetch=fake_fetch).current(LOCATION)

    url = captured["url"]
    assert "latitude=-23.5500" in url
    assert "longitude=-46.6300" in url
    assert "current=weather_code" in url
    assert "relative_humidity_2m" in url
    assert "wind_speed_unit=kmh" in url
    assert "precipitation_unit=mm" in url


def test_url_arredonda_coordenadas_para_4_casas():
    """Given lat/lon com mais casas decimais, when coleta, then URL usa
    coordenadas arredondadas a 4 casas (intent 003 — pedido do dono)."""
    captured: dict[str, str] = {}
    precise = GeoLocation(latitude=-23.5505231, longitude=-46.63098765)

    OpenMeteoProvider(
        fetch=lambda url, timeout: captured.update(url=url) or FIXTURE.read_bytes()
    ).current(precise)

    assert "latitude=-23.5505" in captured["url"]
    assert "longitude=-46.6310" in captured["url"]


def test_falha_de_rede_vira_erro_de_dominio():
    """Given URLError do urllib, when adapter executa, then
    WeatherProviderError (erro tipado, sem vazar URLError)."""

    def failing_fetch(url: str, timeout: float) -> bytes:
        raise URLError("connection refused")

    provider = OpenMeteoProvider(fetch=failing_fetch, max_retries=1)

    with pytest.raises(WeatherProviderError, match="Open-Meteo"):
        provider.current(LOCATION)


def test_retry_esgota_e_levanta_erro_de_dominio():
    """Given fetch que falha sempre, when retries esgotam, then
    WeatherProviderError e nº de tentativas == max_retries."""
    attempts: list[int] = []

    def failing_fetch(url: str, timeout: float) -> bytes:
        attempts.append(1)
        raise TimeoutError("timed out")

    provider = OpenMeteoProvider(
        fetch=failing_fetch, max_retries=3, retry_delay_s=0.0
    )

    with pytest.raises(WeatherProviderError):
        provider.current(LOCATION)

    assert len(attempts) == 3


def test_resposta_invalida_vira_erro_de_dominio():
    """Given JSON sem a chave `current`, when parse, then
    WeatherProviderError (dados inválidos são erro de domínio)."""
    bad = json.dumps({"latitude": -23.55}).encode()

    provider = OpenMeteoProvider(fetch=lambda url, timeout: bad)

    with pytest.raises(WeatherProviderError, match="inválida"):
        provider.current(LOCATION)
