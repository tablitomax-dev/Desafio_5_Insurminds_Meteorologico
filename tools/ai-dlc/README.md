# AI-DLC Tooling — Camada de Execução (fase 2, adapters reais)

Pacote recriado e adaptado do rascunho externo (v0.6.x) aos padrões
deste repositório. Governança: `AGENTS.md` → `.trae/project_rules.md`
(**única** fonte de regras; `.trae/rules/` foi intencionalmente NÃO
criada — ver ADR-006 em `docs/decisions/`).

## O que é

Orquestrador Python **subordinado** ao Master Agent (ADR-001):
roteamento por dificuldade (N1/N2/N3 = TINY/STANDARD/DEEP), loop de
7 passos, gates e contrato de capacidade. Model-agnostic via env
(ADR-004). Spec executável: [ai-dlc-spec.yaml](ai-dlc-spec.yaml)
(v0.2.0 — carregada e validada por [spec_loader.py](spec_loader.py)).

## Fase 2 (esta) — executor e crítico reais + observabilidade

- [ai_dlc_orchestrator.py](ai_dlc_orchestrator.py): `classify_task()`,
  `run_loop()`, gates, stop rules + **fns reais**
  (`call_executor_llm_real` / `call_independent_critic_real`) e
  `real_functions()` para injeção. Os stubs determinísticos permanecem
  como default do loop (determinismo dos testes); os reais são opt-in.
- [openrouter_client.py](openrouter_client.py): transporte **urllib
  stdlib** (sem SDK) — reasoning effort + `provider.only` (tags de
  endpoint); key de `OPENROUTER_API_KEY` (env) ou registro Windows
  HKCU (`setx`); **nunca impressa**. Key ausente →
  `missing_credentials_decision()` (contrato de capacidade).
- Parse JSON **tolerante** do executor/crítico (direto, bloco ```json
  ou embutido em prosa). Erros de rede viram proposal/review anotada —
  o loop nunca derruba; as stop rules decidem.
- [spec_loader.py](spec_loader.py): PyYAML; `verify_spec_consistency()`
  valida perfis/routing da spec contra o código (vazio = consistente).
- [cost_report.py](cost_report.py): `generate_cost_report()` +
  `report_markdown()` — tokens/custo por perfil a partir do `usage`.
- Auditoria: `run_loop(audit_path="runs.jsonl")` → 1 linha JSON por run
  (artefato local, não versionado).
- [dashboard.py](dashboard.py): Flask — `/` (runs), `/runs/<n>`
  (detalhe), `/cost-report`.

## Como rodar

```bash
python -m pytest tools/ai-dlc/tests -q        # suíte TDD (122 testes)
python tools/ai-dlc/ai_dlc_orchestrator.py    # demo do loop com stubs
python tools/ai-dlc/smoke_binding.py          # binding real (4 perfis)
python tools/ai-dlc/smoke_phase2.py           # loop real ponta a ponta (executor + crítico)
python tools/ai-dlc/run_bolt.py --task-id b --objective "..." --criteria "..." --risk medium --tests-cmd "..."  # run de bolt com estado real
python tools/ai-dlc/pre_merge_check.py --base origin/main  # step pre_merge_quality_repair — Fase 1 (read_only_assess, spec: spec_pre_merge_quality_repair.md)
python tools/ai-dlc/dashboard.py              # dashboard :5001
```

Loop real (executor + crítico via OpenRouter — requer key):

```python
from ai_dlc_orchestrator import TaskContext, run_loop, real_functions
ctx = TaskContext(task_id="t1", objective="...", acceptance_criteria=["..."])
fns = real_functions()                     # key lida de env/registro
result = run_loop(ctx, executor_fn=fns["executor_fn"],
                  critic_fn=fns["critic_fn"], audit_path="runs.jsonl")
print(result.status, result.iterations)
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

## Backlog fase 3 (com checkpoints de autorização)

1. Integração Telegram ("Grill Me") — adiado por decisão do usuário
   (2026-09-03).
2. `requirements-ai-dlc.txt`: declarar deps (pyyaml/flask/openai já
   instaladas no ambiente; manifest exige decisão humana).
3. CI de Python (pytest na pipeline; hoje CI é bootstrap npm).

## Referência original

O zip `artifacts.zip` fornecido pelo usuário (saída de gerador LLM
externo, não fonte de verdade) foi extraído em `tools/ai-dlc/_reference/`
e **deletado após a adaptação**, conforme combinado (limpeza total). O
`.aiignore` da referência foi adotado na fase 2 (raiz do repo).
