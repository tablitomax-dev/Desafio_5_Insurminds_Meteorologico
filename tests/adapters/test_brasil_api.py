"""Testes do adapter BrasilAPI (CEP → coordenadas) — intent 003.

Contrato testado contra payload gravado (sem rede): URL com CEP
normalizado, parse com/sem coordenadas (degradação graciosa), CEP
inválido e não encontrado viram erro de domínio tipado.
"""

import json
from urllib.error import HTTPError, URLError

import pytest

from app.adapters.brasil_api import BrasilApiGeocoder
from app.domain.ports import GeocodingError

CEP_GONZAGA = "11065-500"

FIXTURE_COM_COORDS = json.dumps(
    {
        "cep": "11065500",
        "state": "SP",
        "city": "Santos",
        "neighborhood": "Gonzaga",
        "street": "Praça dos Expedicionários",
        "service": "open-cep",
        "location": {
            "type": "Point",
            "coordinates": {
                "longitude": "-46.33361",
                "latitude": "-23.96083",
            },
        },
    }
).encode()

FIXTURE_SEM_COORDS = json.dumps(
    {
        "cep": "11740000",
        "state": "SP",
        "city": "Itanhaém",
        "neighborhood": None,
        "service": "open-cep",
        "location": {"type": "Point"},
    }
).encode()


def test_geocode_com_coordenadas():
    """Given CEP com coordenadas na BrasilAPI, when geocode, then
    CepLocation com GeoLocation e bairro/cidade/UF parseados."""
    captured: dict[str, str] = {}

    def fake_fetch(url: str, timeout: float) -> bytes:
        captured["url"] = url
        return FIXTURE_COM_COORDS

    result = BrasilApiGeocoder(fetch=fake_fetch).geocode(CEP_GONZAGA)

    assert captured["url"] == "https://brasilapi.com.br/api/cep/v2/11065500"
    assert result.cep == "11065500"
    assert result.location is not None
    assert result.location.latitude == pytest.approx(-23.96083)
    assert result.location.longitude == pytest.approx(-46.33361)
    assert result.bairro == "Gonzaga"
    assert result.cidade == "Santos"
    assert result.uf == "SP"


def test_cep_com_hifen_e_normalizado_na_url():
    """Given CEP com hífen, when geocode, then URL usa apenas dígitos."""
    captured: dict[str, str] = {}

    BrasilApiGeocoder(
        fetch=lambda url, timeout: captured.update(url=url) or FIXTURE_COM_COORDS
    ).geocode("11065-500")

    assert captured["url"].endswith("/11065500")


def test_resposta_sem_coordenadas_degrada_para_none():
    """Given CEP municipal sem coordenadas (ex.: 11740000), when geocode,
    then CepLocation com location=None — degradação, sem exceção."""
    result = BrasilApiGeocoder(
        fetch=lambda url, timeout: FIXTURE_SEM_COORDS
    ).geocode("11740-000")

    assert result.location is None
    assert result.cidade == "Itanhaém"
    assert result.bairro == ""


def test_cep_formato_invalido_levanta_erro_sem_rede():
    """Given CEP que não casa com 00000-000, when geocode, then
    GeocodingError imediatamente (fetch nunca é chamado)."""

    def failing_fetch(url: str, timeout: float) -> bytes:
        raise AssertionError("fetch não deveria ser chamado")

    with pytest.raises(GeocodingError, match="inválido"):
        BrasilApiGeocoder(fetch=failing_fetch).geocode("123")


def test_cep_nao_encontrado_levanta_erro_de_dominio():
    """Given HTTPError 404 da BrasilAPI, when geocode, then
    GeocodingError 'não encontrado' (sem retry — 404 é definitivo)."""
    attempts: list[int] = []

    def not_found(url: str, timeout: float) -> bytes:
        attempts.append(1)
        raise HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    with pytest.raises(GeocodingError, match="não encontrado"):
        BrasilApiGeocoder(fetch=not_found).geocode("00000-000")

    assert len(attempts) == 1


def test_falha_de_rede_tem_retry_e_erro_de_dominio():
    """Given URLError do urllib, when retries esgotam, then
    GeocodingError (erro tipado, sem vazar URLError)."""
    attempts: list[int] = []

    def failing_fetch(url: str, timeout: float) -> bytes:
        attempts.append(1)
        raise URLError("connection refused")

    geocoder = BrasilApiGeocoder(
        fetch=failing_fetch, max_retries=3, retry_delay_s=0.0
    )

    with pytest.raises(GeocodingError):
        geocoder.geocode("11065-500")

    assert len(attempts) == 3


def test_resposta_invalida_vira_erro_de_dominio():
    """Given JSON sem `city`, when parse, then GeocodingError."""
    bad = json.dumps({"cep": "11065500"}).encode()

    with pytest.raises(GeocodingError, match="inválida"):
        BrasilApiGeocoder(fetch=lambda url, timeout: bad).geocode("11065-500")
