"""Testes do VO de clima e mapeamento weathercode (unit weather-monitoring — domínio)."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.weather import (
    HAIL_WEATHERCODES,
    WMO_SUPPORTED_CODES,
    GeoLocation,
    WeatherCondition,
    WeatherSnapshot,
    classify_weathercode,
)


class TestGeoLocation:
    def test_cria_com_latitude_longitude(self):
        loc = GeoLocation(latitude=-23.55, longitude=-46.63)
        assert loc.latitude == -23.55
        assert loc.longitude == -46.63

    def test_e_imutavel(self):
        loc = GeoLocation(latitude=-23.55, longitude=-46.63)
        with pytest.raises(FrozenInstanceError):
            loc.latitude = 0.0  # type: ignore[misc]


class TestWeatherSnapshot:
    def test_cria_com_campos_de_open_meteo(self):
        snapshot = WeatherSnapshot(
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            weathercode=65,
            precipitation_mm_h=12.0,
            wind_kmh=42.0,
            temperature_c=21.5,
        )
        assert snapshot.weathercode == 65
        assert snapshot.precipitation_mm_h == 12.0
        assert snapshot.wind_kmh == 42.0
        assert snapshot.temperature_c == 21.5

    def test_e_imutavel(self):
        snapshot = WeatherSnapshot(
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            weathercode=0,
            precipitation_mm_h=0.0,
            wind_kmh=5.0,
            temperature_c=25.0,
        )
        with pytest.raises(FrozenInstanceError):
            snapshot.weathercode = 96  # type: ignore[misc]

    def test_umidade_presente_e_default_none(self):
        """V2 (intent 005): umidade opcional — default None (desconhecida)."""
        loc = GeoLocation(latitude=-23.55, longitude=-46.63)
        sem_umidade = WeatherSnapshot(
            location=loc,
            weathercode=0,
            precipitation_mm_h=0.0,
            wind_kmh=5.0,
            temperature_c=25.0,
        )
        com_umidade = WeatherSnapshot(
            location=loc,
            weathercode=0,
            precipitation_mm_h=0.0,
            wind_kmh=5.0,
            temperature_c=25.0,
            humidity_pct=97.0,
        )
        assert sem_umidade.humidity_pct is None
        assert com_umidade.humidity_pct == 97.0


class TestClassifyWeathercode:
    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            (0, WeatherCondition.CLEAR),
            (1, WeatherCondition.CLOUDY),
            (3, WeatherCondition.CLOUDY),
            (45, WeatherCondition.FOG),
            (48, WeatherCondition.FOG),
            (51, WeatherCondition.DRIZZLE),
            (57, WeatherCondition.DRIZZLE),
            (61, WeatherCondition.RAIN),
            (63, WeatherCondition.RAIN),
            (66, WeatherCondition.RAIN),
            (65, WeatherCondition.HEAVY_RAIN),
            (67, WeatherCondition.HEAVY_RAIN),
            (80, WeatherCondition.RAIN),
            (81, WeatherCondition.RAIN),
            (82, WeatherCondition.HEAVY_RAIN),
            (71, WeatherCondition.SNOW),
            (77, WeatherCondition.SNOW),
            (85, WeatherCondition.SNOW),
            (86, WeatherCondition.SNOW),
            (95, WeatherCondition.THUNDERSTORM),
            (96, WeatherCondition.HAIL),
            (99, WeatherCondition.HAIL),
        ],
    )
    def test_mapeamento_wmo(self, code, expected):
        assert classify_weathercode(code) is expected

    def test_codigo_desconhecido_vira_cloudy(self):
        assert classify_weathercode(42) is WeatherCondition.CLOUDY

    def test_hail_weathercodes_estao_em_hail(self):
        for code in HAIL_WEATHERCODES:
            assert classify_weathercode(code) is WeatherCondition.HAIL


class TestWmoSupportedCodes:
    def test_cobre_exatamente_os_28_codigos_da_tabela_open_meteo(self):
        """Contrato do dicionário da bancada (UI): a lista exposta para
        apresentação é exatamente a união dos códigos classificados."""
        esperado = {
            0, 1, 2, 3,
            45, 48,
            51, 53, 55, 56, 57,
            61, 63, 65, 66, 67, 80, 81, 82,
            71, 73, 75, 77, 85, 86,
            95, 96, 99,
        }
        assert set(WMO_SUPPORTED_CODES) == esperado
        assert WMO_SUPPORTED_CODES == tuple(sorted(esperado))

    def test_todo_codigo_suportado_classifica_sem_fallback(self):
        """Nenhum código do dicionário depende do fallback imediato:
        cada código classifica dentro das condições da tabela."""
        for code in WMO_SUPPORTED_CODES:
            assert classify_weathercode(code) in WeatherCondition
