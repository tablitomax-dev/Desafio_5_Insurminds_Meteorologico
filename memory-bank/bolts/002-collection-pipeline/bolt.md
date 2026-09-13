# Bolt — 002-collection-pipeline

> Intent: [002-proactive-communication](../../intents/002-proactive-communication/intent.md)
> Unit: weather-monitoring + policy-holders + pipeline-cli
> Stories: 01 (coleta Open-Meteo), 07 (envio simulado + relatório da rodada)
> Branch: `feature/002-collection-pipeline` (stacked sobre `feature/002-domain-core`)
> Status: `done` (squash merge no PR #7 → main)

## Objetivo

Fechar o ciclo de coleta do intent 002: port + adapter Open-Meteo, catálogo
de segurados com seeds JSON e pipeline de rodada executável por CLI
(`python -m app run [--offline]`) com relatório de rodada legível para banca.

## Plano (TDD)

1. **Port `WeatherProvider`** (`app/domain/ports.py`) — Protocol no domínio
   puro; erro de domínio `WeatherProviderError` (story 01: sem stack trace cru).
2. **Adapter `OpenMeteoProvider`** (`app/adapters/open_meteo.py`) — urllib da
   stdlib (zero dependências; divergência registrada no ADR-005), timeout,
   retry simples; fetch injetável para testes determinísticos.
3. **Adapter `FixtureWeatherProvider`** (`app/adapters/fixtures.py`) — replay
   de snapshots gravados em `data/weather_fixtures.json` (story 07 `--offline`).
4. **Port `PolicyHolderRepository` + `InMemoryPolicyHolderRepository`**
   (`app/adapters/catalog.py`) — carrega `data/policy_holders.json` (seeds 5–10
   segurados, mix residencial/auto/litoral/rural).
5. **Pipeline de rodada** (`app/pipeline.py`) — `run_round` (holder → snapshot
   → RiskEngine → TemplateGenerator → SimulatedSender) + `format_report` em 5
   seções; falha de coleta registra e continua com os demais (story 01).
6. **CLI** (`app/cli.py` + `app/__main__.py`) — argparse mínimo, composition
   root manual (KISS, sem container).
7. **Run real do orquestrador** (`tools/ai-dlc/run_bolt.py`) — executor +
   crítico via OpenRouter, audit em `runs.jsonl`.

## Critérios de aceite

- [ ] `python -m pytest tests -q` verde (testes novos de adapters/pipeline/CLI).
- [ ] `python -m app run --offline` imprime o relatório da rodada completo
      (5 seções, envios "[SIMULADO]", dedupe por (holder, kind)).
- [ ] Falha de rede em um segurado não derruba a rodada (registra falha, continua).
- [ ] Núcleo de domínio continua sem I/O; adapters isolam urllib.
- [ ] ruff (gate do `ruff.toml`) e mypy `app/` limpos.
- [ ] ADR-005 registrado em `docs/decisions/`.

## Fontes carregadas

- `AGENTS.md`, `.trae/project_rules.md` (protocolo).
- `memory-bank/intents/002-proactive-communication/`: story-01, story-07,
  units weather-monitoring / policy-holders / pipeline-cli / notification-sim.
- Código do bolt 002-1: `app/domain/` (weather, holders, risk, messages, notify).
- `tools/ai-dlc/run_bolt.py` (runner do bolt).

## Não lido / fora de escopo

- Stories 02–06 já cobertas pelo bolt 002-1 (ou bolt 002-3, LLM).
- ADR-001..004, 006 (apenas ADR-005 será criado neste bolt).

## Execução com o orquestrador AI-DLC (fase 2 — modo run_loop completo por bolt)

Igual ao bolt 002-1: `run_bolt.py --max-iterations 1`, com estado objetivo
real (pytest tail + git status) no prompt do executor e verify ancorado na
suíte pytest de verdade; crítico independente gateia; run auditado em
`runs.jsonl`. Resultado: **status=success** em 1 iteração (N2/code_balanced),
crítico accept, custo ≈ US$0.0029.

## Compact Summary

- **Entregue**: port `WeatherProvider` + `PolicyHolderRepository` (domínio
  puro), adapter `OpenMeteoProvider` (urllib, timeout, retry), `FixtureWeatherProvider`
  offline, `InMemoryPolicyHolderRepository` + seeds (8 segurados: urbano/auto/
  litoral/rural), `run_round` + `format_report` (5 seções), CLI `python -m app run [--offline]`.
- **Qualidade**: 84 passed (19 testes novos); ruff limpo; mypy `app/` limpo;
  run real do orquestrador com crítico accept (US$0.0029).
- **Decisões**: urllib em vez de httpx (ADR-005); fixtures versionadas em
  `data/`; console à prova de codepage (bug cp1252 encontrado no smoke).
- **Stories**: 01 e 07 → done; unit weather-monitoring → done; policy-holders → done; pipeline-cli → done.
- **Próximo**: bolt 002-3 (llm-optional — story 06, `LlmGenerator` com fallback template; checkpoint pydantic-ai vs openai).
