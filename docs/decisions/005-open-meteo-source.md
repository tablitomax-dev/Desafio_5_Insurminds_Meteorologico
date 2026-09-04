# ADR-005: Open-Meteo como fonte meteorológica do intent 002

- **Status**: accepted
- **Date**: 2026-09-03
- **Supersedes**: nenhum
- **Bolt**: 002-collection-pipeline (intent 002-proactive-communication, critério de aceite 5)

## Contexto

O intent 002 (comunicação proativa) exige coletar a condição meteorológica
atual da localização de cada segurado (story 01). A decisão de fonte estava
prevista no intent (citar Open-Meteo) mas não registrada como ADR. Restrições
relevantes: demo acadêmica à prova de internet (banca pode rodar `--offline`),
nenhuma dependência nova de produto até aqui, e o núcleo de domínio é puro
(sem I/O) por decisão do bolt 002-1.

## Decisão

1. **Fonte: Open-Meteo Forecast API** (`https://api.open-meteo.com/v1/forecast`),
   endpoint `current` com `weather_code, temperature_2m, precipitation,
   wind_speed_10m`, unidades `kmh`/`mm`, timezone UTC.
   Justificativas: **sem API key**, resposta simples, uso acadêmico sem custo.
2. **Cliente HTTP: `urllib.request` da stdlib** — a unit weather-monitoring
   sugeria httpx; optamos por stdlib para manter **zero dependências novas** no
   produto (checkpoint de dependências fica para o bolt 002-3, pydantic-ai vs
   openai). Timeout + retry simples (2 tentativas) atendem a story 01.
3. **Contrato de erro de domínio**: falhas de rede/resposta viram
   `WeatherProviderError` (definida em `app/domain/ports.py`); o pipeline
   captura por segurado e continua com os demais (story 01 à letra).
4. **Port/adapter**: `WeatherProvider` (Protocol) no domínio; adapter
   `OpenMeteoProvider` em `app/adapters/` com fetch injetável (testes sem rede).
5. **Modo offline**: `FixtureWeatherProvider` reproduz snapshots gravados em
   `data/weather_fixtures.json` (versionado) — a mesma demo da banca roda
   sem rede (`python -m app run --offline`, story 07).

## Consequências

- Adapter Open-Meteo isolado: trocar de fonte exige só um novo adapter.
- Sem httpx no `requirements` do produto; revisitar se surgir need de proxy/
  pooling/retry avançado.
- Fixtures versionadas precisam acompanhar mudanças de seeds
  (`data/policy_holders.json`) para chaves lat/lon continuarem batendo.
