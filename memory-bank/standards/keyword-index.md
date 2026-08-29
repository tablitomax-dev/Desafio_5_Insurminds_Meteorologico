# Keyword Index (Índice Invertido)

version: 1.0.0
effective_date: 2026-08-22
owner: Master Agent (AI-DLC Option A)

---

## Descrição

Índice invertido de **palavras-chave (Linguagem Ubíqua + termos técnicos)** → referências para ADRs, Intent, Unit, Story e Bolt.

**Objetivo**: Evitar carregar todo o memory-bank para responder perguntas pontuais. Pesquisa por keyword primeiro, só abre o artefato se a keyword bater.

**Regras de atualização**:
- SEMPRE adicionar entrada quando criar novo ADR (campo `read_when` do ADR = keywords)
- SEMPRE adicionar entrada quando criar nova Story (keywords extraídas de título + tags)
- SEMPRE adicionar entrada quando concluir Bolt (keywords de domínio + técnicas usadas)
- Manter ordem alfabética por keyword, lowercase

---

## Formato de entrada (por keyword)

```
- **`<keyword>`**:
  - **ADR**: `ADR-XXX` (breve título, se houver)
  - **Intent**: `intent-slug` (link para _index.csv ou arquivo)
  - **Unit**: `unit-slug`
  - **Story**: `story-id` (título curto)
  - **Bolt**: `bolt-slug` (resumo 1 linha, se concluído)
```

Só preencher os campos que tiverem correspondência. Campos vazios são omitidos.

---

## Índice Atual

*(Preenchido automaticamente à medida que artefatos são criados.)*

---

### ADR Keywords

| Keyword | ADR Reference | Context (1 linha) |
|---------|---------------|-------------------|
| `orquestracao automatica` | [ADR-001](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/decision-index.md) | Opção A do AI-DLC: Master Agent roteia sem slash commands. |
| `opcao a` | [ADR-001](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/decision-index.md) | Idem. |
| `ai-dlc` | [ADR-001](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/decision-index.md) | Ciclo de vida: Inception → Construction → Operations. |
| `budget contexto` | ADR-002 (ver decision-index.md) | Política de 3 níveis warning. Hard cap atual: 250k tokens/sessão (ADR-003). |
| `overflow contexto` | ADR-002 | Previne alucinação por janela cheia: 80%/90%/95%. |
| `warning budget` | ADR-002 | 🟡80% inline | 🟠90% pause 3 opções | 🔴95% Hard Stop 2 rotas. |
| `grafo codigo` | ADR-002 | Graphify atualiza automático: 5 .py | 10 .md | 24h | antes Construction. |
| `graphify update` | ADR-002 | 3 triggers + .graph-last-updates.log + step -1 no analyze-context. |
| `per-intent story-index` | ADR-002 | story-index.mode=per-intent, um arquivo por intent, não single-file. |
| `keyword index` | ADR-002 | Este arquivo. Índice invertido keyword → artefatos. |
| `lru contexto` | ADR-002 | Heurística last_touched_at para só carregar artefatos recentes. |
| `integrity check` | ADR-002 | Step 0 OBRIGATÓRIO antes de abrir qualquer conteúdo de arquivo. |
| `bolt summary compact` | ADR-002 | Template ~500 tokens por bolt concluído, substitui ler ddd-01/02/03 brutos (~45k). |
| `cache hit` | ADR-004 | Cache hit é mais barato que cache miss. Prefixo estável do prompt = economia (magnitude depende do modelo). |
| `cache aware loading` | ADR-003 | OPT-13: ordem fixa de carregamento (schema → budget → ADRs → keyword → _index.csv → variável por último). |
| `opt-13` | ADR-003 | Cache-Aware Context Loading. Maior ROI de custo. |
| `thinking mode` | ADR-003 | Non-thinking em diagnóstico; thinking em construção (output é o token mais caro). |
| `non thinking` | ADR-003 | analyze-context, route-request, answer-question, explain-flow, bolt-list, bolt-status, intent-list, navigator. |
| `hard cap 250k` | ADR-003 | 25% da janela 1M. Substitui 120k do ADR-002. Cap do projeto; proporcional à janela se o modelo ativo for menor (ADR-004). |
| `model agnostic` | [ADR-004](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/decision-index.md) | Desacoplamento do modelo LLM: qualquer modelo por sessão; caps na min(caps do projeto, 25% da janela). |

---

### Domínio / Operação Keywords (intent 001)

| Keyword | Referência | Context (1 linha) |
|---------|------------|-------------------|
| `ci` | intent 001-repository-quality-foundation | Workflow CI/quality em PRs para main; bootstrap valida npm ci (`--if-present` até scripts reais). |
| `squash merge` | intent 001-repository-quality-foundation | Política: only squash na main (story-2; enforçamento na UI do GitHub). |

---

### Domínio Keywords (intent 002 — comunicação proativa)

| Keyword | Referência | Context (1 linha) |
|---------|------------|-------------------|
| `open-meteo` | ADR-005 + unit weather-monitoring | Fonte meteorológica do MVP: API aberta sem key, atrás da port `WeatherProvider`. |
| `weathercode` | unit weather-monitoring | Código numérico Open-Meteo mapeado para `WeatherCondition` (rainy/hail/windy/clear). |
| `risk rules` | unit risk-detection | Motor puro de regras: HeavyRain→residencial; Hail→auto; StrongWind→costeira. Núcleo TDD sem I/O. |
| `alerta proativo` | intent 002-proactive-communication | Capacidade do desafio I2A2: avisar segurado antes do sinistro a partir de eventos externos. |
| `llm opcional` | story-06-llm-optional | Template determinístico sempre; LLM (Pydantic AI, model agnostic) via env com fallback ao template. |
| `envio simulado` | unit notification-sim | Simulação de SMS/push no console + NotificationRecord; port isolada para provider real futuro. |

---

### Técnicas / Implementação Keywords

*(Será adicionado durante Construction/Operations)*
