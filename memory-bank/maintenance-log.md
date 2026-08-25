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

### Nenhuma operação de manutenção executada ainda.

Primeira operação será registrada aqui quando disparar trigger.
