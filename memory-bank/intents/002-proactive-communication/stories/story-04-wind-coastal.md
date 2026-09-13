# Story — 04 Vento forte → região costeira

> Unit: risk-detection | Priority: P1

## História

Como seguradora, quero alertar segurados de regiões costeiras quando
houver ventos fortes, prevenindo danos estruturais e quedas.

## Given/When/Then

- **Given** snapshot com vento ≥ limiar (ex.: 60 km/h), **when**
  StrongWindRule avalia segurado marcado região costeira, **then** alerta gerado.
- **Given** segurado não-costeiro com mesmo vento, **when** avaliado,
  **then** nenhum alerta (regra restrita à costa).