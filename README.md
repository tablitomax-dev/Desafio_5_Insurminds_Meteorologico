# Desafio 5 I2A2 — Ferramenta Inteligente para Comunicação Proativa com o Segurado

> Monitoramento meteorológico público → detecção de risco por perfil de seguro →
> mensagem preventiva personalizada (template ou LLM) → envio real via Telegram
> (vínculo telefone → chat persistido em SQLite) + relatório.

## O problema

A comunicação seguradora ↔ segurado é historicamente **reativa**: o contato acontece
depois do sinistro. Este projeto inverte a lógica — usa a **API pública Open-Meteo**
para antecipar eventos meteorológicos e avisar o segurado **antes do sinistro**,
demonstrando o valor de agentes inteligentes no relacionamento com o segurado.

## Como rodar a demo

Requisitos: Python 3.12+ (sem instalar nada para o modo template).

```bash
# 1) Demo determinística offline (banca sem internet — fixtures versionadas)
python -m app run --offline

# 2) Demo online (Open-Meteo real, sem API key)
python -m app run

# 3) Demo com LLM reescrevendo as mensagens (Pydantic AI, model-agnostic)
export OPENROUTER_API_KEY=sua-chave          # Windows PowerShell: $env:OPENROUTER_API_KEY='...'
export LLM_MODEL=openrouter:z-ai/glm-5.3-flash  # identificador pydantic-ai
python -m app run --offline

# Forçar o modo template mesmo com LLM_MODEL setada:
export LLM_PROVIDER=template
```

O relatório de rodada no console mostra as 5 etapas: segurados consultados,
eventos detectados, alertas por regra, mensagens geradas (com o **modo**:
`template`, `llm` ou fallback/híbrido) e envios simulados.

**Garantia de robustez**: sem chave, sem rede ou com a LLM instável, a demo
**nunca quebra** — o `LlmGenerator` tem fallback silencioso para o
`TemplateGenerator` (com retry para erros transitórios de API), e o modo
exercitado é sempre reportado.

## Demo visual (Streamlit)

A mesma rodada da CLI em interface interativa (reusa o **mesmo composition
root**, `app/composition.py`):

```bash
.venv\Scripts\pip install -r requirements-ui.txt   # só a demo visual (fora do CI)
.venv\Scripts\streamlit run ui/demo_app.py
```

Na barra lateral: fonte meteorológica (Open-Meteo real por default ou
fixtures offline determinísticas) e modo de mensagem (LLM com fallback
por default, ou template determinístico). A **bancada de simulação**
permite editar os dados fictícios — nome, telefone, **CEP** (resolve
bairro/cidade e coordenadas via BrasilAPI, com degradação graciosa),
perfil de seguros, litoral e, no offline, o tempo simulado (o alerta é
gerado automaticamente pelas regras analisando o tempo informado). A tela
mostra KPIs da rodada, a tabela de **segurados monitorados** (bairro/
cidade — bairros reais validados via OpenStreetMap/Nominatim —,
coordenadas a 4 casas, tempo atual e alerta gerado), alertas por regra,
as mensagens preventivas com o **modo exercitado** sempre reportado
(template, llm ou fallback) e o relatório textual idêntico ao da CLI
num expander. Nenhuma regra de negócio na UI.

### Envio real via Telegram (vínculos em SQLite)

Na UI o envio é **sempre Telegram real** (a CLI preserva o SMS simulado
da story 07). O destino é resolvido por telefone no banco de vínculos
`data/telegram_links.db` (SQLite via stdlib; FORA do Git — ADR-010):

1. Crie o bot no [@BotFather](https://t.me/BotFather) (`/newbot`) e cole o
   token no campo secreto da sidebar (não é persistido; alternativa: env
   `TELEGRAM_BOT_TOKEN`).
2. O segurado manda `/start` no bot e **toca no botão "Compartilhar meu
   contato"** — o Telegram entrega por `chat_id`, nunca por número de
   telefone; o vínculo fica persistido no banco.
3. Clique em **"Vincular contatos"**: grava no SQL quem compartilhou o
   contato e envia o próprio botão do bot para quem só deu `/start`
   (tocar nele e repetir o clique conclui o vínculo).
4. "Disparar Alertas" entrega a mensagem real no chat vinculado
   (status `sent`). Sem token ou sem vínculo o envio vira `skipped`
   com o motivo — e a rodada segue intacta (degradação, ADR-008).

## Regras de negócio (detecção de risco — V2)

| Evento | Gatilho | Impactados | Severidade |
|---|---|---|---|
| Chuva intensa | precipitação ≥ 10 mm/h (≥ 20 high / ≥ 35 very_high) | segurados **residenciais** | medium → very_high |
| Granizo | weathercode de granizo (WMO) | segurados **auto** | high |
| Vento forte | vento ≥ 60 km/h (≥ 80 very_high) | região **costeira** | medium → very_high |
| Calor / onda de calor | ≥ 35 °C / ≥ 38 °C | residencial ou auto | high / very_high |
| Frio intenso | ≤ 10 °C (≤ 5 very_high) | residencial ou auto | high → very_high |
| Neblina | umidade ≥ 95% + vento ≤ 15 km/h + chuva ≤ 10 mm/h | auto | medium → high |
| Tempestade | chuva ≥ 30 + vento ≥ 60 km/h (35/80 very_high) | residencial ou auto | high → very_high |
| Ressaca | litoral + vento ≥ 80 km/h + chuva ≥ 30 mm/h | residencial (litoral) | very_high |
| Múltiplos riscos | ≥ 2 riscos simultâneos | idem aos componentes | severidade máxima |

Cada mensagem traz nome do segurado, evento, severidade e **≥ 2 recomendações
preventivas específicas** do tipo de evento, limitada a 480 caracteres. Com
**≥ 2 riscos simultâneos para o mesmo segurado, ele recebe UMA única
mensagem consolidada** (intent 007) — do evento mais severo ao menos, com
as precauções específicas de cada um (recomendações repetidas entre
eventos aparecem uma só vez); o relatório da rodada segue exibindo cada
alerta individualmente. As regras são **escopadas por ramo com exposição
material** (classificação pessoal/residencial/auto — ADR-009); a neblina
pula a avaliação quando o Open-Meteo não traz umidade (`humidity_pct`
opcional no snapshot).

## Arquitetura (Ports & Adapters / DDD modular)

```text
data/*.json ──► adapters/catalog.py ─┐
Open-Meteo ──► adapters/open_meteo ──┤      ┌─► domain/risk.py   (regras puras)
fixtures ────► adapters/fixtures ────┴─► pipeline.py ──┼─► domain/messages (template/Llm)
                                             ▲         └─► domain/notify   (simulado)
                              cli.py (composition root) ┘
```

- **Domain puro e sem I/O** (`app/domain/`): regras de risco declarativas,
  ports (`WeatherProvider`, `PolicyHolderRepository`, `MessageGenerator`,
  `NotificationSender`, `TelegramLinkRepository`) e entidades.
- **Adapters** (`app/adapters/`): Open-Meteo e BrasilAPI (geocoding de
  CEP), Telegram (envio real + vínculos em SQLite) — todos stdlib-only
  —, catálogo in-memory com seeds JSON, fixtures para demo offline e
  `LlmGenerator` (import lazy de Pydantic AI — o modo template nunca
  exige o SDK).
- **Pipeline** recebe ports prontas; a **CLI** é o composition root
  (`LLM_MODEL`/`LLM_PROVIDER` selecionam a implementação da mensagem).

Modelo binding default do LLM: `openrouter:z-ai/glm-5.3-flash` (mesmo
executor usado pelas ferramentas AI-DLC deste repositório).

## Qualidade e governança

- **TDD** vermelho→verde em todas as units; **194 testes** do produto +
  **122** da suíte AI-DLC (`pytest`), **ruff** e **mypy** limpos.
- **CI obrigatório** em todo PR/push para `main` (`.github/workflows/ci.yml`):
  `ruff check .` + `mypy app` + `pytest`.
- **AI-DLC completo** (ver [AGENTS.md](AGENTS.md)): intents, stories, units,
  bolts e ADRs em [memory-bank/](memory-bank/) — requisitos, decisões e
  execução auditáveis (`docs/decisions/`, `memory-bank/bolts/`).

## Estrutura

```text
app/            produto (domain, adapters, composition, pipeline, cli)
ui/             demo visual (Streamlit, shell fino sobre app/composition)
tests/          testes do produto (pytest; pythonpath=. via pytest.ini)
data/           seeds de segurados + fixtures meteorológicas da demo offline
docs/           decisões (ADRs) e tasks da ferramenta AI-DLC
memory-bank/    intents, stories, units, bolts, standards (AI-DLC Option A)
tools/ai-dlc/   orquestrador + step pré-merge de qualidade (governança)
```
