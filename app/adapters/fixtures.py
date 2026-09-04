"""Adapter de fixtures offline — story 07 (`--offline`).

Replay de snapshots gravados em JSON (padrão: `data/weather_fixtures.json`,
versionado) — a demo da banca roda sem internet e sem tocar em código de
teste. Chaves: `"<lat>|<lon>"` arredondadas a 2 casas decimais.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.ports import WeatherProviderError
from app.domain.weather import GeoLocation, WeatherSnapshot

DEFAULT_FIXTURES_PATH = Path("data") / "weather_fixtures.json"


def _key(location: GeoLocation) -> str:
    return f"{round(location.latitude, 2)}|{round(location.longitude, 2)}"


class FixtureWeatherProvider:
    """Port WeatherProvider com snapshots gravados (determinístico)."""

    def __init__(
        self,
        snapshots: dict[str, dict[str, float]] | None = None,
        *,
        path: str | Path | None = None,
    ):
        if snapshots is None:
            target = Path(path) if path is not None else DEFAULT_FIXTURES_PATH
            snapshots = json.loads(target.read_text(encoding="utf-8"))
        self._snapshots = snapshots

    def current(self, location: GeoLocation) -> WeatherSnapshot:
        record = self._snapshots.get(_key(location))
        if record is None:
            raise WeatherProviderError(
                f"localização {location} sem fixture gravada "
                f"(chave {_key(location)})"
            )
        return WeatherSnapshot(
            location=location,
            weathercode=int(record["weathercode"]),
            precipitation_mm_h=float(record["precipitation_mm_h"]),
            wind_kmh=float(record["wind_kmh"]),
            temperature_c=float(record["temperature_c"]),
        )
