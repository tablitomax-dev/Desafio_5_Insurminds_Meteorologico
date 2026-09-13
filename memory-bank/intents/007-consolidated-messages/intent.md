# Intent 007 — consolidated-messages

> Status: `in_progress` (mudança isolada de 1 PR em execução) | Owner: pablo |
> Priority: P1 | Criado: 2026-09-06
>
> Contexto: no teste real da intent 006, um segurado com 3 eventos
> simultâneos (granizo, onda de calor e o resumo MULTIPLE_RISKS) recebeu
> 3 mensagens separadas — o pipeline gerava mensagem/envio para CADA
> alerta emitido pelo engine. O dono pediu UMA mensagem única por
> segurado, com todos os eventos e as precauções de cada um.

## Problema / capacidade

`RiskEngine.evaluate` emite os alertas individuais + UM resumo
MULTIPLE_RISKS (decisão da intent 005 — preservada), e `run_round`
gerava mensagem + envio por alerta: N+1 envios para um segurado com N
riscos. O segurado recebe informação fragmentada e redundante (as
mensagens individuais E o resumo repetem os mesmos eventos).

## Decisões (aprovadas pelo humano 2026-09-06)

| Decisão | Escolha | Registro |
|---|---|---|
| Granularidade de envio | **1 mensagem por segurado por rodada**: 1 risco → mensagem individual (como hoje); ≥2 riscos → UMA mensagem consolidada com todos os eventos e precauções | plano aprovado pelo dono |
| Relatório | `report.alerts` continua COMPLETO (individuais + resumo) — bancada/CLI mantêm o detalhe por evento; só mensagens/envios são consolidados | plano aprovado |
| Ordem no texto | Do evento mais severo ao menos (nome curto + rótulo de severidade) | plano aprovado |
| Recomendações | Específicas de cada evento com **dedup entre eventos**; encaixa em 480 chars tentando 3→2→1 rec/evento (salvaguarda da story 05) | plano aprovado |
| Resumo MULTIPLE_RISKS | Não entra na lista de eventos do consolidado (recomendações genéricas duplicariam); define apenas o `alert_kind` da mensagem | design |
| LLM | `generate_consolidated` reescreve via LLM com prompt multi-evento; fallback silencioso para o template consolidado (mesmo padrão da story 06) | padrão do repo |

## Escopo (1 PR)

- `app/domain/messages.py`: `EVENT_NAME_BY_KIND`,
  `SEVERITY_LABEL_BY_SEVERITY`; port `MessageGenerator` ganha
  `generate_consolidated`; `TemplateGenerator` implementa
- `app/adapters/llm_messages.py`: `build_prompt_consolidated` +
  `LlmGenerator.generate_consolidated` (núcleo `_rewrite` compartilhado,
  fallback silencioso)
- `app/pipeline.py`: `run_round` gera 1 mensagem/envio por segurado
  (individual com 1 alerta; consolidada com ≥2)
- `ui/demo_app.py`: cards "Mensagens preventivas" iteram
  mensagens/envios (1:1); severidade do card via lookup
  `(holder_id, kind) → alerta`
- Testes: consolidado no template (2 e 3 eventos, ordem por severidade,
  dedup, ≤480), pipeline (3 alertas → 1 mensagem/envio), LLM (prompt com
  todos os eventos, fallback, truncamento)

## Fora de escopo

Mudar o engine (individuais + resumo permanecem — ADR-009); enviar
mensagens individuais opcionais; ADR novo (comportamento de produto, não
decisão arquitetural duradoura — registrado nesta intent).

## Critérios de aceite

1. [x] Segurado com ≥2 riscos simultâneos recebe UMA mensagem citando todos os eventos e ≥1 recomendação específica de cada (teste do template)
2. [x] `run_round` com 2 riscos no mesmo segurado: 3 alertas no relatório, 1 mensagem, 1 envio (teste do pipeline)
3. [x] Mensagem consolidada ≤ 480 chars; recomendação repetida entre eventos aparece uma única vez
4. [x] Modo LLM consolida com fallback silencioso para o template (testes do adaptador)
5. [x] `ruff check .`, `mypy app` e `pytest` verdes (194 passed)
