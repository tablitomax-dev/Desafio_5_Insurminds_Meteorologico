# Intent 003 — streamlit-ui

> Status: `in_progress` (mudança isolada de 1 PR em execução) | Owner: pablo |
> Priority: P1 | Criado: 2026-09-04
>
> Contexto: o desafio I2A2 já está fechado pelo intent 002 (MVP funcional
> via CLI). Este intent é a camada de APRESENTAÇÃO da banca — nenhuma
> regra de negócio nova.

## Problema / capacidade

O relatório da rodada existe apenas no console (`python -m app run`).
Para a banca, a demo fica mais forte com uma visual interativa: escolher
a fonte (offline/online) e o modo de mensagem (template/LLM) e ver KPIs,
alertas e as mensagens geradas em cards — com o modo exercitado sempre
reportado.

## Decisões (aprovadas pelo humano 2026-09-04)

| Decisão | Escolha | Registro |
|---|---|---|
| Framework da UI | **Streamlit** (Python-only, demo rápida) | isto (FastAPI+HTML e `--html` na CLI avaliados e descartados) |
| Posição na arquitetura | Shell fino `ui/demo_app.py` → **reusa o composition root** extraído em `app/composition.py` (CLI e UI montam o mesmo grafo) | isto |
| Dependência | `streamlit` em `requirements-ui.txt` — **fora do CI** (produto segue stdlib-only; `mypy app` não cobre `ui/` e ruff não resolve imports) | isto |
| Regras de negócio | NENHUMA nova — a UI apenas apresenta o relatório do pipeline | isto |
| Defaults da sidebar | **Online (Open-Meteo) + LLM** primeiro (pedido do dono 2026-09-06); fallback silencioso garante a demo sem chave | isto |

## Escopo (1 PR)

- `app/composition.py`: composition root compartilhado —
  `build_weather_provider` + `run_proactive_round` (retorna relatório e
  modo exercitado)
- `app/adapters/llm_messages.py`: `build_generator` aceita `provider`
  explícito (além do env da story 06, que segue valendo como fallback)
- `app/cli.py`: usa o composition root compartilhado (comportamento idêntico)
- `ui/demo_app.py`: sidebar (fonte, mensagem, modelo pydantic-ai) + KPIs +
  tabela **Segurados monitorados** (cidade/região, coordenadas, tempo
  atual e alerta gerado — ampliação aprovada 2026-09-06) + alertas +
  mensagens em cards + relatório textual em expander
- `data/policy_holders.json`: campo `city` nos 8 seeds com
  **bairro/região + cidade** (ex.: "República, São Paulo/SP") e
  coordenadas a 4 casas decimais
- `app/adapters/open_meteo.py`: URL da API usa lat/lon a **4 casas
  decimais** (recomendação da própria Open-Meteo, ≈ 11 m; pedido do dono
  2026-09-06). Bairro/região: a Open-Meteo NÃO tem reverse geocoding —
  fica como rótulo nos seeds (sem API nova)
- **CEP na bancada** (ampliação 2, aprovada 2026-09-06): a banca edita
  **CEP** (não lat/lon) → BrasilAPI CEP v2 resolve bairro/cidade +
  coordenadas (`CepGeocoder` port + `BrasilApiGeocoder` adapter +
  `GeocodingError`, ADR-007), cache por sessão e degradação graciosa
  (sem coords/rede → coords dos seeds + aviso; nunca quebra). User-Agent
  próprio obrigatório (BrasilAPI bloqueia urllib default com 403).
  Seeds com CEPs reais (H001 01016-020 … H008 12210-060)
- **Geocode automático + botão Disparar Alertas** (ampliação 3, aprovada
  2026-09-06): coluna Litoral removida da bancada (perfil vem dos seeds);
  ao digitar CEP válido, bairro/cidade é atualizado na hora e o **clima
  da região** aparece em preview (online: Open-Meteo nas coords do CEP;
  offline: tempo da bancada); botão "Rodar rodada" renomeado para
  **"Disparar Alertas"**
- `app/pipeline.py`: `RoundReport.snapshots` (tempo efetivo de cada
  segurado consultado; default `()` — sem quebra de contratos)
- `app/composition.py`: `run_proactive_round` aceita `holders` e
  `weather_snapshots` injetados (bancada da UI) — as regras do domínio
  continuam gerando os alertas analisando o tempo informado
- Dívida documentada: testes automatizados da UI (AppTest não suporta
  `data_editor` na 1.63) — bancada validada por smoke manual + testes
  do composition (TDD)
- `requirements-ui.txt`: pin da demo visual
- Testes TDD: `tests/test_composition.py` (fonte offline/online, escolha
  explícita template/LLM, env como fallback quando parâmetros omitidos)

## Fora de escopo

Edição de segurados; envio real; autenticação; temas customizados;
testes automatizados da UI via `st.testing.v1.AppTest` (dívida opcional).

## Critérios de aceite

1. [ ] `streamlit run ui/app.py` roda a demo nos 4 modos (offline, online, LLM real, fallback sem chave)
2. [ ] O modo exercitado (template / llm / fallback) é sempre visível na UI
3. [ ] CLI mantém comportamento e suíte verde (nenhum contrato mudou)
4. [ ] `ruff` / `mypy app` / `pytest` verdes sem streamlit instalado no CI
5. [ ] README documenta como rodar a demo visual
