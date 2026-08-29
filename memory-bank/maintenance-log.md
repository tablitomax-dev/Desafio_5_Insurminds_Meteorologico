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
