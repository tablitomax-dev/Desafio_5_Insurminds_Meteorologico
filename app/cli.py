"""CLI do intent 002 — story 07 (`python -m app run [--offline]`).

Composition root em `app.composition` (compartilhado com a demo visual
da intent 003): monta ports→adapters, executa a rodada e imprime o
relatório. `--offline` usa fixtures gravadas (banca sem internet vê a
mesma demo). O modo de mensagem segue o env (`LLM_MODEL`/`LLM_PROVIDER`,
story 06) — na UI Streamlit a escolha é feita por botões.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.composition import run_proactive_round
from app.pipeline import format_report


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
    report, mode = run_proactive_round(offline=args.offline, data_dir=args.data)
    print(format_report(report, generator_name=mode))
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
