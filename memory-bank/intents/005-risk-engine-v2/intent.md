# Intent 005 — risk-engine-v2

> Status: `in_progress` (mudança isolada de 1 PR em execução) | Owner: pablo |
> Priority: P1 | Criado: 2026-09-06
>
> Contexto: a intent 004 entregou o envio real via Telegram (merge #14).
> Este intent evolui o motor de risco (`app/domain/risk.py`) com o
> material de `analise/` (risk_v2 + Mudancas_Risc_v2): mais tipos de
> risco, escalonamento de severidade e consolidação de riscos
> simultâneos — preservando as stories 02–04 do desafio.

## Problema / capacidade

O motor atual detecta 3 riscos (chuva, granizo, vento) com severidade
fixa. A análise estatística da planilha
(50_situacoes_meteorologicas_simuladas) mostra situações relevantes não
cobertas (calor, frio, neblina, tempestade, ressaca) e gradientes de
severidade (chuva 20 vs 35 mm/h têm impactos distintos para o segurado).
Uma mesma situação pode combinar ameaças simultâneas — o segurado
deveria receber UM aviso consolidado além dos individuais.

## Decisões (aprovadas pelo humano 2026-09-06)

| Decisão | Escolha | Registro |
|---|---|---|
| Sequenciamento | Fechar a 004 primeiro (merge #14) e abrir branch nova `feature/005-risk-engine-v2` | AskUserQuestion |
| Umidade | **Estender snapshot + Open-Meteo**: `WeatherSnapshot.humidity_pct` (default `None`), `relative_humidity_2m` no adapter; FogRule pula quando umidade desconhecida (degradação graciosa) | AskUserQuestion |
| Consolidação | **Alertas individuais + resumo adicional**: ≥2 riscos → alerta `MULTIPLE_RISKS` (severidade = máxima) acrescido DEPOIS dos individuais | AskUserQuestion |
| Adaptar, não copiar | Regras consomem `WeatherSnapshot`/`PolicyHolder` do domínio (enum `InsuranceType`, `is_coastal`, weathercode WMO para granizo); modelos duplicados do risk_v2 descartados | análise crítica |
| Fallback estatístico | Perfis de distância da planilha FICAM FORA do engine default (falso positivo em clima benigno); material permanece em `analise/` como referência | análise crítica |
| Escalonamento | Preserva stories: chuva 10 mm/h→MEDIUM, granizo HIGH, vento restrito ao litoral; v2 acrescenta tiers (20/35 chuva, 80 vento) | análise crítica |

## Escopo (1 PR)

- `app/domain/risk.py`: `Severity.VERY_HIGH`; 7 novos `RiskKind`
  (HEAT, HEAT_WAVE, EXTREME_COLD, STORM, ROUGH_SEA, FOG,
  MULTIPLE_RISKS); novas regras `HeatRule`/`ExtremeColdRule`/`FogRule`/
  `StormRule`/`RoughSeaRule`; escalonamento em tiers em
  `HeavyRainRule`/`StrongWindRule`; `RiskEngine` consolida ≥2 alertas em
  resumo adicional; limiares em constantes
- `app/domain/weather.py`: `WeatherSnapshot.humidity_pct: float | None`
  (default `None` = desconhecida)
- `app/adapters/open_meteo.py`: coleta `relative_humidity_2m` (null →
  `None`, sem quebrar o parse)
- `app/adapters/fixtures.py` + `data/weather_fixtures.json`: replay com
  umidade (Curitiba com 97% → neblina na demo offline)
- `app/domain/messages.py`: `EVENT_BY_KIND` +
  `RECOMMENDATIONS_BY_KIND` para os novos kinds (≥2 recomendações cada —
  story 05; o loop de 480 chars do test_messages exige entrada para todo
  kind)
- `ui/demo_app.py`: `EVENT_LABELS` + `SEVERITY_COLOR` para os novos
  kinds e `very_high`
- Testes TDD: novos rules (heat/cold/fog/storm/rough_sea + tiers),
  consolidação no engine, umidade no snapshot/adapter/fixtures,
  mensagens dos novos kinds

## Fora de escopo

Classificação por perfil estatístico (distância euclidiana normalizada)
no engine default; previsão de várias horas (usa `current`); UI de
configuração de limiares; mudança nos textos/limiares das stories 02–04.

## Critérios de aceite

1. [ ] Stories 02–04 preservadas: chuva 10 mm/h → RESIDENTIAL MEDIUM; granizo weathercode → AUTO HIGH; vento 60 km/h → litoral MEDIUM (suite atual segue verde com ajustes deliberados mínimos)
2. [ ] Escalonamento: chuva ≥20 HIGH / ≥35 VERY_HIGH; vento ≥80 VERY_HIGH; calor ≥35 HIGH / ≥38 onda de calor VERY_HIGH; frio ≤10 HIGH / ≤5 VERY_HIGH
3. [ ] Regras compostas: tempestade (chuva+vento) e ressaca (litoral+vento≥80+chuva≥30) disparando; neblina exige umidade e PULA quando desconhecida
4. [ ] Escopo por ramo validado: calor/onda, frio e tempestade só para RESIDENTIAL/AUTO; neblina só AUTO; ressaca só RESIDENTIAL (litoral); segurado sem ramo com exposição não recebe esses alertas
5. [ ] ≥2 riscos simultâneos → alertas individuais + resumo MULTIPLE_RISKS (severidade máxima) por último; 1 risco → sem resumo
6. [ ] Snapshot carrega umidade do Open-Meteo (null → None sem erro); fixture offline com umidade; mensagem ≤ 480 chars para TODO kind; `ruff`/`mypy app`/`pytest` verdes
