# Intent 002 — proactive-communication

> Status: `done` (2026-09-04 — 7/7 stories implementadas via TDD e mergeadas
> em `main` por squash: PRs #6, #7, #11; CI mandatário verde) | Owner: pablo |
> Priority: P0 | Criado: 2026-08-29
>
> Contexto: trabalho acadêmico I2A2 — Desafio 5 "Ferramenta Inteligente
> para Comunicação Proativa com o Segurado". Primeiro intent de PRODUTO
> (o intent 001 foi de fundação do repositório).

## Problema / capacidade

Comunicação seguradora↔segurado hoje é reativa (após sinistro). Queremos
monitorar eventos meteorológicos externos e gerar avisos preventivos
personalizados ANTES do sinistro, demonstrando o valor de agentes
inteligentes no relacionamento seguradora-segurado.

## Capacidade desejada (MVP)

Fluxo completo demonstrável: coleta em API pública meteorológica →
identificação de eventos relevantes → regras de negócio por perfil de
seguro → geração de mensagens personalizadas (IA/template) → simulação
de envio. Sem envio real de SMS/e-mail/push.

## Decisões de Inception (aprovadas pelo humano 2026-08-29)

| Decisão | Escolha | Registro |
|---|---|---|
| Fonte meteorológica | **Open-Meteo** (aberta, sem API key) | ADR-005 |
| Interface de demo | **CLI/pipeline** (`python -m app run`) | isto (MVP; API FastAPI é YAGNI agora) |
| Mensagens | **Template paramétrico + LLM opcional** (Pydantic AI, model-agnostic via env) | isto |
| Persistência | **In-memory + seeds JSON**; DuckDB quando precisar de banco | isto |
| Stack | Python 3.12, pytest (TDD), Ruff, mypy — padrões do template | tech-stack.md |

## Escopo

- 6 units (ver `units/`), 7 stories (ver `stories/`)
- Regras de risco: chuva intensa→residencial; granizo→auto; vento
  forte→regiões costeiras (+ recomendações preventivas)
- Relatório da rodada visível no console (eventos, impactados, mensagens, envios simulados)

## Fora de escopo

- Envio real de notificações; frontend; autenticação; persistência SQL
  (DuckDB entra só se necessário); múltiplas fontes simultâneas (adapter
  isolado permite crédito futuro)

## Critérios de aceite do intent

1. [x] `python -m app run` executa o fluxo completo ponta a ponta (mock/offline-free via Open-Meteo real)
2. [x] Segurados de seeds recebem apenas alertas condizentes com perfil/região
3. [x] Regras de risco 100% cobertas por testes unitários (TDD, núcleo sem I/O)
4. [x] Mensagens: template determinístico sempre funciona; LLM opcional melhora, sem quebrar demo se não houver key
5. [x] ADR-005 documenta a fonte com alternativas e trade-offs
6. [x] Relatório final em console demonstra etapas 1–5 do enunciado

## Fechamento (2026-09-04)

MVP concluído: 7/7 stories `done` (PRs #6, #7 e #11), README de apresentação
na raiz, demo offline determinística para a banca e modo LLM com fallback
garantido (`openrouter:z-ai/glm-5.3-flash`). Dívidas não-bloqueantes da
fundação ficam no intent 001; evoluções futuras exigem novo intent.
