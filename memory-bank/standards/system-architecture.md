# System Architecture
> Estado: Inicialmente definido em 2026-08-22. Detalhar durante Inception Phase.

## Overview
Arquitetura de **Monolito Modular** (contexto delimitado por módulo) usando **Clean Architecture / Ports & Adapters** (Hexagonal) alinhado a DDD Estratégico.

## Bounded Contexts
> A definir no Inception. Lista inicial TBD. Cada contexto será um módulo Python separado com suas próprias camadas domain/application/infrastructure/interface.

## Architecture Patterns
- **Domain-Driven Design (DDD)**: Entidades, VOs, Aggregates, Repositories (como Ports/Interfaces), Domain Services, Domain Events.
- **Ports & Adapters (Hexagonal)**: Isolamento do domínio em relação a frameworks e externals.
- **CQRS (opcional)**: Considerar se houve necessidade de modelos separados read/write. Decidir por ADR.
- **Dependency Injection**: Uso de DI container leve (ex: `dependency-injector`) ou manual via FastAPI Depends.

## Core Architectural Layers (por contexto)
```
Interface (FastAPI routers, CLI handlers)
    | uses
Application (Use cases, DTOs, command/query handlers)
    | uses
Domain (Entities, VOs, Aggregates, Domain Events, Repository interfaces)
    | implements (Infra depends on Domain)
Infrastructure (Repository impl, DB, message brokers, external APIs)
```

## Cross-Cutting Concerns
- **Logging**: structlog (standards)
- **Tracing**: OpenTelemetry (TBD)
- **Validation**: Pydantic v2 em portas de entrada e VOs de domínio
- **Auth/Z**: Middleware + domain-level policies (TBD)

## Data
- **DB**: TBD (PostgreSQL recomendado por padrão)
- **Migrations**: Alembic
- **ORM**: SQLAlchemy 2.0 (repositórios concretos em infra)

## Deployment
- **Container: Docker + docker compose (local)**
- **Target env**: TBD em Operations Phase
