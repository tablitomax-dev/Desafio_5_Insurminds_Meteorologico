# AI-DLC Tooling — Camada de Execução (fase 1, stub)

Pacote recriado e adaptado do rascunho externo (v0.6.x) aos padrões
deste repositório. Governança: `AGENTS.md` → `.trae/project_rules.md`
(**única** fonte de regras; `.trae/rules/` foi intencionalmente NÃO
criada — ver ADR-006 em `docs/decisions/`).

## O que é

Orquestrador Python **subordinado** ao Master Agent (ADR-001):
roteamento por dificuldade (N1/N2/N3 = TINY/STANDARD/DEEP), loop de
7 passos, gates e contrato de capacidade. Model-agnostic via env
(ADR-004). Spec executável: [ai-dlc-spec.yaml](ai-dlc-spec.yaml).

## Fase 1 (esta) — stub, sem rede e sem dependências novas

- [contracts.py](contracts.py): contratos Pydantic (`TaskContext`,
  `CapacityDecision`, `BlockerType`, `ModelProfile`, `ExecutorProposal`,
  `CriticReview`, `IterationRecord`, `LoopResult`)
- [ai_dlc_orchestrator.py](ai_dlc_orchestrator.py): `classify_task()`
  determinístico + `run_loop()` + gates (N1/N2 autônomos, N3 dupla
  confirmação) + stop rules (`success = tests_pass E
  acceptance_criteria_met E critic=accept`)
- `call_executor_llm()` / `call_independent_critic()`: **stubs tipados
  determinísticos** (sem OpenRouter). A fase 2 troca o interior, não a
  assinatura.

## Como rodar

```bash
python -m pytest tools/ai-dlc/tests -v      # suíte TDD (39 testes)
python tools/ai-dlc/ai_dlc_orchestrator.py  # demo do loop com stubs
```

## Binding de modelos (definitivo — validado na API do OpenRouter, 2026-09-01)

Env override (ADR-004) mantido: `OPENROUTER_MODEL_FAST/BALANCED/DEEP/CRITIC`
sobrescreve o `default_model` do perfil.

| Perfil | Modelo (default) | Effort | Temp | max_tokens | Endpoints (whitelist, cascata) |
|---|---|---|---|---|---|
| code_fast | ~deepseek/deepseek-v4-flash-latest | low | 0.2 | 4096 | baidu/fp8 → deepinfra/fp8 → open-inference/fp8 |
| code_balanced | z-ai/glm-5.3-flash | high | 0.3 | 8192 | z-ai/fp8 → novita/fp8 → gmicloud/fp8 |
| code_deep | z-ai/glm-5.3-flash | max | 0.5 | 16384 | z-ai/fp8 → novita/fp8 → gmicloud/fp8 |
| critic | openai/gpt-5.6-luna-pro | max | 0.2 | 20000 | openai/flex |

Correções impostas pela API real:
- O modelo fast exige o alias `~` (sem til: HTTP 404).
- GLM aceita apenas `max/high/low` (reasoning mandatory) — a escolha
  original `xhigh` foi ajustada para `high` no balanced.
- Tags `z-ai/fp8`, `baidu/fp8`… confirmadas no campo `tag` de `/endpoints`.

Política de roteamento: whitelist via objeto `provider` (`only`) do
OpenRouter; fallback **só entre endpoints** da lista (sem fallback de
modelo); sem `max_price`; sem seed; sem top_k/top_p;
`data_collection` não configurado.

## Smoke test real

Ferramenta permanente: [smoke_binding.py](smoke_binding.py) — 1 chamada de
chat por perfil (stdlib puro, key lida do env ou do registro Windows;
nunca impressa).

```bash
python tools/ai-dlc/smoke_binding.py
```

Resultado da validação de 2026-09-01 (key via `setx`, custo ~centavos):

```
[OK  ] code_fast: provider=DeepInfra model=deepseek/deepseek-v4-flash-0731 tokens=45
[OK  ] code_balanced: provider=Novita model=z-ai/glm-5.3-flash tokens=81
[OK  ] code_deep: provider=Z.AI model=z-ai/glm-5.3-flash tokens=82
[OK  ] critic: provider=OpenAI model=openai/gpt-5.6-luna-pro tokens=1728
4/4 perfis validados com chamada real.
```

Confirma: alias `~` do fast (resolvido para v4-flash-0731), efforts
low/high/max aceitos, tags de endpoint roteando dentro da whitelist e
`openai/flex` funcional no crítico.

## Backlog fase 2 (bolt próprio, com checkpoints de autorização)

1. Executor real via OpenRouter (deps `pyyaml`/`openai` — instalar
   somente com checkpoint humano).
2. Loader PyYAML da spec + persistência real em
   `memory-bank/maintenance-log.md` (hoje: `log_sink` em memória).
3. Crítico independente real (perfil deep).
4. `requirements-ai-dlc.txt` (criar/instalar com autorização).
5. Dashboard Flask, `generate_cost_report`, integração Telegram
   ("Grill Me").
6. Avaliar adoção do `.aiignore` da referência (config de ferramenta).

## Referência original

O zip `artifacts.zip` fornecido pelo usuário (saída de gerador LLM
externo, não fonte de verdade) foi extraído em `tools/ai-dlc/_reference/`
e **deletado após a adaptação**, conforme combinado (limpeza total).
