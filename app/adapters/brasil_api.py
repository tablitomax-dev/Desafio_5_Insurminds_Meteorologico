"""Adapter BrasilAPI CEP v2 — geocoding CEP → coordenadas (intent 003).

`https://brasilapi.com.br/api/cep/v2/{cep}` retorna bairro/cidade/UF e —
quando a base (OpenStreetMap/open-cep) tem — as coordenadas do CEP.
HTTP via urllib da stdlib (mesmo padrão do ADR-005: zero dependências),
timeout + retry simples, fetch injetável para testes determinísticos.

Degradacao graciosa (decisão do dono, 2026-09-06):
- CEP sem coordenadas na base → `CepLocation(location=None)`, SEM exceção
  (a UI decide: usa coords dos seeds e avisa);
- CEP inválido (formato) ou não encontrado (404) → `GeocodingError`
  imediato, sem retry (erro definitivo);
- Falha de rede → retry e, esgotado, `GeocodingError` (domínio).
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from app.domain.ports import GeocodingError
from app.domain.weather import CepLocation, GeoLocation

API_URL = "https://brasilapi.com.br/api/cep/v2"

# A BrasilAPI bloqueia o User-Agent default do urllib (403) — identificar
# a aplicação é boa prática de client HTTP.
_USER_AGENT = "insurminds-meteorologico-demo/1.0 (desafio I2A2)"

_CEP_RE = re.compile(r"^\d{5}-?\d{3}$")

_FETCH_TIMEOUT_S = 10.0
_DEFAULT_RETRIES = 2
_RETRY_DELAY_S = 0.2

# Callable(url, timeout_s) -> bytes (injetável para testes).
Fetcher = Callable[[str, float], bytes]


def _http_get(url: str, timeout_s: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return response.read()


class BrasilApiGeocoder:
    """Port CepGeocoder contra a BrasilAPI CEP v2."""

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

    def geocode(self, cep: str) -> CepLocation:
        """Resolve CEP → CepLocation (coords opcionais)."""
        cep_normalizado = self._normalize(cep)
        payload = self._fetch_with_retry(cep_normalizado)
        return self._parse(payload, cep_normalizado)

    @staticmethod
    def _normalize(cep: str) -> str:
        digits = "".join(ch for ch in cep if ch.isdigit())
        if not _CEP_RE.fullmatch(digits):
            raise GeocodingError(
                f"CEP inválido: {cep!r} (formato esperado 00000-000)"
            )
        return digits

    def _fetch_with_retry(self, cep: str) -> bytes:
        url = f"{self._base_url}/{cep}"

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return self._fetch(url, self._timeout_s)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:  # erro definitivo: sem retry
                    raise GeocodingError(
                        f"CEP não encontrado na BrasilAPI: {cep}"
                    ) from exc
                last_error = exc
            except Exception as exc:  # noqa: BLE001 — retry de rede genérico
                last_error = exc
            if attempt + 1 < self._max_retries:
                time.sleep(self._retry_delay_s)
        raise GeocodingError(
            f"falha ao consultar BrasilAPI para o CEP {cep}: {last_error}"
        ) from last_error

    def _parse(self, payload: bytes, cep: str) -> CepLocation:
        try:
            data = json.loads(payload)
            bairro = str(data.get("neighborhood") or "")
            cidade = str(data["city"])
            uf = str(data["state"])
            coords = (data.get("location") or {}).get("coordinates")
            location = (
                GeoLocation(
                    latitude=float(coords["latitude"]),
                    longitude=float(coords["longitude"]),
                )
                if coords
                else None
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise GeocodingError(
                f"resposta inválida da BrasilAPI para o CEP {cep}: {exc!r}"
            ) from exc
        return CepLocation(
            cep=cep, location=location, bairro=bairro, cidade=cidade, uf=uf
        )
