"""AI-DLC Orchestrator — camada subordinada de execução (ADR-006).

Fase 1 (stub): roteamento determinístico, loop de 7 passos, gates e
contrato de capacidade — sem rede e sem dependências novas (pydantic/
pytest já presentes no ambiente).

- `call_executor_llm()` e `call_independent_critic()` são stubs tipados
  determinísticos: o bolt da fase 2 substitui o interior (OpenRouter
  real) mantendo assinaturas e contratos.
- Ordem de autoridade: AGENTS.md > .trae/project_rules.md > ai-dlc-spec.yaml.
- Níveis unificados com depth_levels (context-budget): N1=TINY, N2=STANDARD,
  N3=DEEP. Schema/segredos → N3 (checkpoint do project_rules).
- Binding de modelos por env (ADR-004): OPENROUTER_MODEL_FAST/BALANCED/
  DEEP/CRITIC. Valores validados na API pública do OpenRouter (2026-09-01).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from contracts import (
    BlockerType,
    CapacityDecision,
    CriticReview,
    DifficultyLevel,
    ExecutorProposal,
    IterationRecord,
    LoopResult,
    ModelProfile,
    TaskContext,
)

MODEL_PROFILES: dict[str, ModelProfile] = {
    # Valores validados na API pública do OpenRouter (2026-09-01):
    # modelo fast exige o alias "~" (sem til → 404); GLM aceita apenas
    # max/high/low (mandatory=true) — balanced usa "high".
    "code_fast": ModelProfile(
        name="code_fast",
        env_var="OPENROUTER_MODEL_FAST",
        default_model="~deepseek/deepseek-v4-flash-latest",
        temperature=0.2,
        thinking=False,
        reasoning_effort="low",
        max_tokens=4096,
        endpoint_tags=["baidu/fp8", "deepinfra/fp8", "open-inference/fp8"],
        quantizations=["fp8"],
    ),
    "code_balanced": ModelProfile(
        name="code_balanced",
        env_var="OPENROUTER_MODEL_BALANCED",
        default_model="z-ai/glm-5.3-flash",
        temperature=0.3,
        thinking=True,
        reasoning_effort="high",  # GLM: supported_efforts=[max, high, low]
        max_tokens=8192,
        endpoint_tags=["z-ai/fp8", "novita/fp8", "gmicloud/fp8"],
        quantizations=["fp8"],
    ),
    "code_deep": ModelProfile(
        name="code_deep",
        env_var="OPENROUTER_MODEL_DEEP",
        default_model="z-ai/glm-5.3-flash",
        temperature=0.5,
        thinking=True,
        reasoning_effort="max",
        max_tokens=16384,
        endpoint_tags=["z-ai/fp8", "novita/fp8", "gmicloud/fp8"],
        quantizations=["fp8"],
    ),
}

# Crítico independente (decisão do usuário, 2026-09-01): modelo separado.
# openai/flex confirmado como tag de endpoint na API.
CRITIC_PROFILE: ModelProfile = ModelProfile(
    name="critic",
    env_var="OPENROUTER_MODEL_CRITIC",
    default_model="openai/gpt-5.6-luna-pro",
    temperature=0.2,
    thinking=True,
    reasoning_effort="max",
    max_tokens=20000,
    endpoint_tags=["openai/flex"],
)

PROFILE_BY_LEVEL: dict[int, str] = {1: "code_fast", 2: "code_balanced", 3: "code_deep"}


def classify_task(ctx: TaskContext) -> DifficultyLevel:
    """Roteamento determinístico por sinais objetivos (spec: objective_signals).

    N3: arquitetura, segurança/dados, migration, schema, auth/segredos ou
    risco alto. N2: 3+ arquivos, concorrência/infra ou risco médio.
    N1: caso contrário.
    """
    if (
        ctx.involves_architecture
        or ctx.involves_security_or_data
        or ctx.involves_migration
        or ctx.has_schema_changes
        or ctx.has_auth_or_secrets
        or ctx.risk == "high"
    ):
        return DifficultyLevel.N3
    if ctx.files_involved >= 3 or ctx.has_concurrency_or_infra or ctx.risk == "medium":
        return DifficultyLevel.N2
    return DifficultyLevel.N1


def profile_for(level: DifficultyLevel) -> ModelProfile:
    return MODEL_PROFILES[PROFILE_BY_LEVEL[int(level)]]


def requires_dual_confirmation(level: DifficultyLevel) -> bool:
    """Gate N3: dupla confirmação humana (decisão do usuário, Q-gates)."""
    return level is DifficultyLevel.N3


# --------------------------------------------------------------------------
# Stubs tipados (fase 1) — fase 2 troca o interior, não a assinatura.
# --------------------------------------------------------------------------


def call_executor_llm(
    ctx: TaskContext, iteration: int, profile: ModelProfile
) -> ExecutorProposal:
    """Stub determinístico: tests verdes na 2ª iteração, aceitação na 3ª."""
    return ExecutorProposal(
        stub=True,
        summary=f"[stub] iteração {iteration} de {ctx.task_id}",
        changed_files=[],
        tests_pass=iteration >= 2,
        acceptance_criteria_met=iteration >= 3,
        notes=["stub: substituir no bolt da fase 2 (executor OpenRouter real)"],
    )


def call_independent_critic(proposal: ExecutorProposal) -> CriticReview:
    """Stub: aceita somente com stop rule satisfeita; senão pede repair."""
    if proposal.tests_pass and proposal.acceptance_criteria_met:
        verdict, reason = "accept", "critérios de aceite e testes confirmados"
    else:
        verdict, reason = "repair", "stop rule ainda não satisfeita"
    return CriticReview(
        stub=True,
        verdict=verdict,
        reason=reason,
        risk_notes=["stub: crítico independente real entra na fase 2"],
    )


# --------------------------------------------------------------------------
# Loop principal
# --------------------------------------------------------------------------

VerifyFn = Callable[[TaskContext, ExecutorProposal], bool]
ExecutorFn = Callable[[TaskContext, int, ModelProfile], ExecutorProposal]
CriticFn = Callable[[ExecutorProposal], CriticReview]
CapacityFn = Callable[[ExecutorProposal, int], CapacityDecision | None]


def run_loop(
    ctx: TaskContext,
    *,
    verify: VerifyFn | None = None,
    executor_fn: ExecutorFn | None = None,
    critic_fn: CriticFn | None = None,
    capacity_fn: CapacityFn | None = None,
    log_sink: list[dict] | None = None,
    human_confirmed: bool = False,
    max_iterations: int | None = None,
    log_path: "str | Path | None" = None,
) -> LoopResult:
    """Executa o loop plan→act→verify→critic até stop rule ou gate.

    Stop rules:
      success = tests_pass E acceptance_criteria_met E critic=accept.
      blocked = capacidade bloqueada OU estagnação (max_iterations).
    Gate N3: sem `human_confirmed`, retorna awaiting_dual_confirmation.
    Se `log_path` for informado, persiste auditoria via
    write_maintenance_entry() ao final do run.
    """
    result = _run_loop_inner(
        ctx,
        verify=verify,
        executor_fn=executor_fn,
        critic_fn=critic_fn,
        capacity_fn=capacity_fn,
        log_sink=log_sink,
        human_confirmed=human_confirmed,
        max_iterations=max_iterations,
    )
    if log_path is not None:
        write_maintenance_entry(log_path, result)
    return result


def _run_loop_inner(
    ctx: TaskContext,
    *,
    verify: VerifyFn | None,
    executor_fn: ExecutorFn | None,
    critic_fn: CriticFn | None,
    capacity_fn: CapacityFn | None,
    log_sink: list[dict] | None,
    human_confirmed: bool,
    max_iterations: int | None,
) -> LoopResult:
    level = classify_task(ctx)
    profile = profile_for(level)

    if requires_dual_confirmation(level) and not human_confirmed:
        record = IterationRecord(
            iteration=0, profile=profile.name, outcome="awaiting_human"
        )
        _persist(log_sink, record)
        return LoopResult(
            status="awaiting_dual_confirmation",
            iterations=0,
            level=level,
            profile=profile.name,
            records=[record],
        )

    verify = verify or (lambda _ctx, proposal: proposal.tests_pass)
    executor_fn = executor_fn or call_executor_llm
    critic_fn = critic_fn or call_independent_critic
    cap = max_iterations if max_iterations is not None else level.max_iterations

    records: list[IterationRecord] = []
    for iteration in range(1, cap + 1):
        proposal = executor_fn(ctx, iteration, profile)
        verified = verify(ctx, proposal)
        critic = critic_fn(proposal)

        capacity = capacity_fn(proposal, iteration) if capacity_fn else None
        if capacity is not None and capacity.status == "blocked":
            record = IterationRecord(
                iteration=iteration,
                profile=profile.name,
                executor=proposal,
                critic=critic,
                capacity=capacity,
                outcome="blocked",
            )
            records.append(record)
            _persist(log_sink, record)
            return LoopResult(
                status="blocked",
                iterations=iteration,
                level=level,
                profile=profile.name,
                blocker_type=capacity.blocker_type,
                records=records,
            )

        success = (
            verified
            and proposal.acceptance_criteria_met
            and critic.verdict == "accept"
        )
        record = IterationRecord(
            iteration=iteration,
            profile=profile.name,
            executor=proposal,
            critic=critic,
            outcome="success" if success else "repair",
        )
        records.append(record)
        _persist(log_sink, record)
        if success:
            return LoopResult(
                status="success",
                iterations=iteration,
                level=level,
                profile=profile.name,
                records=records,
            )

    # Estagnação: esgotou max_iterations sem success (stop rule).
    capacity = CapacityDecision(
        status="blocked",
        confidence=1.0,
        can_continue_autonomously=False,
        blocker_type=BlockerType.stagnation,
        evidence=[f"max_iterations={cap} atingido sem stop rule satisfeita"],
        required_human_input=[
            "revisar escopo/critérios ou reclassificar a dificuldade"
        ],
        safe_next_actions=["quebrar a tarefa em unidades menores"],
    )
    record = IterationRecord(
        iteration=cap,
        profile=profile.name,
        capacity=capacity,
        outcome="blocked",
    )
    records.append(record)
    _persist(log_sink, record)
    return LoopResult(
        status="blocked",
        iterations=cap,
        level=level,
        profile=profile.name,
        blocker_type=BlockerType.stagnation,
        records=records,
    )


def _persist(log_sink: list[dict] | None, record: IterationRecord) -> None:
    """Persistência por iteração (fase 1: sink; fase 2: maintenance-log.md)."""
    if log_sink is not None:
        log_sink.append(record.model_dump(mode="json"))


def write_maintenance_entry(path: "str | Path", result: LoopResult) -> None:
    """Append de uma entrada de auditoria por run em arquivo markdown.

    Formato compatível com memory-bank/maintenance-log.md: cabeçalho
    compacto + records completos em bloco JSON (auditoria por iteração).
    """
    target = Path(path)
    header = (
        f"- **ai-dlc run: {result.status}** (task-level)\n"
        f"  - iterations={result.iterations} level={result.level.name} "
        f"profile={result.profile} blocker={result.blocker_type.value if result.blocker_type else 'none'}\n"
    )
    payload = json.dumps(
        [r.model_dump(mode="json") for r in result.records], ensure_ascii=False, indent=2
    )
    block = f"{header}```json\n{payload}\n```\n"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(block)


if __name__ == "__main__":
    demo_ctx = TaskContext(
        task_id="demo-001",
        objective="Implementar endpoint de desconto com cupom",
        acceptance_criteria=["cupom aplicado", "testes verdes"],
        files_involved=4,
        risk="medium",
    )
    sink: list[dict] = []
    result = run_loop(demo_ctx, log_sink=sink)
    print(f"status={result.status} iterations={result.iterations} "
          f"level={result.level.name} profile={result.profile}")
    for entry in sink:
        print(f"  it={entry['iteration']} outcome={entry['outcome']}")
