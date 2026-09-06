# ADR-009: Motor de risco V2 — limiares em tiers, regras compostas e consolidação de riscos simultâneos

- **Status**: accepted
- **Date**: 2026-09-06
- **Bolt**: N/A (intent 005-risk-engine-v2, aprovada pelo dono via AskUserQuestion + análise crítica de `analise/`)
- **Path**: `docs/decisions/009-risk-engine-v2.md` | `app/domain/risk.py` | `app/domain/weather.py` (`WeatherSnapshot.humidity_pct`) | `app/adapters/open_meteo.py` (`relative_humidity_2m`) | `app/domain/messages.py` | `memory-bank/intents/005-risk-engine-v2/`

## Contexto

O motor de risco do desafio (stories 02–04) detecta 3 eventos com
severidade fixa. A análise estatística da planilha
`50_situacoes_meteorologicas_simuladas` (material em `analise/`,
risk_v2) propôs ampliar para calor/frio/neblina/tempestade/ressaca, com
gradientes de severidade e consolidação de riscos simultâneos. O código
do risk_v2 NÃO era drop-in: duplicava o domínio (`WeatherInput`,
`PolicyHolder` próprios), usava strings para ramo de seguro, subia o
limiar da story 02 (10 → 20 mm/h), removia a restrição costeira da
story 04 e classificava SEMPRE por perfil estatístico (alerta mesmo em
clima benigno).

## Decisão (4 pontos)

1. **Adaptar, não copiar**: as regras consomem o domínio existente —
   `WeatherSnapshot` (granizo por weathercode WMO 96/99, não por
   string) e `PolicyHolder` (enum `InsuranceType` com múltiplos ramos,
   `is_coastal`). Os limiares das stories 02–04 são preservados como
   tier base; o v2 adiciona tiers superiores (chuva ≥20 HIGH / ≥35
   VERY_HIGH; vento ≥80 VERY_HIGH).
2. **Novas regras escopadas por ramo** (classificação por nível pessoal/
   residencial/auto aprovada pelo dono em 2026-09-06 — somente riscos
   com exposição material a AUTO/RESIDENTIAL são mantidos):
   `HeatRule` (≥35 HIGH; ≥38 vira HEAT_WAVE VERY_HIGH) e
   `ExtremeColdRule` (≤10 HIGH; ≤5 VERY_HIGH) → RESIDENTIAL ou AUTO;
   `FogRule` (umidade ≥95 + vento ≤15 + chuva ≤10; ≥98 → HIGH) → AUTO;
   `StormRule` (chuva ≥30 + vento ≥60; ≥35 + ≥80 → VERY_HIGH) →
   RESIDENTIAL ou AUTO; `RoughSeaRule` (litoral + vento ≥80 + chuva
   ≥30 → VERY_HIGH) → RESIDENTIAL. O viés pessoal/saúde (desidratação,
   hipotermia) fica FORA do escopo do desafio — os riscos permanecem
   apenas onde há dano material segurável.
3. **Umidade entra no snapshot**: `WeatherSnapshot.humidity_pct: float |
   None` (default `None` = desconhecida); Open-Meteo passa a pedir
   `relative_humidity_2m` (null → `None`, degradação graciosa sem
   quebrar o parse). `FogRule` PULA quando a umidade é desconhecida.
   Fixtures offline ganham umidade (Curitiba 97% → neblina na demo).
4. **Consolidação SEM perda**: ≥2 riscos simultâneos geram os alertas
   individuais (1 mensagem por risco, granularidade preservada) + UM
   resumo `MULTIPLE_RISKS` adicional por último (severidade = máxima).
   O fallback por perfil estatístico (distância euclidiana normalizada
   nos perfis da planilha) fica FORA do engine default — permanece em
   `analise/` como material de referência/estudo.

## Consequências

- Suite atual segue verde com ajustes deliberados mínimos (o teste do
  engine passa a esperar `MULTIPLE_RISKS` no cenário de 3 riscos).
- `messages.py` precisa de entrada para TODO kind (o teste de 480 chars
  itera `RiskKind` inteiro) — novos kinds com ≥2 recomendações cada.
- `Severity.VERY_HIGH` propaga por relatório/UI/LLM (labels e cores
  adicionados; `SEVERITY_COLOR` tem fallback gray).
- Novos limiares ficam em constantes configuráveis no módulo (mesmo
  estilo das stories); trocar de fonte de umidade é barato (port
  `WeatherProvider` intacta).

## Alternativas consideradas

- **Copiar risk_v2 direto**: rejeitado — quebrava stories 02/04
  (limiares e escopo), duplicava o domínio e gerava falso positivo em
  clima benigno (fallback estatístico incondicional).
- **Consolidação substituindo individuais** (comportamento do risk_v2):
  rejeitada — perde a mensagem específica por tipo de seguro; escolhida
  a consolidação aditiva (individual + resumo).
- **Não coletar umidade / pular neblina**: rejeitada — neblina é
  relevante para AUTO e o custo é pequeno (1 campo opcional no
  snapshot).
