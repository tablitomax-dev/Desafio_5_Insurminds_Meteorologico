"""Ports de saída do domínio — weather-monitoring e policy-holders.

Domínio puro: apenas interfaces (typing.Protocol) e o erro de domínio
tipado da story 01. Implementações (adapters) vivem em `app/adapters/`.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.holders import PolicyHolder
from app.domain.weather import GeoLocation, WeatherSnapshot


class WeatherProviderError(RuntimeError):
    """Erro de domínio para falha de coleta meteorológica (story 01).

    Adapters convertem exceções de rede/parse nesta exceção — o
    pipeline NUNCA vê stack trace cru de urllib/JSON.
    """


class WeatherProvider(Protocol):
    """Port: GeoLocation → WeatherSnapshot atual."""

    def current(self, location: GeoLocation) -> WeatherSnapshot: ...


class PolicyHolderRepository(Protocol):
    """Port: catálogo de segurados consultável pelo pipeline."""

    def list_all(self) -> list[PolicyHolder]: ...
