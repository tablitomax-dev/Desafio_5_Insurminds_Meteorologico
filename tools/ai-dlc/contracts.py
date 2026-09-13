"""Contratos tipados da camada de execução AI-DLC (ADR-006).

Fontes de design: rascunho externo v0.6.x (referência), adaptado aos
padrões do repo — Pydantic v2 (tech-stack), níveis unificados com
depth_levels do context-budget, binding de modelos por env (ADR-004).
Fase 1: sem rede, sem dependências além de pydantic.
"""

from __future__ import annotations

import os
from enum import Enum, IntEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DifficultyLevel(IntEnum):
    """Nível de dificuldade unificado com depth_levels (context-budget)."""

    N1 = 1
    N2 = 2
    N3 = 3

    @property
    def depth(self) -> str:
        return {1: "TINY", 2: "STANDARD", 3: "DEEP"}[int(self)]

    @property
    def max_iterations(self) -> int:
        return {1: 3, 2: 5, 3: 7}[int(self)]


class BlockerType(str, Enum):
    """Tipos de bloqueio do contrato de capacidade."""

    missing_credentials = "missing_credentials"
    missing_product_decision = "missing_product_decision"
    ambiguous_requirement = "ambiguous_requirement"
    destructive_next_step = "destructive_next_step"
    non_reproducible_error = "non_reproducible_error"
    stagnation = "stagnation"


class TaskContext(BaseModel):
    """Contexto da tarefa com sinais objetivos para roteamento."""

    task_id: str
    objective: str
    acceptance_criteria: list[str] = Field(min_length=1)
    files_involved: int = Field(default=1, ge=1)
    has_schema_changes: bool = False
    has_auth_or_secrets: bool = False
    has_concurrency_or_infra: bool = False
    involves_architecture: bool = False
    involves_security_or_data: bool = False
    involves_migration: bool = False
    risk: RiskLevel = RiskLevel.LOW


class ModelProfile(BaseModel):
    """Perfil de modelo model-agnostic: binding via env (ADR-004)."""

    name: str
    env_var: str
    default_model: str
    temperature: float = Field(default=0.2, ge=0, le=2)
    thinking: bool = False
    # Binding definitivo (decisão do usuário, 2026-09-01; validado na API
    # pública do OpenRouter — /api/v1/models e /endpoints):
    reasoning_effort: Literal["max", "xhigh", "high", "medium", "low", "minimal", "none"] | None = None
    max_tokens: int = Field(default=4096, ge=1)
    endpoint_tags: list[str] = Field(default_factory=list)  # tags de endpoint (ex.: "z-ai/fp8")
    quantizations: list[str] = Field(default_factory=list)   # ex.: ["fp8"]

    def resolve_model(self) -> str:
        value = os.getenv(self.env_var, "").strip()
        return value or self.default_model

    def provider_policy(self) -> dict:
        """Objeto `provider` do OpenRouter: whitelist de tags + quantização.

        Tags de endpoint confirmadas na API (campo `tag`, ex.: "z-ai/fp8",
        "openai/flex"). Fallback só entre endpoints da lista
        (allow_fallbacks=true padrão); sem fallback de modelo (decisão do
        usuário).
        """
        policy: dict = {"only": list(self.endpoint_tags)} if self.endpoint_tags else {}
        if self.quantizations:
            policy["quantizations"] = list(self.quantizations)
        return policy


class CapacityDecision(BaseModel):
    """Contrato de capacidade: status ok/warning/blocked."""

    status: Literal["ok", "warning", "blocked"]
    confidence: float = Field(ge=0.0, le=1.0)
    can_continue_autonomously: bool = True
    blocker_type: BlockerType | None = None
    evidence: list[str] = Field(default_factory=list)
    required_human_input: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistency(self) -> "CapacityDecision":
        if self.status == "blocked":
            if self.blocker_type is None:
                raise ValueError("blocker_type é obrigatório quando status='blocked'")
            if self.can_continue_autonomously:
                raise ValueError("status 'blocked' implica can_continue_autonomously=False")
        if self.status == "ok" and self.blocker_type is not None:
            raise ValueError("blocker_type deve ser nulo quando status='ok'")
        if self.status == "warning" and not self.required_human_input:
            raise ValueError("status 'warning' exige required_human_input (pausa + opções)")
        return self


class ExecutorProposal(BaseModel):
    """Proposta do executor: o LLM só propõe, o loop valida."""

    stub: bool = False
    summary: str
    changed_files: list[str] = Field(default_factory=list)
    tests_pass: bool
    acceptance_criteria_met: bool
    notes: list[str] = Field(default_factory=list)
    # Metadados de uso (fase 2, chamadas reais; default None nos stubs)
    model: str | None = None
    provider: str | None = None
    usage: dict | None = None


class CriticReview(BaseModel):
    """Veredito do crítico independente."""

    stub: bool = False
    verdict: Literal["accept", "repair", "blocked"]
    reason: str
    risk_notes: list[str] = Field(default_factory=list)
    # Metadados de uso (fase 2, chamadas reais; default None nos stubs)
    model: str | None = None
    provider: str | None = None
    usage: dict | None = None


class IterationRecord(BaseModel):
    """Registro auditável de uma iteração (persistência por iteração)."""

    iteration: int
    profile: str
    executor: ExecutorProposal | None = None
    critic: CriticReview | None = None
    capacity: CapacityDecision | None = None
    outcome: Literal["continue", "repair", "success", "blocked", "awaiting_human"]


class LoopResult(BaseModel):
    """Resultado do run_loop."""

    status: Literal["success", "blocked", "awaiting_dual_confirmation"]
    iterations: int
    level: DifficultyLevel
    profile: str
    blocker_type: BlockerType | None = None
    records: list[IterationRecord] = Field(default_factory=list)
    task_id: str = ""  # preenchido pelo run_loop (auditoria/dashboard)
