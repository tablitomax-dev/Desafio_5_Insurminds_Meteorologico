---
last_updated: 2026-09-06T00:00:00Z
total_decisions: 9
---

# Decision Index

This index tracks all Architecture Decision Records (ADRs) created during Construction bolts.

## How to Use
- **Agentes**: Verifique este índice ANTES de implementar qualquer coisa, para seguir decisões já tomadas.
- **Humanos**: Navegue cronologicamente ou por palavras-chave.

---

## Decisions

### ADR-001: Orquestração Opção A — Master Agent automático no TRAE
- **Status**: accepted
- **Date**: 2026-08-22
- **Bolt**: N/A (decisão de inicialização do projeto)
- **Path**: `standards/decision-index.md` (esta entrada)
- **Summary**: O usuário escolheu a Opção A de orquestração. A IA sempre atuará como Master Orchestrator automático do AI-DLC no ambiente TRAE, sem exigir slash commands. Roteamento para Inception/Construction/Operations é feito internamente.
- **Read when**: Sempre que iniciar qualquer interação no projeto. Verifica o estado do memory-bank e roteia internamente.

---

### ADR-002: Política de Budget de Contexto + Atualização Automática de Grafos
- **Status**: accepted
- **Date**: 2026-08-22
- **Bolt**: N/A (decisão de otimização de contexto do memory-bank)
- **Path**: `standards/context-budget.yaml` | `standards/keyword-index.md` | `standards/lru-policy.md` | `maintenance-log.md` | `.graph-last-updates.log` | `.specsmd/aidlc/skills/master/analyze-context.md`
- **Summary**: Implementa 12 otimizações de contexto para prevenir overflow de janela LLM e alucinação. Pilares:
  1. **Budget determinístico**: proxy 4 chars ≈ 1 token + 20% margem; hard cap 120k tokens/sessão; orçamento por skill em `context-budget.yaml`.
  2. **3 Níveis de Warning**: 🟡 80% (inline) → 🟠 90% (pausa + 3 opções do usuário A/B/C) → 🔴 95% (Hard Stop + 2 rotas de recuperação R1/R2).
  3. **Níveis de profundidade**: TINY (3k) / STANDARD (15k, default 90% das sessões) / DEEP (40k, só com confirmação).
  4. **Índices canônicos**: `_index.csv` por diretório (fonte de metadados), `keyword-index.md` (índice invertido), `story-index.mode=per-intent` (1 arquivo por intent, não single-file).
  5. **Integrity check obrigatório**: step 0 no analyze-context, ANTES de abrir qualquer conteúdo de arquivo.
  6. **Bolt summary compact**: template ~500 tokens por bolt concluído, substitui leitura de ddd-01/02/03 brutos (~45k).
  7. **Atualização automática do grafo graphify**: 3 triggers determinísticos (T1: ≥5 .py OU ≥10 .md alterados; T2: ≥24h; T3: antes de rotear para Construction Agent) + `.graph-last-updates.log` + step -1 no analyze-context + flag nativa `--update` incremental.
  8. **LRU heurística** (futura, opt-in): `last_touched_at` + carregamento 80/20 por recência; ativação via ADR-004 quando houver ≥20 bolts ou 3 ocorrências de 🟠.
- **Read when**: Sempre que carregar contexto do memory-bank, rodar analyze-context, iniciar Construction Agent, ou quando o usuário perguntar sobre budget/overflow/atualização de grafo.

---

### ADR-003: Revisão de Budget para DeepSeek V4 Flash (janela 1M) + OPT-13 Cache-Aware Loading
- **Status**: accepted
- **Date**: 2026-08-22
- **Supersedes**: parcialmente ADR-002 (apenas valores de budget e estratégia de custo; demais pilares do ADR-002 permanecem)
- **Bolt**: N/A (decisão de otimização de custo/contexto)
- **Path**: `standards/context-budget.yaml` (v1.1.0) | `.specsmd/aidlc/skills/master/analyze-context.md` (step -2)
- **Summary**: Revisão baseada no modelo real usado (DeepSeek V4 Flash):
  1. **Janela real verificada**: 1M tokens (não 128k como assumido). Hard cap de sessão subiu de **120k → 250k** (25% da janela, margem para 384k output + thinking).
  2. **Correção de inconsistência**: `budget_per_skill.analyze-context` agora é **≥ depth_levels** (3k/15k/80k). Antes era 2.4k/6.4k/14.4k — menor que o conteúdo que o skill carrega (bug de design).
  3. **DEEP**: 40k → 80k (auditoria profunda com janela 1M).
  4. **OPT-13 — Cache-Aware Loading**: DeepSeek cobra $0.0028/M (cache hit) vs $0.14/M (cache miss) = **50x**. Ordem de carregamento FIXA e determinística (schema → budget → ADRs → keyword-index → _index.csv → conteúdo variável por último) para maximizar prefixo cacheado. Maior ROI de custo.
  5. **Thinking mode**: non-thinking para skills de diagnóstico (analyze-context, route-request, answer-question, explain-flow, bolt-list, bolt-status, intent-list, navigator); thinking mantido para construção (bolt-start, requirements, story-create, units, vibe-to-spec, prototype-apply, build, bolt-replan). Output é o token mais caro ($0.28/M).
- **Read when**: Sempre que rodar analyze-context, revisar budgets, configurar cliente DeepSeek, ou perguntar sobre custo/cache/thinking mode.

---

### ADR-004: Orçamento de contexto MODEL-AGNOSTIC (desacoplamento do modelo LLM)
- **Status**: accepted
- **Date**: 2026-08-25
- **Supersedes**: parcialmente ADR-003 (apenas o perfil do modelo alvo e preços DeepSeek; caps 250k/16k, profundidades, OPT-13 e política de thinking mode permanecem como estratégias gerais)
- **Bolt**: N/A (decisão de política do projeto)
- **Path**: `standards/context-budget.yaml` (v2.0.0) | `standards/keyword-index.md`
- **Summary**: O projeto NÃO fica acoplado a um modelo específico (ex.: DeepSeek V4 Flash, ADR-003). Qualquer LLM pode ser usado por sessão, a critério do usuário. O `context-budget.yaml` passa a descrever um perfil genérico: os caps (hard cap 250k, artefato único 16k) são política do projeto e, se o modelo ativo tiver janela menor que 1M, o orçamento ativo da sessão é min(caps, 25% da janela real). Diretrizes de custo ficam genéricas (cache hit < cache miss; output costuma ser o token mais caro), sem preços de provider. Menções a DeepSeek foram removidas da stack/standards ativos; o histórico permanece aqui nos ADR-002/003 para rastreabilidade.
- **Read when**: Sempre que configurar o modelo de uma sessão, revisar budgets, ou perguntar sobre seleção de LLM/custo/cache/thinking mode.

---

### ADR-005: Open-Meteo como fonte meteorológica do MVP (Ports & Adapters)
- **Status**: accepted
- **Date**: 2026-08-29
- **Bolt**: N/A (decisão rodada no Inception do intent 002, aprovada pelo humano)
- **Path**: `intents/002-proactive-communication/units/weather-monitoring.md`
- **Summary**: A fonte de dados do desafio I2A2 será **Open-Meteo** (API pública aberta, sem API key, cobertura global/BR, resposta com weathercode/precipitação/vento no endpoint forecast). Acesso isolado atrás da port `WeatherProvider` (Protocol) + adapter `OpenMeteoProvider` — trocar de fonte no futuro é barato. Alternativas consideradas: OpenWeatherMap (exige key gratuita + rate limit = atrito de demo), INMET (alertas oficiais BR, porém API menos estável para granularidade por cidade), DUAS fontes (demonstra adapter melhor, custo extra fora do MVP). Decisão dirigida por: zero atrito de credenciais na demonstração (banca/parceiro roda sem setup), documentação estável, e a exigência do enunciado é UMA fonte "devidamente documentada".
- **Read when**: Ao implementar/alterar weather-monitoring, ao avaliar trocar/adicionar fonte meteorológica, ou ao explicar a fonte na entrega.

---

### ADR-006: Orquestrador secundário como camada subordinada de execução (AI-DLC tooling)
- **Status**: accepted
- **Date**: 2026-09-01
- **Supersedes**: nenhum (complementa ADR-001 e ADR-004)
- **Bolt**: N/A (decisão de Inception do pacote `tools/ai-dlc/`, aprovada pelo humano — sessão de grilling Q1–Q13)
- **Path**: `docs/decisions/006-orchestrator-secondary-execution-layer.md` | `tools/ai-dlc/` (`ai-dlc-spec.yaml`, `ai_dlc_orchestrator.py`, `contracts.py`)
- **Summary**: O rascunho externo de orquestração ("AI-DLC v0.6.x") foi recriado e adaptado como camada de execução SUBORDINADA ao Master Agent (ADR-001): loops/gates/roteamento vivem em código Python testável em `tools/ai-dlc/`, não em policy YAML (esboço `agent-orchestration.yaml` descartado pelo usuário). Fase 1 = stubs tipados determinísticos (`call_executor_llm`/`call_independent_critic`), sem rede e sem deps novas; fase 2 = bolt próprio com executor real via OpenRouter (deps com checkpoint). Níveis unificados com depth_levels (N1=TINY, N2=STANDARD, N3=DEEP; máx. 3/5/7 iterações). Gates: N1/N2 autônomos, N3 com dupla confirmação humana; `.trae/rules/` NÃO criada (project_rules.md é a única fonte). Stop rule: success = tests_pass E acceptance_criteria_met E critic=accept. Binding definitivo (2026-09-01, validado na API pública do OpenRouter): fast `~deepseek/deepseek-v4-flash-latest` (alias `~` obrigatório) effort low; balanced/deep `z-ai/glm-5.3-flash` effort high/max (GLM só aceita max/high/low, mandatory); crítico `openai/gpt-5.6-luna-pro` effort max no endpoint `openai/flex`; whitelist de endpoints por tags (`z-ai/fp8`, `baidu/fp8`, …), fallback só entre endpoints; persistência de auditoria REAL via `write_maintenance_entry()` (append por run). Model-agnostic mantido via env `OPENROUTER_MODEL_FAST/BALANCED/DEEP/CRITIC` (ADR-004).
- **Read when**: Ao implementar/alterar `tools/ai-dlc/`, configurar binding de modelos, decidir gates/stop rules de orquestração, ou ao perguntar sobre o rascunho externo AI-DLC v0.6.x.

---

### ADR-007: BrasilAPI CEP v2 como geocoder da bancada (intent 003)
- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (ampliação da intent 003-streamlit-ui, aprovada pelo dono)
- **Path**: `docs/decisions/007-brasilapi-cep-geocoding.md` | `app/adapters/brasil_api.py` | `app/domain/ports.py` (`CepGeocoder`, `GeocodingError`) | `app/domain/weather.py` (`CepLocation`)
- **Summary**: A bancada da demo substituiu edição de lat/lon por **CEP**: BrasilAPI CEP v2 resolve bairro/cidade/UF + coordenadas em 1 chamada (sem key). Cliente stdlib urllib (ADR-005) com **User-Agent próprio obrigatório** (urllib default recebe 403). Degradacao graciosa: CEP sem coords na base ou falha de rede → coords dos seeds + aviso na UI (nunca quebra a rodada); CEP inválido/404 → `GeocodingError` imediato. Cache por sessão; seeds com CEPs reais (01016-020 … 12210-060).
- **Read when**: Ao implementar/alterar geocoding de CEP, a bancada da UI, ou ao avaliar trocar/adicionar provedor de geocoding.

---

### ADR-008: Telegram Bot API como canal real de entrega (intent 004)
- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (intent 004-telegram-delivery, aprovada pelo dono)
- **Path**: `docs/decisions/008-telegram-bot-api-delivery.md` | `app/adapters/telegram_api.py` | `app/domain/notify.py` (`NotificationRecord.detail`) | `app/composition.py` (`build_sender`)
- **Summary**: Envio real via **TelegramSender** implementando a port `NotificationSender` existente — domínio/pipeline intactos. Restrição da plataforma: entrega por `chat_id` (NUNCA por telefone) e só para conversas iniciadas; **linking** telefone → chat_id via fluxo `/start` + contato compartilhado (`getUpdates`), casando o `phone_number` com o telefone da bancada. Token em `TELEGRAM_BOT_TOKEN` (env, contrato igual ao gerador LLM) + campo secreto na UI (não persiste). Degradação graciosa: `sent`/`failed`/`skipped` com motivo em `NotificationRecord.detail` — falha NUNCA quebra a rodada; texto da story 07 preservado para o canal SMS/CLI.
- **Read when**: Ao implementar/alterar o envio (canais, linking, token, status de entrega), ou ao avaliar adicionar outro canal real (SMS/WhatsApp).

---

### ADR-009: Motor de risco V2 — limiares em tiers, regras compostas e consolidação de riscos simultâneos (intent 005)
- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (intent 005-risk-engine-v2, aprovada pelo dono)
- **Path**: `docs/decisions/009-risk-engine-v2.md` | `app/domain/risk.py` | `app/domain/weather.py` (`WeatherSnapshot.humidity_pct`) | `app/adapters/open_meteo.py` (`relative_humidity_2m`) | `app/domain/messages.py` | `analise/` (material de referência)
- **Summary**: Motor de risco V2 ADAPTADO do material `analise/risk_v2` (não copiado): regras consomem o domínio existente (`WeatherSnapshot` com weathercode WMO, `PolicyHolder` com enum `InsuranceType`/`is_coastal`); stories 02–04 preservadas como tier base e tiers superiores adicionados (chuva ≥20 HIGH / ≥35 VERY_HIGH; vento ≥80 VERY_HIGH). Novas regras ESCOPADAS POR RAMO com exposição material (classificação pessoal/residencial/auto aprovada pelo dono — só AUTO/RESIDENTIAL permanecem): calor (≥35 HIGH / ≥38 HEAT_WAVE VERY_HIGH) e frio (≤10 HIGH / ≤5 VERY_HIGH) → RESIDENTIAL ou AUTO; neblina (umidade ≥95 + vento ≤15 + chuva ≤10 — PULA sem umidade) → AUTO; tempestade (chuva+vento) → RESIDENTIAL ou AUTO; ressaca (litoral+vento≥80+chuva≥30) → RESIDENTIAL; vento forte segue a story 04 (geográfico). Umidade entra no snapshot (`humidity_pct: float | None`, Open-Meteo `relative_humidity_2m`, null → None). ≥2 riscos simultâneos → alertas individuais + resumo `MULTIPLE_RISKS` adicional (severidade máxima). Fallback por perfil estatístico FICA FORA do engine default (falso positivo em clima benigno) — material permanece em `analise/`.
- **Read when**: Ao implementar/alterar regras de risco, limiares, severidades, escopo por ramo de seguro, consolidação de alertas, ou o campo de umidade do snapshot.
