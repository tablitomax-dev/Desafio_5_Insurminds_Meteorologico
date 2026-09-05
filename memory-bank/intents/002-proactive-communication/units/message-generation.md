# Unit — message-generation

> Intent: 002-proactive-communication | Stage: application
> Status: `done` (TemplateGenerator ✓ bolt 002-1; LlmGenerator ✓ bolt 002-3)

## Objetivo

`MessageGenerator` (Port) com **duas implementações**: template
paramétrico (determinística, SEMPRE disponível) e LLM (Pydantic AI,
opcional via env `LLM_PROVIDER`/`LLM_MODEL`). Mensagem =
personalizada por nome, perfil de seguro, evento e recomendações preventivas.

## Fatia técnica

- Port `MessageGenerator.generate(holder, alert) -> GeneratedMessage`
- `TemplateGenerator`: f-strings nativas por (tipo de alerta × tipo de seguro)
- `LlmGenerator`: Pydantic AI agent (`app/adapters/llm_messages.py`); prompt
  com regras de tom (claro, empático, acionável, ≤ 480 chars) + as MESMAS
  recomendações do template; retry curto (429/5xx); fallback silencioso →
  template; modo exercitado reportado no relatório (`mode` llm | template |
  híbrido)
- Seleção no composition root (CLI): `LLM_MODEL` (id pydantic-ai, ex.:
  `openrouter:z-ai/glm-5.3-flash`) ativa; `LLM_PROVIDER=template` força
  template; default = template
