# ADR-011 — Bateria preventiva por ramo (Risco × Ramo × Fase) e escopo ampliado

**Status:** aceito (2026-09-07) | **Supersedes:** [ADR-009](009-risk-engine-v2.md) | **Intents:** 008
**Fonte de negócio:** `memory-bank/standards/tabela-alertas-preventiva.md` (bateria Risco × Ramo, fases ANTES/DURANTE, aprovada pelo dono)

## Contexto

A classificação de 005 (ADR-009) ficou rígida: chuva intensa só RESIDENTIAL,
granizo só AUTO, ressaca só RESIDENTIAL. No teste real (intent 007) o dono
verificou que **chuva intensa afeta casa E/OU veículo** — e pediu a bateria
completa de alertas para todos os ramos, mais o material de decisão para a
LLM. A tabela de negócio traz ainda fases ANTES/DURANTE, severidade
INMET/Defesa Civil (amarelo/laranja/vermelho/preto) e 6 regras transversais.

## Decisão

1. **Escopo por ramo ampliado** — regras disparam para os ramos com
   exposição material na NOVA bateria:
   - `heavy_rain`: RESIDENTIAL **ou** AUTO (era só RESIDENTIAL);
   - `hail`: RESIDENTIAL **ou** AUTO (era só AUTO);
   - `strong_wind`: os dois ramos em QUALQUER região — **emenda de
     2026-09-13 (decisão do dono)**: vendavais causam dano material
     fora do litoral; supersedes o gate geográfico da story 04;
   - `rough_sea`: os dois ramos (gatilho geográfico — litoral — mantido);
   - `heat`, `heat_wave`, `extreme_cold`, `storm`: os dois ramos (inalterado);
   - `fog`: somente AUTO (inalterado — sem exposição material residencial).
2. **Regras novas** (da bateria): `low_humidity` (umidade < 30% → LOW;
   < 20% → MEDIUM; pula quando a umidade é desconhecida) e `frost`
   (temperatura ≤ 0 °C → HIGH; ≤ −2 °C → VERY_HIGH). Fumaça de queimadas
   fica no **backlog** (exige a Air Quality API do Open-Meteo).
3. **`app.domain.risk_battery`** é a fonte de verdade OPERACIONAL do
   conteúdo: células por (risco, ramo) com `impacts`, `before`, `during`;
   `INMET_LEVELS` mapeia nossa Severity (low→amarelo monitorar,
   medium→laranja prevenir, high→vermelho agir hoje,
   very_high→preto agir imediatamente); `EMERGENCY_PHONES`.
   O arquivo de negócio permanece a referência do dono.
4. **Regras transversais na mensagem** (consumidas por template e prompt):
   só células dos ramos contratados; fases pela severidade (amarelo →
   só Antes; laranja+ → Antes+Durante); telefones 199/193/192 apenas em
   laranja+; **NUNCA conteúdo pós-sinistro** (diretriz explícita no
   prompt da LLM); perfis vulneráveis como diretriz condicional.
5. **Consistência template/LLM:** prompt do LLM recebe as MESMAS células
   (impactos + recs por fase) + regras transversais; limite da story 05
   elevado de 480 para 600 chars (pedido do dono, 2026-09-08; cascata
   3→2→1 recomendação por bloco mantida).

## Consequências

- **Vento forte em qualquer região** (emenda 2026-09-13): ≥ 60 km/h
  medium, ≥ 80 km/h very_high para todo segurado com residencial/auto;
  `is_coastal` segue como sinal exclusivo da ressaca.
- Segurado **só-auto agora recebe** chuva intensa, granizo, vento e
  ressaca (mensagens exclusivas de veículo); **só-residencial recebe**
  granizo com precauções de casa.
- 2 novas regras → 2 novos RiskKind (`low_humidity`, `frost`) e rótulos
  na UI; consolidado e dedup preservados (intent 007).
- Fumaça (Air Quality API) e detecção de "evento em andamento" (fase
  Durante acionável via forecast/histórico) seguem como evoluções
  registradas no intent 008.
