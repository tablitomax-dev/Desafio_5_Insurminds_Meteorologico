"""CLI do intent 002 — story 07 (`python -m app run [--offline]`).

Composition root manual (KISS, sem container): monta ports→adapters,
executa a rodada e imprime o relatório. `--offline` usa fixtures
gravadas (banca sem internet vê a mesma demo).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.adapters.catalog import (
    InMemoryPolicyHolderRepository,
    load_policy_holders,
)
from app.adapters.fixtures import FixtureWeatherProvider
from app.adapters.llm_messages import build_generator, describe_mode
from app.adapters.open_meteo import OpenMeteoProvider
from app.domain.notify import SimulatedSender
from app.domain.ports import WeatherProvider
from app.domain.risk import RiskEngine
from app.pipeline import format_report, run_round


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app",
        description=(
            "Comunicação proativa com o segurado — desafio meteorológico"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="executa uma rodada completa")
    run.add_argument(
        "--offline",
        action="store_true",
        help="usa fixtures gravadas (sem rede) — demo determinística",
    )
    run.add_argument(
        "--data",
        type=Path,
        default=Path("data"),
        help="diretório com policy_holders.json e weather_fixtures.json",
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    data_dir: Path = args.data
    repository = InMemoryPolicyHolderRepository(
        load_policy_holders(data_dir / "policy_holders.json")
    )
    provider: WeatherProvider
    if args.offline:
        provider = FixtureWeatherProvider(
            path=data_dir / "weather_fixtures.json"
        )
    else:
        provider = OpenMeteoProvider()

    # Composition root: env LLM_MODEL/LLM_PROVIDER decide story 06
    # (LLM opcional com fallback silencioso; default template).
    generator = build_generator()

    report = run_round(
        repository=repository,
        provider=provider,
        engine=RiskEngine(),
        generator=generator,
        sender=SimulatedSender(),
    )
    print(format_report(report, generator_name=describe_mode(generator)))
    return 0


def _ensure_console_tolerant() -> None:
    """Console Windows (cp1252) não crasha com •/→/emojis (usa '?').

    Mantém o encoding do terminal (acentos corretos) e apenas troca
    erros estritos por substituição — demo à prova de codepage.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    _ensure_console_tolerant()
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _run(args)
    return 2
