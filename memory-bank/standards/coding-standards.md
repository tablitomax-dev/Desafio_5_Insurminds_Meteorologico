# Coding Standards
> Estado: Inicialmente definido em 2026-08-22. A refinar durante o skill project-init.

## Overview
Padrões alinhados ao perfil: DDD Estratégico, KISS/YAGNI, TDD (testes ANTES do código), SDD e forte encapsulamento.

## Code Formatting
- **Tool: Ruff (format)** — Black-compatible, extremamente rápido.
- **Key Settings**:
  - Line length: 100
  - Indentation: 4 spaces
  - Target version: Python 3.12+
- **Enforcement**: pre-commit hooks + CI.

## Linting
- **Tool: Ruff**
- **Base Config**: `ruff default rules` + `pydocstyle` (parcial) + `pyflakes`
- **Strictness**: balanced (erros em bugs/warnings em estilo)
- **Key Rules**:
  - Unused imports/vars: error
  - Complexity (McCabe) > 10: warning
  - No bare `except`: error

## Type System
- **Type hints OBRIGATÓRIOS em toda a surface pública de domínio e aplicação.**
- Verificação estática: **mypy --strict** (a ajustar gradualmente).

## Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Variáveis, funções, métodos | snake_case | `user_name`, `register_user` |
| Classes, Interfaces (Protocol) | PascalCase | `User`, `UserRepository` |
| Constantes | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Módulos/arquivos | snake_case | `user_service.py` |
| Private | leading underscore | `_internal_calc` |
| Interfaces (Protocol) | PascalCase sem prefixo I | `UserRepository` (não `IUserRepository`) |
| Bool prefix | `is_`, `has_`, `can_` | `is_active` |

**File Naming**:
- Domínio: `{aggregate_context}/{entity|vo|service}.py`
- Testes: `test_{nome}.py` co-localizados ou em `tests/`

## File Organization
- **Pattern: DDD (Domain-Driven) em Monolito Modular.**

```text
src/
  {bounded_context}/
    domain/         # Entities, VOs, Aggregates, Domain Events, Repositories (Protocol)
    application/    # Use cases (services de aplicação), DTOs, Ports
    infrastructure/ # Repositories impl, DB, external adapters
    interface/      # API controllers, handlers (FastAPI routers)
tests/
  unit/
  integration/
  e2e/
```

**Conventions**:
- Tests: `tests/` no root (ou co-localizados em `tests/` por contexto)
- Tipos: Definidos junto ao domínio (`.domain/`) ou em `application/dto/`
- Index files (`__init__.py`): Usar apenas para exports públicos, reduzir acoplamento.

## Testing Strategy (TDD - RIGOROSO)
- **Framework: pytest + pytest-asyncio**
- **Coverage Target**: 80% global, 100% em camadas `domain/` e `application/`
- **TDD Rule**: Teste escrito ANTES do código de produção. Ciclo: Red → Green → Refactor.

**Test Types**:
| Type | Tool | When to Use |
|------|------|-------------|
| Unit | pytest | Entities, VOs, serviços de domínio, use cases (com ports mockados) |
| Integration | pytest + testcontainers | Repositórios concretos, DB, adapters externos |
| E2E | pytest + httpx (FastAPI TestClient) | Fluxos completos via API |
| Property-Based | hypothesis | invariantes de domínio, parsers, serialização |

**Conventions**:
- Naming: `def test_{given}_{when}_{then}():`
- Estrutura: **Arrange-Act-Assert** (Given-When-Then)
- Mock strategy: Mocar APENAS ports/adapters externos. NÃO mockar domínio.
- Test data: **polyfactory** factories (não fixtures gigantes).

## Error Handling
- **Pattern: Throw (raise) custom errors de domínio.** Tratamento em camada de interface (middleware do FastAPI).
- **Custom Errors**: Sim, herdar de `DomainError`, `ApplicationError`, `InfrastructureError`.
- **API Errors**: Formato padrão RFC 7807 (Problem Details) via middleware.

## Logging
- **Tool: structlog (estruturado, JSON em prod)**
- **Format**: JSON em prod, console colorido em dev.
- **Níveis**: error, warn, info, debug.
- **Rules**:
  - Sempre logar: eventos de domínio importantes (registro, pagamento), request (method, path, status, duration), erros com context.
  - Nunca logar: secrets, PII sensível, tokens, senhas.
