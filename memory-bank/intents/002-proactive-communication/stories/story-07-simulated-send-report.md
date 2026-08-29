# Story — 07 Envio simulado + relatório da rodada

> Unit: notification-sim + pipeline-cli | Priority: P0

## História

Como avaliador, quero executar `python -m app run` e ver o fluxo
completo do enunciado em console, com envios claramente marcados como
simulação.

## Given/When/Then

- **Given** pipeline concluído, **when** relatório impresso, **then**
  mostra: segurados consultados → eventos detectados → alertas por regra
  → mensagens geradas (template/LLM) → "[SIMULADO]" envios por canal.
- **Given** `--offline`, **when** rodado, **then** usa fixtures gravadas
  (banca sem internet vê a mesma demo).
- **Given** dois alertas idênticos (holder, tipo), **when** enviando,
  **then** deduplicado — 1 mensagem só.