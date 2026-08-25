# LRU Heuristic Policy: last_touched_at + Carregamento 80/20 por Recência

version: 1.0.0
effective_date: 2026-08-22
owner: Master Agent (AI-DLC Option A)
status: optional (heurística futura, opt-in; sem impacto funcional até ser ativada por ADR)

---

## Descrição

Heurística de **Least Recently Used (LRU)** para priorizar o carregamento de artefatos do memory-bank com base em **recência de acesso**, alinhada com a regra 80/20 de Pareto:

> 80% das operações do dia a dia usam APENAS 20% dos artefatos do memory-bank.

**Objetivo**: Carregar por padrão só os artefatos recentes (20%), economizando ~60% de tokens por sessão sem perder informação útil. Artefatos antigos são carregados SÓ se:
1. Nível de profundidade = DEEP
2. Keyword de busca cair explicitamente neles
3. Usuário requisitar o artefato por nome

---

## Como funciona

### 1. Fonte de verdade: campo `last_touched_at` no `_index.csv`

Todos os `_index.csv` (intents, bolts, operations, standards) tem a coluna `last_touched_at` (ISO datetime).

**Regra de atualização do timestamp**:
- Toda vez que um artefato (intent, bolt, operação, standard) **for lido ou modificado** por qualquer skill → atualizar `last_touched_at = now()`.
- Ex: se `analyze-context` ler um _index.csv e abrir o Bolt `auth-login-bolt-3` → linha dele no bolts/_index.csv ganha `last_touched_at: 2026-08-22T14:30:00Z`.

### 2. Política de Carregamento por Nível de Profundidade

| Nível | % de artefatos a carregar por diretório | Como decidir | Default comportamento |
|-------|-----------------------------------------|--------------|-----------------------|
| **TINY** | 5% só | Top 5% recentes + ADRs obrigatórios | Não carrega nenhum bolt antigo. |
| **STANDARD** | 20% (regra 80/20) | Ordena por `last_touched_at` desc, pega 20% top. | Padrão da maioria das sessões. |
| **DEEP** | 100% | Todos os artefatos. | Só com confirmação do usuário. |

### 3. Flush LRU (remoção lógica, SEM apagar arquivo)

Quando 🔴 Hard Stop disparar e Recovery R1 rodar, além de compactar bolts:

1. Ordena todos artefatos do memory-bank por `last_touched_at` ASC (mais antigo primeiro)
2. Marca **30% dos mais antigos** como `lru_flush: true` (campo extra no CSV ou observação interna)
3. Nas próximas sessões, níveis TINY/STANDARD **ignoram esses artefatos marcados** a menos que keyword busca ou usuário explicitamente peça.
4. Flush NUNCA apaga arquivo físico. Artefato pode sempre ser "reativado" sendo acessado de novo.

---

## Ativação

- **Status atual**: *Documentado, não ativado.* Ainda não há artefatos suficientes para valer a pena.
- **Quando ativar**:
  1. Quando houver ≥ 20 bolts concluídos (volume suficiente para 80/20 valer a pena)
  2. Ou após 3 ocorrências de 🟠 warning laranja por excesso de contexto em sessões STANDARD
- **Processo de ativação**: Criar ADR-004 alterando este standard de `optional` → `required` + patch em analyze-context para aplicar a ordenação antes de carregar.

---

## Métricas Monitoradas

Para decidir se a heurística está funcionando após ativada:

| Métrica | Antes Esperado | Depois Esperado | Meta |
|---------|----------------|-----------------|------|
| Tokens carregados por sessão STANDARD | ~15k | ~6k (-60%) | ≥ 50% redução |
| Ocorrências 🟠 laranja por semana | TBD | -50% | Redução clara |
| Taxa de "false negative" (usuário precisou de artefato antigo que não carregou) | N/A | ≤ 5% | ≤ 5% |
