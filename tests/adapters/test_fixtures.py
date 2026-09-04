"""Testes do FixtureWeatherProvider — replay offline (story 07 --offline)."""

import json

import pytest

from app.adapters.fixtures import FixtureWeatherProvider
from app.domain.ports import WeatherProviderError
from app.domain.weather import GeoLocation, WeatherSnapshot

_DATA = {
    "-23.55|-46.63": {
        "weathercode": 65,
        "precipitation_mm_h": 12.0,
        "wind_kmh": 15.0,
        "temperature_c": 18.0,
    }
}


def test_replay_retorna_snapshot_gravado():
    """Given fixture gravada para a chave lat|lon, when coleta, then
    WeatherSnapshot com os valores gravados e a location pedida."""
    provider = FixtureWeatherProvider(snapshots=_DATA)

    snapshot = provider.current(GeoLocation(latitude=-23.55, longitude=-46.63))

    assert snapshot.weathercode == 65
    assert snapshot.precipitation_mm_h == 12.0
    assert snapshot.wind_kmh == 15.0
    assert snapshot.temperature_c == 18.0
    assert snapshot.location == GeoLocation(latitude=-23.55, longitude=-46.63)


def test_chave_arredondada_para_2_casas():
    """Given location com mais casas decimais que a chave, when coleta,
    then encontra a chave por arredondamento a 2 casas."""
    provider = FixtureWeatherProvider(snapshots=_DATA)

    snapshot = provider.current(
        GeoLocation(latitude=-23.5504, longitude=-46.6333)
    )

    assert snapshot.weathercode == 65


def test_location_sem_fixture_vira_erro_de_dominio():
    """Given localização sem snapshot gravado, when coleta, then
    WeatherProviderError (não KeyError cru)."""
    provider = FixtureWeatherProvider(snapshots=_DATA)

    with pytest.raises(WeatherProviderError, match="sem fixture"):
        provider.current(GeoLocation(latitude=0.0, longitude=0.0))


def test_carrega_de_arquivo_json(tmp_path):
    """Given path de JSON gravado, when constrói provider, then replay
    funciona a partir do disco."""
    path = tmp_path / "weather_fixtures.json"
    path.write_text(json.dumps(_DATA), encoding="utf-8")

    provider = FixtureWeatherProvider(path=path)

    snapshot = provider.current(GeoLocation(latitude=-23.55, longitude=-46.63))
    assert snapshot is not None
    assert isinstance(snapshot, WeatherSnapshot)
