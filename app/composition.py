"""Composition root compartilhado — intent 003 (CLI e UI Streamlit).

Monta o grafo ports→adapters de uma rodada e o executa. A CLI
(`app.cli`) e a demo visual (`ui/demo_app.py`) chamam o MESMO ponto: a
fonte meteorológica (offline fixtures / Open-Meteo) e o modo de mensagem
(template / LLM) são escolhas explícitas; quando omitidas, vale o
contrato de env da story 06 (`LLM_MODEL`/`LLM_PROVIDER`).

A bancada da UI (intent 003) também pode injetar `holders` editados
(nome/telefone/coordenadas/perfil) e `weather_snapshots` simulados —
o alerta continua sendo gerado pelas MESMAS regras do domínio
analisando o tempo informado; nada de regra nova aqui. O CANAL de
envio também é escolha explícita (intent 004): `SimulatedSender` (SMS
fake) ou `TelegramSender` real (Telegram Bot API) via `build_sender` —
com degradação graciosa, a falha de entrega nunca quebra a rodada.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.adapters.catalog import (
    InMemoryPolicyHolderRepository,
    load_policy_holders,
)
from app.adapters.fixtures import FixtureWeatherProvider
from app.adapters.llm_messages import build_generator, describe_mode
from app.adapters.open_meteo import OpenMeteoProvider
from app.adapters.telegram_api import TelegramSender
from app.domain.holders import PolicyHolder
from app.domain.notify import NotificationSender, SimulatedSender
from app.domain.ports import WeatherProvider
from app.domain.risk import RiskEngine
from app.pipeline import RoundReport, run_round

DEFAULT_DATA_DIR: Path = Path("data")

# Canais de envio da rodada (intent 004).
DELIVERY_SIMULATED = "simulated"
DELIVERY_TELEGRAM = "telegram"


def build_weather_provider(
    *,
    offline: bool,
    data_dir: Path,
    weather_snapshots: dict[str, dict[str, float]] | None = None,
) -> WeatherProvider:
    """Fonte da rodada: fixtures versionadas (offline) ou Open-Meteo real.

    No offline, `weather_snapshots` (bancada da UI) substitui o arquivo
    de fixtures — mesmo formato, chaves `"<lat>|<lon>"` a 2 casas.
    """
    if offline:
        if weather_snapshots is not None:
            return FixtureWeatherProvider(snapshots=weather_snapshots)
        return FixtureWeatherProvider(path=data_dir / "weather_fixtures.json")
    return OpenMeteoProvider()


def build_sender(
    *,
    delivery: str = DELIVERY_SIMULATED,
    telegram_token: str | None = None,
) -> NotificationSender:
    """Canal de envio da rodada — intent 004.

    "simulated": SimulatedSender (SMS fake — comportamento original).
    "telegram": TelegramSender real (Telegram Bot API). O token vem do
    parâmetro explícito (campo secreto da UI) ou, em último caso, de
    TELEGRAM_BOT_TOKEN (mesmo contrato do gerador LLM). Sem token ou
    chat_id o envio vira "skipped" — degradação, nunca quebra a rodada
    (ADR-008).
    """
    if delivery == DELIVERY_TELEGRAM:
        token = (
            telegram_token
            if telegram_token is not None
            else os.environ.get("TELEGRAM_BOT_TOKEN", "")
        )
        return TelegramSender(token)
    return SimulatedSender()


def run_proactive_round(
    *,
    offline: bool,
    data_dir: Path = DEFAULT_DATA_DIR,
    llm_model: str | None = None,
    llm_provider: str | None = None,
    holders: list[PolicyHolder] | None = None,
    weather_snapshots: dict[str, dict[str, float]] | None = None,
    delivery: str = DELIVERY_SIMULATED,
    telegram_token: str | None = None,
) -> tuple[RoundReport, str]:
    """Executa a rodada completa; retorna (relatório, modo exercitado).

    `llm_model`/`llm_provider` explícitos (botões da UI) vencem; `None`
    cai no env — contrato da story 06 preservado para a CLI. `holders`
    e `weather_snapshots` injetados (bancada da UI) vencem os seeds.
    `delivery` escolhe o canal de envio (simulated/telegram — intent
    004); `telegram_token` explícito vence o env TELEGRAM_BOT_TOKEN.
    """
    repository = InMemoryPolicyHolderRepository(
        holders
        if holders is not None
        else load_policy_holders(data_dir / "policy_holders.json")
    )
    generator = build_generator(model=llm_model, provider=llm_provider)
    report = run_round(
        repository=repository,
        provider=build_weather_provider(
            offline=offline,
            data_dir=data_dir,
            weather_snapshots=weather_snapshots,
        ),
        engine=RiskEngine(),
        generator=generator,
        sender=build_sender(delivery=delivery, telegram_token=telegram_token),
    )
    return report, describe_mode(generator)
