# Unit — message-generation

> Intent: 002-proactive-communication | Stage: application
> Status: `planned`

## Objetivo

`MessageGenerator` (Port) com **duas implementações**: template
paramétrico (determinística, SEMPRE disponível) e LLM (Pydantic AI,
opcional via env `LLM_PROVIDER`/`LLM_MODEL`). Mensagem =
personalizada por nome, perfil de seguro, evento e recomendações preventivas.

## Fatia técnica

- Port `MessageGenerator.generate(holder, alert) -> GeneratedMessage`
- `TemplateGenerator`: Jinja2/native f-string por (tipo de alerta × tipo de seguro)
- `LlmGenerator`: Pydantic AI agent; prompt com regras de tom (claro,
  empático, acionável, ≤ 480 chars); fallback → template se erro/sem key
- Seleção no composition root (CLI): env var decide; default template