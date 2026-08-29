# Story Index — Intent 002-proactive-communication

> Fonte canônica por intent (mode `per-intent`).

| Story | Título | Unit | Status | Prioridade |
|---|---|---|---|---|
| `story-01-collect-open-meteo` | Coleta Open-Meteo por segurado | weather-monitoring | planned | P1 |
| `story-02-heavy-rain-residential` | Chuva intensa → residencial | risk-detection | planned | P0 |
| `story-03-hail-auto` | Granizo → automóvel | risk-detection | planned | P0 |
| `story-04-wind-coastal` | Vento forte → região costeira | risk-detection | planned | P1 |
| `story-05-template-message` | Mensagem por template paramétrico | message-generation | planned | P0 |
| `story-06-llm-optional` | LLM opcional melhora a mensagem | message-generation | planned | P1 |
| `story-07-simulated-send-report` | Envio simulado + relatório da rodada | notification-sim + pipeline-cli | planned | P0 |

Ordem de construção sugerida (TDD, núcleo primeiro):
`risk-detection` → `policy-holders` → `weather-monitoring` →
`message-generation` → `notification-sim` → `pipeline-cli`.