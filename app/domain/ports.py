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


class TelegramLinkRepository(Protocol):
    """Port: vínculo telefone ↔ chat_id do bot (intent 006).

    A API do Telegram entrega por chat_id — o repositório persiste o
    linking (nascido do /start + contato compartilhado) para que o
    envio resolva o destino consultando-o, sem campo na UI.
    """

    def get_chat_id_by_phone(self, phone_digits: str) -> str | None: ...

    def upsert_link(
        self, phone_digits: str, chat_id: str, first_name: str = ""
    ) -> None: ...
