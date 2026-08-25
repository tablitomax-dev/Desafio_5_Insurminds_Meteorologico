# Tech Stack
> Estado: Inicialmente definido em 2026-08-22. A refinar durante o skill project-init.

## Overview
Stack alinhada ao perfil do usuário: Python como linguagem principal, foco em DDD Estratégico, Monolito Modular e TDD. Ajustes serão aplicados via decision-index ao longo dos bolts.

## Languages
- **Principal: Python 3.12+**
  - Rationale: Preferência declarada do usuário para agentes de IA e automação com Pydantic AI. Ecossistema maduro para DDD (Pydantic, SQLAlchemy 2.0, polyfactory).
- TypeScript poderá ser adicionado futuramente caso haja frontend.

## Framework
- **API: FastAPI**
  - Rationale: Async, tipagem forte (Pydantic integrado), auto-docs. Bom fit para DDD e monolito modular.
- **Testes: pytest + pytest-asyncio + polyfactory + hypothesis**
  - Rationale: TDD rigoroso exigido. hypothesis para property-based testing.

## Authentication
- TBD — definir no Inception (será decidido durante a fase de Inception)

## Infrastructure & Deployment
- **Ambiente local: Docker + docker compose**
- **Cloud Provider: TBD** (a definir no Operations Phase)

## Package Manager
- **pip + venv (requirements.txt) OU pdm/poetry** — TBD no project-init.
- Preferência inicial: **pdm** por lock determinístico e suporte nativo a PEP 582/621.

## Domain & Architecture Tooling
- **Pydantic v2** — Value Objects, DTOs, validações.
- **SQLAlchemy 2.0** — ORM estilo repositório.
- **dddlib (ou implementação própria)** — Aggregates, Entities, Domain Events (a decidir em ADR).
