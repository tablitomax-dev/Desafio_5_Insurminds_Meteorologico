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
    then WeatherSnapshot com weathercode/precip/vento/temperatura."""
    payload = FIXTURE.read_bytes()

    provider = OpenMeteoProvider(fetch=lambda url, timeout: payload)

    snapshot = provider.current(LOCATION)

    assert snapshot.location == LOCATION
    assert snapshot.weathercode == 65
    assert snapshot.precipitation_mm_h == 12.4
    assert snapshot.wind_kmh == 18.2
    assert snapshot.temperature_c == 21.5


def test_url_montada_com_parametros_da_api():
    """Given segurado com GeoLocation, when coleta, then URL contém
    lat/lon, campos `current` e unidades kmh/mm."""
    captured: dict[str, str] = {}

    def fake_fetch(url: str, timeout: float) -> bytes:
        captured["url"] = url
        return FIXTURE.read_bytes()

    OpenMeteoProvider(fetch=fake_fetch).current(LOCATION)

    url = captured["url"]
    assert "latitude=-23.55" in url
    assert "longitude=-46.63" in url
    assert "current=weather_code" in url
    assert "wind_speed_unit=kmh" in url
    assert "precipitation_unit=mm" in url


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
