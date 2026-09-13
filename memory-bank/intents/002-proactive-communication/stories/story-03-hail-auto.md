# Story — 03 Granizo → automóvel

> Unit: risk-detection | Priority: P0 (núcleo TDD)

## História

Como seguradora, quero alertar segurados com seguro AUTO quando o
weathercode indicar granizo, pois é o dano mais frequente em temporais.

## Given/When/Then

- **Given** snapshot com weathercode de granizo (Open-Meteo), **when**
  HailRule avalia segurado AUTO, **then** RiskAlert de granizo é gerado.
- **Given** weathercode de chuva simples, **when** avaliado segurado AUTO,
  **then** nenhum alerta de granizo.