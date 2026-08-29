# Unit — pipeline-cli

> Intent: 002-proactive-communication | Stage: interface (orquestração)
> Status: `planned`

## Objetivo

Entrypoint `python -m app run`: orquestra as 5 etapas do enunciado e
imprime o relatório da rodada (etapa por etapa, legível para banca).

## Fatia técnica

- `app/__main__.py` + `app/cli.py` (argparse mínimo: `run`, `--offline` usa fixtures gravadas)
- Composition root manual (sem container — KISS): ports→adapters, seleção LLM por env
- Relatório de rodada: nº segurados consultados, eventos detectados,
  alertas por regra, mensagens geradas (modo template/LLM), envios simulados
- `--offline`: replay de snapshots gravados — demo sem rede (banca à prova de internet)