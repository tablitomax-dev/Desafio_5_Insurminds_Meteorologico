# Story — 02 Chuva intensa → residencial

> Unit: risk-detection | Priority: P0 (núcleo TDD)

## História

Como seguradora, quero alertar segurados com seguro RESIDENCIAL quando
houver chuva intensa em sua localização, para prevenção de danos.

## Given/When/Then

- **Given** snapshot com precipitação ≥ limiar (ex.: 10 mm/h), **when**
  HeavyRainRule avalia segurado RESIDENTIAL, **then** RiskAlert de chuva é gerado.
- **Given** mesmo snapshot, **when** avaliado segurado apenas AUTO,
  **then** nenhum alerta.
- **Given** precipitação abaixo do limiar, **when** avaliado, **then** nenhum alerta.