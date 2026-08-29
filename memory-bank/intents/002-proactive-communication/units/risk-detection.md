# Unit — risk-detection

> Intent: 002-proactive-communication | Stage: domain (NÚCLEO TDD)
> Status: `planned`

## Objetivo

Motor de regras puro (sem I/O): dado `WeatherSnapshot` + `PolicyHolder`
→ `Optional[RiskAlert(tipo, severidade, motivo)]`. Regras declarativas e
testáveis — o coração do desafio.

## Fatia técnica

- `RiskRule` (Protocol): `evaluate(snapshot, holder) -> Optional[RiskAlert]`
- Regras concretas (limiares em constantes configuráveis):
  - `HeavyRainRule`: precipitação ≥ limiar → segurados RESIDENTIAL
  - `HailRule`: weathercode de granizo → segurados AUTO
  - `StrongWindRule`: vento ≥ limiar → segurados em região costeira
- `RiskEngine`: aplica todas as regras, dedup por (holder, tipo)
- Prioridade TDD RIGOROSO: tests/domain/risk/ ANTES do código, casando
  given-when-then das stories 2–4