# Story — 05 Mensagem por template paramétrico

> Unit: message-generation | Priority: P0

## História

Como segurado, quero receber mensagem clara e personalizada com
recomendações preventivas, para agir antes do sinistro.

## Given/When/Then

- **Given** RiskAlert de chuva para segurado maría (RESIDENTIAL), **when**
  TemplateGenerator gera, **then** mensagem tem saudação pelo nome, o
  evento, e ≥ 2 recomendações específicas (ex.: verificar drenagem, tirar
  veículo da garagem alagável).
- **Given** qualquer alerta, **when** gerada, **then** mensagem ≤ 480
  chars, sem segredos/dados sensíveis além do necessário.