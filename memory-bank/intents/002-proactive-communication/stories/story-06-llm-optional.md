# Story — 06 LLM opcional melhora a mensagem

> Unit: message-generation | Priority: P1

## História

Como avaliador da banca, quero ver o LLM reescrever mensagens de forma
mais natural/quando disponível, demonstrando IA Generativa; e quero que
a demo nunca quebre sem API key.

## Given/When/Then

- **Given** env LLM configurada, **when** pipeline roda, **then**
  mensagens vêm do LlmGenerator (Pydantic AI, model-agnostic).
- **Given** env AUSENTE ou erro de LLM, **when** generando, **then**
  fallback silencioso para o template (demo segue; modo reportado no relatório).