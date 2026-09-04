# execution-log — 002-collection-pipeline

## Cronologia

| # | Etapa | Resultado |
|---|---|---|
| 1 | Protocolo git (status/branch/remote/diff) | OK — branch `feature/002-collection-pipeline` criada sobre `6194cdd` (stacked, PR 002-1 aberto, aguardando squash merge) |
| 2 | Contexto: story-01, story-07, units weather-monitoring / policy-holders / pipeline-cli / notification-sim | OK |
| 3 | Artefatos: bolt.md, ADR-005, `_index.csv` | OK |
| 4 | TDD vermelho (19 testes novos: ModuleNotFoundError) → verde | OK — **84 passed** (63 domínio + 19 novos + 2 observabilidade) |
| 5 | Smoke da CLI (`python -m app run --offline`) | OK — rodada: 8 consultados, 0 falhas, 5 alertas (2 heavy_rain, 1 hail, 2 strong_wind), 5 mensagens, 5 envios; **bug de codepage cp1252 corrigido** (ver Decisões) |
| 6 | Lint: ruff (gate `ruff.toml`) + mypy `app/` | OK — ruff all checks passed (3 auto-fixes F401); mypy Success 15 files (1 fix de anotação `provider: WeatherProvider`) |
| 7 | Run real do orquestrador (`run_bolt.py`, executor + crítico OpenRouter) | OK — **status=success**, 1 iteração, N2/code_balanced, crítico **accept**, custo **US$0.0029**, audit em `tools/ai-dlc/runs.jsonl` |
| 8 | Artefatos finais (story-index, units, maintenance-log) | OK |
| 9 | Commit + push `feature/002-collection-pipeline` | OK |

## Decisões

- **urllib (stdlib) em vez de httpx** (unit sugeria httpx): zero dependências
  novas; timeout + retry simples atendem a story 01. Registrado no ADR-005.
- **Fixtures offline versionadas em `data/weather_fixtures.json`** (não só em
  `tests/fixtures/`): a demo `--offline` da banca roda sem internet e sem
  tocar em código de teste — story 07 à letra.
- **Erro de domínio `WeatherProviderError`** vive em `app/domain/ports.py`:
  story 01 exige erro tipado sem stack trace cru; pipeline captura e continua.
- **Console à prova de codepage**: o smoke real revelou `UnicodeEncodeError`
  (cp1252) no `→`/`•` do print. Correção: print do sender ASCII-safe (`->`) e
  `sys.stdout.reconfigure(errors="replace")` na CLI (acentos corretos, sem
  crash em qualquer console Windows).
- **Composition root manual em `app/cli.py`** (KISS, sem container) — unit pipeline-cli.

## Medição

- Run do orquestrador: 2 chamadas (executor code_balanced 1.113 tokens;
  crítico 9.898 tokens) — custo total ≈ **US$0.0029**; evidence `runs.jsonl`.
- Suíte: 84 passed (0.3s). ruff limpo; mypy `app/` limpo (15 files).
- Ambiente: `.venv` local (ruff 0.16.5, mypy 2.3.1, pytest 9.1.1).

## Pendências humanas

- Squash merge do PR do bolt 002-1 (`feature/002-domain-core`) — este PR é stacked.
- Abrir PR desta branch (base sugerida: `feature/002-domain-core` até o PR 1 mergeiar).
- PR da branch `chore/004-ruff-auto-fixes` (auto-fixes de lint, independente).
