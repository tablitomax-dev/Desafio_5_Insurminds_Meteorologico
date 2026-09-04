"""Adapter Open-Meteo — unit weather-monitoring (story 01).

HTTP via urllib da stdlib (ADR-005: zero dependências novas), timeout
+ retry simples. O fetch é injetável para testes determinísticos;
falhas de rede/parse viram `WeatherProviderError` (erro de domínio).
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable

from app.domain.ports import WeatherProviderError
from app.domain.weather import GeoLocation, WeatherSnapshot

API_URL = "https://api.open-meteo.com/v1/forecast"

_FETCH_TIMEOUT_S = 10.0
_DEFAULT_RETRIES = 2
_RETRY_DELAY_S = 0.2

# Callable(url, timeout_s) -> bytes (injetável para testes).
Fetcher = Callable[[str, float], bytes]


def _http_get(url: str, timeout_s: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return response.read()


class OpenMeteoProvider:
    """Port WeatherProvider contra a API pública do Open-Meteo."""

    def __init__(
        self,
        *,
        base_url: str = API_URL,
        timeout_s: float = _FETCH_TIMEOUT_S,
        max_retries: int = _DEFAULT_RETRIES,
        retry_delay_s: float = _RETRY_DELAY_S,
        fetch: Fetcher | None = None,
    ):
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._retry_delay_s = retry_delay_s
        self._fetch = fetch or _http_get

    def current(self, location: GeoLocation) -> WeatherSnapshot:
        payload = self._fetch_with_retry(location)
        return self._parse(payload, location)

    def _fetch_with_retry(self, location: GeoLocation) -> bytes:
        params = urllib.parse.urlencode(
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": (
                    "weather_code,temperature_2m,precipitation,"
                    "wind_speed_10m"
                ),
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "timezone": "UTC",
            }
        )
        url = f"{self._base_url}?{params}"

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return self._fetch(url, self._timeout_s)
            except Exception as exc:  # noqa: BLE001 — retry de rede genérico
                last_error = exc
                if attempt + 1 < self._max_retries:
                    time.sleep(self._retry_delay_s)
        raise WeatherProviderError(
            f"falha ao coletar Open-Meteo para {location}: {last_error}"
        ) from last_error

    def _parse(
        self, payload: bytes, location: GeoLocation
    ) -> WeatherSnapshot:
        try:
            data = json.loads(payload)
            current = data["current"]
            return WeatherSnapshot(
                location=location,
                weathercode=int(current["weather_code"]),
                precipitation_mm_h=float(current["precipitation"]),
                wind_kmh=float(current["wind_speed_10m"]),
                temperature_c=float(current["temperature_2m"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise WeatherProviderError(
                f"resposta inválida do Open-Meteo para {location}: {exc!r}"
            ) from exc
