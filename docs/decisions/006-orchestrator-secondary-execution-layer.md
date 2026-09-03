# ADR-006: Orquestrador secundário como camada subordinada de execução (AI-DLC tooling)

- **Status**: accepted
- **Date**: 2026-09-01
- **Supersedes**: nenhum (complementa ADR-001 e ADR-004)
- **Bolt**: N/A (decisão de Inception do pacote `tools/ai-dlc/`, aprovada pelo humano — sessão de grilling Q1–Q13)

## Contexto

Um rascunho de orquestração gerado por LLM externo ("AI-DLC v0.6.x",
fornecido como `artifacts.zip` + QUICKSTART) propunha um orquestrador
Python paralelo com spec YAML executável, adapters fixos ("GLM Flash +
Luna Pro"), setup que criaria `.trae/rules/project_rules.md` e níveis
próprios de dificuldade. Análise (grilling Q1–Q13) identificou conflitos:
duplicaria a autoridade de regras (AGENTS.md), fixaria modelos (contra
ADR-004), criaria segunda camada de orquestração (contra ADR-001) e
exigiria dependências sem checkpoint. O esboço anterior em policy-YAML
(`agent-orchestration.yaml`) já havia sido descartado pelo usuário.

## Decisão

Adotar o orquestrador como **camada subordinada de execução** do Master
Agent (ADR-001), vivendo em `tools/ai-dlc/`:

1. **Loops/gates/roteamento como código testável** (não policy YAML do
   memory-bank): `contracts.py` (Pydantic) + `ai_dlc_orchestrator.py`
   (`classify_task()` determinístico, `run_loop()` de 7 passos, gates).
2. **Níveis unificados** com `depth_levels` do context-budget: N1=TINY
   (3 iterações), N2=STANDARD (5), N3=DEEP (7). Sem esquema paralelo.
3. **Model-agnostic (ADR-004)**: perfis `code_fast/balanced/deep` + crítico
   independente, com binding por env `OPENROUTER_MODEL_FAST/BALANCED/
   DEEP/CRITIC`. Binding definitivo decidido pelo usuário (2026-09-01) e
   **validado contra a API pública do OpenRouter** (`/api/v1/models`,
   `/models/{id}/endpoints`):
   - fast: `~deepseek/deepseek-v4-flash-latest` (alias com `~` obrigatório;
     sem til → 404), effort `low`, endpoints `baidu/fp8 → deepinfra/fp8 →
     open-inference/fp8`;
   - balanced: `z-ai/glm-5.3-flash`, effort `high` (GLM aceita apenas
     `max/high/low`, reasoning `mandatory=true`; a escolha original
     `xhigh` foi rejeitada pela API), endpoints `z-ai/fp8 → novita/fp8 →
     gmicloud/fp8`;
   - deep: `z-ai/glm-5.3-flash`, effort `max`, mesmos endpoints;
   - crítico: `openai/gpt-5.6-luna-pro`, effort `max`, endpoint
     `openai/flex`.
   Roteamento: whitelist via `provider.only` (tags de endpoint confirmadas
   no campo `tag`), fallback só entre endpoints, sem fallback de modelo,
   sem `max_price`, sem seed, sem top_k/top_p, `data_collection` não
   configurado.
4. **Fase 1 = stubs tipados determinísticos** (`call_executor_llm`,
   `call_independent_critic`), sem rede e sem dependências novas.
   Fase 2 = bolt próprio com executor real via OpenRouter (deps com
   checkpoint humano), trocando o interior, não as assinaturas.
5. **Gates**: N1/N2 autônomos; N3 com **dupla confirmação humana**.
   `.trae/rules/` NÃO é criada — `.trae/project_rules.md` permanece a
   única fonte de regras.
6. **Stop rules**: success = `tests_pass AND acceptance_criteria_met AND
   critic=accept`; blocked inclui estagnação (max_iterations) e os 6
   blocker types do contrato de capacidade.
7. **Rastreabilidade**: toda decisão de loop é registrada por iteração
   (fase 1: `log_sink`; fase 2: `maintenance-log.md`).

## Alternativas consideradas

- **Policy YAML no memory-bank** (esboço v0.1.0): descartada pelo usuário —
  política sem executor é declarativa demais; código dá testes e gates reais.
- **Orquestrador paralelo autônomo** (literal do rascunho): rejeitado —
  conflita com ADR-001 e duplica autoridade de regras.
- **Integração real imediata** (OpenRouter + deps agora): rejeitada —
  checkpoints de dependência e nomes de modelo ainda não decididos.

## Consequências

- Positivas: base testável (56 testes + smoke 4/4), gates alinhados 1:1 ao
  project_rules, binding de modelos validado contra a API real (slugs,
  efforts e tags de endpoint) **e contra chamadas de chat reais**
  (smoke_binding.py: fast→DeepInfra, balanced→Novita, deep→Z.AI,
  crítico→OpenAI/flex), zero risco de segredos no repo.
- Custo/dívida: executor e crítico ainda são stubs (fase 2 troca o
  interior); loader PyYAML da spec pendente.
- Invalidação: se a fase 2 mostrar que o loop determinístico não sustenta
  executor real, novo ADR com `supersedes`.
