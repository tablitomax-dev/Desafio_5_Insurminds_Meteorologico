"""Ports de saída do domínio — weather-monitoring e policy-holders.

Domínio puro: apenas interfaces (typing.Protocol) e os erros de domínio
tipados (story 01 e intent 003). Implementações (adapters) vivem em
`app/adapters/`.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.holders import PolicyHolder
from app.domain.weather import CepLocation, GeoLocation, WeatherSnapshot


class WeatherProviderError(RuntimeError):
    """Erro de domínio para falha de coleta meteorológica (story 01).

    Adapters convertem exceções de rede/parse nesta exceção — o
    pipeline NUNCA vê stack trace cru de urllib/JSON.
    """


class GeocodingError(RuntimeError):
    """Erro de domínio para falha de geocoding de CEP (intent 003).

    Adapters convertem CEP inválido/não encontrado/falha de rede nesta
    exceção — a UI decide a degradação (nunca vê urllib cru).
    """


class WeatherProvider(Protocol):
    """Port: GeoLocation → WeatherSnapshot atual."""

    def current(self, location: GeoLocation) -> WeatherSnapshot: ...


class CepGeocoder(Protocol):
    """Port: CEP → CepLocation (coords opcionais — intent 003)."""

    def geocode(self, cep: str) -> CepLocation: ...


class PolicyHolderRepository(Protocol):
    """Port: catálogo de segurados consultável pelo pipeline."""

    def list_all(self) -> list[PolicyHolder]: ...
