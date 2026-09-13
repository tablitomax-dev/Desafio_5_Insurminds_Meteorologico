# Story — 01 Coleta Open-Meteo por segurado

> Unit: weather-monitoring | Priority: P1

## História

Como sistema, quero coletar a condição meteorológica atual da localização
de cada segurado via Open-Meteo, para alimentar a detecção de risco.

## Given/When/Then

- **Given** um segurado com GeoLocation válida, **when** o pipeline coleta,
  **then** obtém WeatherSnapshot com weathercode/precipitação/vento/temperatura.
- **Given** falha de rede/timeout, **when** o adapter executa,
  **then** erro domínio tipado (sem stack trace cru) e pipeline continua com os demais.