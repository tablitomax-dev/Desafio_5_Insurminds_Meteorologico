# Spec — 003-ai-dlc-orchestrator-tooling (fase 1)

- **Tipo**: mudança isolada de 1 PR (rastreabilidade AI-DLC: spec curta + branch + PR)
- **Branch**: `chore/003-ai-dlc-orchestrator-tooling`
- **Data**: 2026-09-01
- **Decisão**: ADR-006 (`docs/decisions/006-orchestrator-secondary-execution-layer.md`)

## Contexto

Pacote AI-DLC gerado por LLM externo (rascunho "v0.6.x") foi fornecido como
zip + QUICKSTART. Análise de grilling (Q1–Q13, respostas aprovadas pelo
usuário) concluiu: recriar daqui, adaptado aos padrões do repo, como camada
de execução **subordinada** ao Master Agent (ADR-001).

## Objetivo

Loops, gates e roteamento de orquestração como **código Python testável** em
`tools/ai-dlc/` — substituindo a abordagem policy-YAML (esboço
`agent-orchestration.yaml` descartado pelo usuário).

## Escopo (fase 1)

- Contratos Pydantic + orquestrador com `classify_task()` determinístico,
  `run_loop()` (7 passos), gates (N1/N2 autônomos, N3 dupla confirmação) e
  stop rules (`success = tests_pass E acceptance_criteria_met E critic=accept`).
- Stubs tipados `call_executor_llm()` / `call_independent_critic()` — sem rede.
- Binding de modelos por env `OPENROUTER_MODEL_FAST/BALANCED/DEEP` (ADR-004).
- Suíte TDD (39 testes), spec executável `ai-dlc-spec.yaml`, README.

## Fora de escopo (backlog fase 2 — bolt próprio)

Executor real via OpenRouter; instalar deps (`pyyaml`/`openai` — checkpoint);
loader PyYAML da spec; persistência real em `maintenance-log.md`;
`requirements-ai-dlc.txt`; dashboard Flask; cost report; Telegram ("Grill
Me"); nomes definitivos de modelos (providers/top_k/max_tokens/fallback);
`.aiignore`.

## Critérios de aceite

1. `python -m pytest tools/ai-dlc/tests -v` verde.
2. Nenhum arquivo em `.trae/rules/` (governança única em `.trae/project_rules.md`).
3. Nenhuma dependência nova instalada ou manifest criado.
4. Sem segredos no diff; sem binários (zip) commitados.
5. Limpeza total: `artifacts.zip`, `tools/ai-dlc/_reference/` e
   `AI-DLC-QUICKSTART.md` (raiz) deletados após adaptação.
6. Rastreabilidade gravada: ADR-006 + decision-index + keyword-index +
   maintenance-log + `_index.csv` (last_touched_at material).
