# Unit — weather-monitoring

> Intent: 002-proactive-communication | Stage: infrastructure/domain edge
> Status: `planned`

## Objetivo

Port + adapter para Open-Meteo: dado lat/lon (ou cidade do segurado),
retorna `WeatherSnapshot` (domínio): weathercode, precipitação (mm/h),
vento (km/h), temperatura. Nenhuma regra de negócio aqui.

## Fatia técnica

- Port `WeatherProvider` (Protocol) — domain
- Adapter `OpenMeteoProvider` (httpx, timeout, retry simples) — infrastructure
- Value Objects: `GeoLocation`, `WeatherSnapshot` — domain
- Mapeamento weathercode → `WeatherCondition` enum (rainy/hail/windy/clear...)

## Notas

Sem API key. Testes de adapter usam resposta gravada (contract fixture);
o núcleo de risco NUNCA depende de I/O.