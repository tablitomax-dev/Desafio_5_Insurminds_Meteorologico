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
from openrouter_client import OpenRouterError, chat

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
        notes=["stub: padrão determinístico dos testes; fns reais são injetadas"],
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
        risk_notes=["stub: crítico determinístico; fn real é call_independent_critic_real"],
    )


# --------------------------------------------------------------------------
# Adapters reais (fase 2) — OpenRouter via openrouter_client (urllib).
# Erros de rede NUNCA derrubam o loop: viram proposal/review com o erro
# anotado (o loop aplica as stop rules sobre eles).
# --------------------------------------------------------------------------

EXECUTOR_SYSTEM_PROMPT = (
    "Você é o executor do loop AI-DLC (ADR-006). Responda SOMENTE com um "
    "objeto JSON válido, sem texto fora do JSON, com as chaves: "
    'summary (string), changed_files (array de strings), tests_pass (boolean), '
    "acceptance_criteria_met (boolean), notes (array de strings)."
)

CRITIC_SYSTEM_PROMPT = (
    "Você é o crítico independente do loop AI-DLC (ADR-006). Avalie a "
    "proposta contra a stop rule: tests_pass E acceptance_criteria_met E "
    "veredito accept. Responda SOMENTE com um objeto JSON válido, com as "
    'chaves: verdict ("accept" | "repair" | "blocked"), reason (string), '
    "risk_notes (array de strings)."
)


def _message_content(data: dict) -> str:
    try:
        return str(data["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError):
        return ""


def _extract_json(content: str) -> dict | None:
    """Parse tolerante: JSON direto, bloco cercado ```json ou embutido em prosa."""
    if not content:
        return None
    text = content.strip()
    candidates: list[str] = []
    if "```" in text:  # blocos cercados
        for part in text.split("```"):
            part = part.strip()
            if part.lower().startswith("json"):
                part = part[4:].strip()
            if part:
                candidates.append(part)
    candidates.append(text)
    lo, hi = text.find("{"), text.rfind("}")
    if lo != -1 and hi > lo:
        candidates.append(text[lo : hi + 1])
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def call_executor_llm_real(
    ctx: TaskContext,
    iteration: int,
    profile: ModelProfile,
    *,
    api_key: "str | None" = None,
) -> ExecutorProposal:
    """Executor real: propõe via OpenRouter; parse tolerante do JSON."""
    prompt_user = (
        f"Tarefa {ctx.task_id}: {ctx.objective}\n"
        "Critérios de aceite:\n- " + "\n- ".join(ctx.acceptance_criteria)
        + f"\n\nIteração {iteration}. Se os critérios ainda não estiverem "
        "atendidos, marque tests_pass/acceptance_criteria_met como false e "
        "liste em notes o que falta."
    )
    try:
        data = chat(
            profile,
            [
                {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_user},
            ],
            api_key=api_key,
        )
    except OpenRouterError as exc:
        return ExecutorProposal(
            stub=False,
            summary=f"[erro de transporte] iteração {iteration} de {ctx.task_id}",
            tests_pass=False,
            acceptance_criteria_met=False,
            notes=[f"OpenRouterError: {exc}"],
        )

    usage, model, provider = data.get("usage"), data.get("model"), data.get("provider")
    content = _message_content(data)
    obj = _extract_json(content)
    if obj is None:
        return ExecutorProposal(
            stub=False,
            summary=f"[resposta não-JSON] iteração {iteration} de {ctx.task_id}",
            tests_pass=False,
            acceptance_criteria_met=False,
            notes=["conteúdo sem JSON parseável", f"preview: {content[:200]}"],
            model=model,
            provider=provider,
            usage=usage,
        )
    return ExecutorProposal(
        stub=False,
        summary=str(obj.get("summary", "")),
        changed_files=[str(f) for f in obj.get("changed_files", []) if f],
        tests_pass=bool(obj.get("tests_pass", False)),
        acceptance_criteria_met=bool(obj.get("acceptance_criteria_met", False)),
        notes=[str(n) for n in obj.get("notes", []) if n],
        model=model,
        provider=provider,
        usage=usage,
    )


def call_independent_critic_real(
    proposal: ExecutorProposal, *, api_key: "str | None" = None
) -> CriticReview:
    """Crítico real: CRITIC_PROFILE independente avalia a proposta."""
    payload = json.dumps(proposal.model_dump(mode="json"), ensure_ascii=False, default=str)
    prompt_user = (
        f"Proposta do executor (JSON):\n{payload}\n\n"
        "Avalie contra a stop rule e responda com o JSON do sistema."
    )
    try:
        data = chat(
            CRITIC_PROFILE,
            [
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_user},
            ],
            api_key=api_key,
        )
    except OpenRouterError as exc:
        return CriticReview(
            stub=False,
            verdict="blocked",
            reason=f"crítico indisponível: {exc}",
        )

    usage, model, provider = data.get("usage"), data.get("model"), data.get("provider")
    content = _message_content(data)
    obj = _extract_json(content)
    verdict = str(obj.get("verdict", "")).lower() if obj else ""
    if obj is None or verdict not in ("accept", "repair", "blocked"):
        return CriticReview(
            stub=False,
            verdict="repair",
            reason="resposta malformada do crítico (JSON/verdict ausente ou inválido)",
            risk_notes=[f"preview: {content[:200]}"],
            model=model,
            provider=provider,
            usage=usage,
        )
    return CriticReview(
        stub=False,
        verdict=verdict,  # type: ignore[arg-type] — validado no if acima
        reason=str(obj.get("reason", "")),
        risk_notes=[str(n) for n in obj.get("risk_notes", []) if n],
        model=model,
        provider=provider,
        usage=usage,
    )


def real_functions(api_key: "str | None" = None) -> dict[str, Callable]:
    """Fns reais com assinaturas do loop (injetar em run_loop).

    run_loop(ctx, executor_fn=fns["executor_fn"], critic_fn=fns["critic_fn"]).
    """
    def executor_fn(ctx: TaskContext, iteration: int, profile: ModelProfile) -> ExecutorProposal:
        return call_executor_llm_real(ctx, iteration, profile, api_key=api_key)

    def critic_fn(proposal: ExecutorProposal) -> CriticReview:
        return call_independent_critic_real(proposal, api_key=api_key)

    return {"executor_fn": executor_fn, "critic_fn": critic_fn}


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
    audit_path: "str | Path | None" = None,
) -> LoopResult:
    """Executa o loop plan→act→verify→critic até stop rule ou gate.

    Stop rules:
      success = tests_pass E acceptance_criteria_met E critic=accept.
      blocked = capacidade bloqueada OU estagnação (max_iterations).
    Gate N3: sem `human_confirmed`, retorna awaiting_dual_confirmation.
    Se `log_path` for informado, persiste auditoria via
    write_maintenance_entry() ao final do run.
    Se `audit_path` for informado, persiste 1 linha JSON por run
    (fonte do dashboard Flask — fase 2).
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
    result.task_id = ctx.task_id
    if audit_path is not None:
        append_run_jsonl(audit_path, result)
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
        f"  - task={result.task_id or 'n/a'} iterations={result.iterations} "
        f"level={result.level.name} profile={result.profile} "
        f"blocker={result.blocker_type.value if result.blocker_type else 'none'}\n"
    )
    payload = json.dumps(
        [r.model_dump(mode="json") for r in result.records], ensure_ascii=False, indent=2
    )
    block = f"{header}```json\n{payload}\n```\n"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(block)


def append_run_jsonl(path: "str | Path", result: LoopResult) -> None:
    """Append de 1 linha JSON por run (fonte do dashboard — fase 2).

    Formato JSONL: um LoopResult serializado por linha; linhas
    corrompidas são ignoradas na leitura (load_runs do dashboard).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result.model_dump(mode="json"), ensure_ascii=False) + "\n")


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
