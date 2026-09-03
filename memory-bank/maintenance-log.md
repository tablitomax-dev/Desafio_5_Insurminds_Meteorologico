# Maintenance Log (Log de Manutenção de Contexto)

version: 1.0.0
effective_date: 2026-08-22
owner: Master Agent (AI-DLC Option A)

---

## Objetivo

Registro **determinístico** de todas operações de manutenção do memory-bank:

1. **Compactação** de bolts concluídos (geração de `bolt-summary-compact.md`)
2. **Rotação** / flush LRU de artefatos marcados como "não carregar por padrão"
3. **Rebuild** de índices (`_index.csv`, `keyword-index.md`, `story-indexes/`)
4. **Atualização** do grafo graphify (registro de trigger disparado, resultado)
5. **Integrity sync** (cascade de status e correção de inconsistências)

**Quando rodar**:
- Manual, quando usuário escolhe Opção C no warning 🟠 laranja
- Automático, no recovery R1 após 🔴 Hard Stop
- A cada 10 bolts concluídos (auto-trigger)

---

## Formato de Registro

```
- **[YYYY-MM-DD HH:MM:SS] Operação: {{op_type}}**
  - **Trigger**: {{por que rodou}} | Ex: "warning 🟠 90% user option C" / "Hard Stop 🔴 R1" / "auto: 10 bolts concluídos"
  - **Artefatos tocados (N)**: {{quantos arquivos}}
  - **Economia de contexto estimada**: ~{{X}}k tokens (antes → depois)
  - **Resultado**: ✅ sucesso / ⚠️ parcial / ❌ falha
  - **Detalhes**:
    - 1. {{detalhe_1}}
    - 2. {{detalhe_2}}
```

---

## Histórico

*(A partir daqui, registro cronológico mais recente primeiro)*

---

### [2026-09-01] Operação: artifact_registration (binding definitivo validado na API OpenRouter)

- **Trigger**: decisão humana (round de binding) + comando "resolva pendências com testes reais" — validação contra `/api/v1/models` e `/endpoints`
- **Artefatos tocados (6)**: tools/ai-dlc/{contracts.py, ai_dlc_orchestrator.py, ai-dlc-spec.yaml, README.md, tests/test_binding.py, tests/test_persistence.py}, docs/decisions/006 (revisado)
- **Economia de contexto estimada**: n/a
- **Resultado**: ✅ sucesso (56 testes pytest)
- **Detalhes**:
  - 1. Binding definitivo gravado e VALIDADO: fast `~deepseek/deepseek-v4-flash-latest` (alias `~` obrigatório — sem til: 404), balanced/deep `z-ai/glm-5.3-flash` effort high/max (GLM só aceita max/high/low; `xhigh` rejeitado pela API), crítico `openai/gpt-5.6-luna-pro` effort max no endpoint `openai/flex`
  - 2. Tags de endpoint confirmadas no campo `tag` da API (`z-ai/fp8`, `openai/flex`, `baidu/fp8`…) — whitelist via `provider.only`, fallback só entre endpoints
  - 3. Persistência de auditoria real implementada (`write_maintenance_entry`, append por run, 6 testes)
  - 4. SMOKE TEST REAL 4/4 OK (key via setx, smoke_binding.py): fast→DeepInfra (alias ~→v4-flash-0731), balanced→Novita, deep→Z.AI, crítico→OpenAI/flex; efforts low/high/max aceitos; tags de endpoint roteando na whitelist

---

### [2026-09-01] Operação: artifact_registration (AI-DLC tooling — fase 1 stub)

- **Trigger**: decisão humana explícita (grilling Q1–Q13) — rascunho externo AI-DLC recriado como camada de execução subordinada; ADR-006
- **Artefatos tocados (10)**: tools/ai-dlc/{README.md, ai-dlc-spec.yaml, contracts.py, ai_dlc_orchestrator.py, conftest.py, tests/test_contracts.py, tests/test_classify.py, tests/test_loop.py, tests/test_gates.py}, docs/decisions/006-orchestrator-secondary-execution-layer.md, docs/tasks/003-ai-dlc-orchestrator-tooling.md, standards/decision-index.md, standards/keyword-index.md, standards/_index.csv
- **Economia de contexto estimada**: n/a
- **Resultado**: ✅ sucesso (39 testes pytest)
- **Detalhes**:
  - 1. ADR-006 gravado (docs/decisions/ + decision-index): loops/gates/roteamento como código; esboço `agent-orchestration.yaml` permanece descartado
  - 2. Níveis unificados com depth_levels (N1=TINY, N2=STANDARD, N3=DEEP); binding por env (ADR-004); `.trae/rules/` NÃO criada (project_rules.md única fonte)
  - 3. Limpeza combinada: `artifacts.zip`, `tools/ai-dlc/_reference/` e `AI-DLC-QUICKSTART.md` da raiz deletados após adaptação (conteúdo reescrito em tools/ai-dlc/README.md)

---

=======
>>>>>>> origin/main
### [2026-08-29] Operação: policy_update (aprovação flexível — contexto acadêmico)

- **Trigger**: decisão humana explícita — remover bloqueio de aprovação por outra pessoa; trabalho acadêmico exige fluxo mais flexível
- **Artefatos tocados (3)**: standards/git-and-collaboration.md (v1.2.0), CONTRIBUTING.md (raiz), standards/_index.csv
- **Economia de contexto estimada**: n/a
- **Resultado**: ✅ sucesso
- **Detalhes**:
  - 1. `git-and-collaboration.md` v1.2.0: aprovação deixa de ser bloqueante (recomendada); status checks e conversas resolvidas viram recomendados; PR obrigatório, squash e proibição de force push mantidos
  - 2. `CONTRIBUTING.md` (raiz): regras essenciais e fluxo (passo 10) alinhados à nova política
  - 3. `AGENTS.md` (raiz): sem alteração — proibições de agente (não mergear/aprovar) e aprovação humana para o agente agir permanecem
  - 4. Ação humana pendente no GitHub: desmarcar "Require approvals" na branch protection de `main` (e, se desejado, "require branches up to date" e "conversation resolution")

---

### [2026-08-25] Operação: policy_update (model-agnostic)

- **Trigger**: decisão humana explícita — a stack não deve estar acoplada a um modelo LLM; qualquer modelo pode ser usado por sessão
- **Artefatos tocados (5)**: standards/context-budget.yaml (v2.0.0), standards/decision-index.md (ADR-004), standards/keyword-index.md, standards/_index.csv, maintenance-log.md
- **Economia de contexto estimada**: n/a
- **Resultado**: ✅ sucesso
- **Detalhes**:
  - 1. Criado ADR-004 (model-agnostic, supersede parcial do ADR-003 — ADRs históricos preservados para rastreabilidade, não reescritos)
  - 2. `context-budget.yaml`: perfil de modelo genericizado (era `deepseek-v4-flash`); preços de provider removidos; regra `min(caps do projeto, 25% da janela do modelo ativo)`
  - 3. `keyword-index.md`: keyword `deepseek v4 flash` removida; `cache hit` genericizada; adicionada keyword `model agnostic` → ADR-004
  - 4. `standards/_index.csv`: keywords da linha `context-budget` atualizadas (`deepseek v4 flash` → `model agnostic`, references `ADR-003,ADR-004`)

---

### [2026-08-25] Operação: integrity_sync + rebuild de índice

- **Trigger**: drift disco/índice e referências fantasma detectados na coleta de contexto para revisão externa; correção autorizada explicitamente pelo usuário
- **Artefatos tocados (8)**: standards/_index.csv, standards/git-and-collaboration.md, standards/keyword-index.md, standards/context-budget.yaml, story-index.md, docs/architecture.md (novo), docs/decisions/.gitkeep (novo), docs/tasks/.gitkeep (novo)
- **Economia de contexto estimada**: n/a (sem bolts/artefatos pesados no repo)
- **Resultado**: ✅ sucesso
- **Detalhes**:
  - 1. `git-and-collaboration` adicionada ao standards/_index.csv (era órfã no disco, invisível para descoberta por índice)
  - 2. `git-and-collaboration.md` reescrito (v1.1.0) como política-only, delegando procedimento ao `.trae/CONTRIBUTING.md` e enforcement à branch protection do GitHub
  - 3. Links `file:///` de `keyword-index.md` (3× ADR-001, 1× ADR-003) e `story-index.md` (5×) corrigidos — apontavam para o projeto antigo `Desafio_5_Tempo`
  - 4. Keyword `budget contexto` atualizada: hard cap 120k → 250k (alinhada ao ADR-003)
  - 5. Criados stubs `docs/architecture.md`, `docs/decisions/`, `docs/tasks/` para satisfazer a hierarquia de leitura de `.trae/AGENTS.md` e o fluxo de `.trae/CONTRIBUTING.md` (referências deixam de ser fantasma)
