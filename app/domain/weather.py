"""Value Objects de clima — port domain da unit weather-monitoring.

Sem regras de negócio e sem I/O: apenas a modelagem do snapshot
(espelho do payload `current_weather` do Open-Meteo) e o mapeamento
WMO weathercode → WeatherCondition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WeatherCondition(str, Enum):
    """Condição meteorológica relevante para regras de risco."""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    HAIL = "hail"
    THUNDERSTORM = "thunderstorm"


# Weathercodes WMO de granizo (thunderstorm with hail) — Open-Meteo.
HAIL_WEATHERCODES: frozenset[int] = frozenset({96, 99})

# Weathercodes WMO de chuva intensa (heavy rain / violent showers).
HEAVY_RAIN_WEATHERCODES: frozenset[int] = frozenset({65, 67, 82})

# Tabela WMO code → condição (fonte: documentação Open-Meteo).
_WMO_MAP: tuple[tuple[frozenset[int], WeatherCondition], ...] = (
    (frozenset({0}), WeatherCondition.CLEAR),
    (frozenset({1, 2, 3}), WeatherCondition.CLOUDY),
    (frozenset({45, 48}), WeatherCondition.FOG),
    (frozenset({51, 53, 55, 56, 57}), WeatherCondition.DRIZZLE),
    (frozenset({61, 63, 66, 80, 81}), WeatherCondition.RAIN),
    (frozenset({65, 67, 82}), WeatherCondition.HEAVY_RAIN),
    (frozenset({71, 73, 75, 77, 85, 86}), WeatherCondition.SNOW),
    (frozenset({95}), WeatherCondition.THUNDERSTORM),
    (frozenset({96, 99}), WeatherCondition.HAIL),
)


def classify_weathercode(code: int) -> WeatherCondition:
    """Mapeia um weathercode WMO (Open-Meteo) para WeatherCondition.

    Códigos fora da tabela caem em CLOUDY (neutro: nenhuma regra de
    risco dispara com condição neutra).
    """
    for codes, condition in _WMO_MAP:
        if code in codes:
            return condition
    return WeatherCondition.CLOUDY


@dataclass(frozen=True)
class GeoLocation:
    """Coordenadas geográficas do segurado (decimal degrees)."""

    latitude: float
    longitude: float


@dataclass(frozen=True)
class WeatherSnapshot:
    """Estado meteorológico pontual de uma GeoLocation.

    Campos espelham a API `current_weather` do Open-Meteo:
    weathercode (WMO), precipitação (mm/h), vento (km/h), temperatura (°C).
    """

    location: GeoLocation
    weathercode: int
    precipitation_mm_h: float
    wind_kmh: float
    temperature_c: float

    @property
    def condition(self) -> WeatherCondition:
        return classify_weathercode(self.weathercode)
