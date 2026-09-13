# Intent 008 — risk-battery-matrix

> Status: `in_progress` (mudança isolada de 1 PR em execução) | Owner: pablo |
> Priority: P1 | Criado: 2026-09-07
>
> Contexto: o dono verificou no teste real (intent 007) que a
> classificação da 005 era rígida demais — "chuva intensa não afeta
> somente auto ou somente residencial; ela afeta um ou o outro ou
> ambos" — e produziu com uma LLM a bateria de negócio
> `memory-bank/standards/tabela-alertas-preventiva.md` (Risco × Ramo,
> fases Antes/Durante, severidade INMET, 6 regras transversais).
> Esta intent consolida a bateria no produto.

## Problema / capacidade

1. Escopo por ramo da 005 era rígido: segurado só-auto não recebia chuva
   intensa; só-residencial não recebia granizo/ressaca — apesar de
   exposição material clara nos dois ramos.
2. O conteúdo preventivo era uma tupla genérica por risco
   (`RECOMMENDATIONS_BY_KIND`), sem ramos, fases nem severidade INMET —
   pouco material para a LLM decidir tom/urgência.
3. 3 riscos da bateria não existiam no engine: baixa umidade, fumaça de
   queimadas e geada.

## Decisões (aprovadas pelo humano 2026-09-07)

| Decisão | Escolha | Registro |
|---|---|---|
| Novos riscos | Baixa umidade (< 30% LOW / < 20% MEDIUM) e geada (≤ 0 °C HIGH / ≤ −2 °C VERY_HIGH) viram regras; fumaça fica no backlog (Air Quality API) | decisão recomendada aceita |
| Escopo | Chuva e granizo passam a RESIDENTIAL **ou** AUTO; vento e ressaca no litoral atingem os 2 ramos; neblina permanece AUTO | ADR-011 (supersedes ADR-009) |
| Fases | Pela severidade (regra 4): amarelo → só Antes; laranja+ → Antes+Durante | decisão recomendada aceita |
| Telefones | 199/193/192 no template e no prompt quando ≥ laranja (regra 3) | decisão recomendada aceita |
| Limite 480 | Mantido (story 05); cascata 3→2→1 recs por bloco; bateria completa no prompt da LLM | decisão recomendada aceita |
| Fonte de verdade | `app.domain.risk_battery` (código) consumido por template + prompt; .md permanece referência de negócio | decisão recomendada aceita |
| Pós-sinistro | PROIBIDO (regra 5 do arquivo; proibição explícita no prompt) | tabela do dono |
| Vulneráveis | Diretriz condicional (regra 6) — o domínio ainda não tem dados de moradores/animais | backlog de dados |

## Escopo (1 PR)

- `app/domain/risk_battery.py` (novo): bateria estruturada
  (RISK_BATTERY, INMET_LEVELS, EMERGENCY_PHONES, BRANCH_LABELS + helpers)
- `app/domain/risk.py`: escopos (heavy_rain/hail res+auto; strong_wind e
  rough_sea nos 2 ramos), kinds `low_humidity`/`frost`, limiares,
  LowHumidityRule e FrostRule + registro no engine
- `app/domain/messages.py`: template individual e consolidado consomem a
  bateria (células por ramo contratado, fases, nível INMET, telefones);
  `RECOMMENDATIONS_BY_KIND` removida
- `app/adapters/llm_messages.py`: prompts (individual e consolidado) com
  células da bateria + regras transversais do negócio
- `ui/demo_app.py`: EVENT_LABELS dos 2 novos kinds
- Testes: escopos invertidos para o novo comportamento, regras novas,
  fases/severidade, ramo contratado, telefones, consolidação ≤480,
  prompts com bateria
- `docs/decisions/011-risk-battery-matrix.md`, README, `_index.csv`

## Fora de escopo

Fumaça/queimadas (Air Quality API); detecção de "evento em andamento"
(fase Durante acionável via forecast/histórico do Open-Meteo); dados de
perfis vulneráveis no domínio.

## Critérios de aceite

1. [x] Chuva intensa e granizo disparam para segurado apenas-auto/apenas-residencial (regras respe o novo escopo; testes de escopo atualizados)
2. [x] Novas regras `low_humidity` e `frost` com tiers testados; umidade desconhecida pula a regra
3. [x] Mensagem individual traz nível INMET, blocos Casa/Carro SOMENTE dos ramos contratados, fases pelas severidade e telefones em laranja+
4. [x] Consolidado (007) preservado: eventos ordenados por severidade, dedup, ≤600, nível global
5. [x] Prompt da LLM contém células (impactos, Antes/Durante), regras transversais 1–6 e proibição de pós-sinistro
6. [x] `ruff check .`, `mypy app` e `pytest` verdes (209 passed)
