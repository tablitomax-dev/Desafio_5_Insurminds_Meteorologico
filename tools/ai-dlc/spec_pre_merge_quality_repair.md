# Spec Operacional Completa — Step `pre_merge_quality_repair`

## Objetivo

Definir, com precisão operacional suficiente para implementação robusta no Trae, um step de pré-merge responsável por validar, reparar e revalidar a qualidade de um Pull Request antes de qualquer merge. O step deve impedir merges com falhas de CI/quality, coordenar executor e crítico em loop controlado, manter rastreabilidade completa e produzir uma decisão final auditável: `approved_for_merge` ou `blocked`.[page:12]

O repositório analisado mostra um fluxo centrado em Pull Requests, gates explícitos de qualidade (`Lint`, `Type-check`, `Testes unitários`, `Build`) e, no estado atual observado, nenhum PR aberto, o que indica que a spec deve ser genérica, desacoplada do PR momentâneo e pronta para operação contínua.[page:12]

---

## Problema que este step resolve

Em muitos fluxos de PR, a validação de qualidade acontece de forma passiva: os checks falham, alguém corrige manualmente, e o merge é retomado sem um protocolo claro de análise, crítica, convergência e revalidação integral. Isso cria quatro riscos principais:

1. **Correção local e regressão global** — corrige-se um teste e quebra-se tipagem, build ou lint.
2. **Correção cosmética** — remove-se sintoma, não causa raiz.
3. **Merge prematuro** — PR recebe merge com estado parcialmente verde ou com evidência incompleta.
4. **Baixa auditabilidade** — não há trilha clara do que falhou, por que falhou, o que foi alterado e por que foi considerado aceitável.

O step `pre_merge_quality_repair` existe para transformar validação de qualidade em um processo determinístico, iterativo e auditável, com papel explícito para um crítico técnico independente.

---

## Princípios operacionais

1. **Nunca fazer merge com gate obrigatório em vermelho.**
2. **Sempre rerodar a suíte completa após qualquer correção.** Não rerodar apenas o check que falhou.
3. **Toda correção relevante deve ser revisada pelo crítico antes da decisão final.**
4. **Bloquear quando não houver convergência técnica.** Repetir indefinidamente é falha do sistema.
5. **Distinguir falha determinística de falha ambiental/flaky.** O tratamento é diferente.
6. **Separar claramente “corrigir” de “autorizar merge”.** O step não deve implicitamente fundir essas decisões.
7. **Toda decisão deve gerar evidência persistente.**
8. **Escopo mínimo de mudança.** Correções devem preservar intenção e evitar expansão indevida do diff.
9. **Base branch e stacked PRs devem ser tratados explicitamente.**
10. **Crítico não é ornamentação.** Ele deve ter poder real de vetar correções frágeis.

---

## Escopo

### Dentro do escopo

- Descobrir/checkar gates obrigatórios do PR.
- Rodar ou consultar status de `lint`, `type-check`, `test`, `build`.
- Coletar logs e artefatos diagnósticos.
- Classificar falhas por tipo e severidade.
- Propor correções.
- Submeter correções ao crítico.
- Aplicar patches na branch do PR.
- Reexecutar a suíte completa.
- Produzir decisão final: `approved_for_merge` ou `blocked`.
- Registrar trilha completa de execução.

### Fora do escopo

- Fazer o merge automaticamente sem step explícito posterior.
- Alterar política de branch protection.
- Reescrever o escopo funcional do PR sem autorização.
- Aprovar mudança arquitetural grande como “correção de CI” sem governança separada.

---

## Resultado esperado

Ao final, o sistema deve produzir um envelope de decisão contendo:

```json
{
  "step": "pre_merge_quality_repair",
  "status": "approved_for_merge",
  "pr_number": 7,
  "head_branch": "feature/002-collection-pipeline",
  "base_branch": "main",
  "attempt_count": 2,
  "checks": {
    "lint": "passed",
    "type_check": "passed",
    "unit_tests": "passed",
    "build": "passed"
  },
  "critic_final_verdict": "approved",
  "merge_recommendation": {
    "allowed": true,
    "strategy": "squash"
  }
}
```

Se houver bloqueio, o status deve ser `blocked` e incluir causa estruturada.

---

## Modelo mental correto

Este step não deve ser pensado como “rodar CI”. Ele é, na prática, uma **máquina de convergência de qualidade** com quatro capacidades:

1. **Observação** — ler estado do PR e dos checks.
2. **Diagnóstico** — transformar logs em hipóteses de causa raiz.
3. **Correção controlada** — mudar o mínimo necessário.
4. **Julgamento** — decidir se o estado final é realmente apto para merge.

Sem essas quatro capacidades explícitas, o sistema vira apenas um wrapper de CI.

---

## Arquitetura conceitual

Participantes:

- **PR Context Loader**: coleta dados do PR, branches, diff, checks esperados, conflitos, regras de merge.
- **Quality Runner**: executa ou consulta checks obrigatórios.
- **Failure Classifier**: classifica falhas por categoria, impacto e confiabilidade diagnóstica.
- **Repair Planner**: propõe plano mínimo de correção.
- **Executor**: aplica patch.
- **Critic**: revisa diagnóstico e patch.
- **Revalidation Runner**: reroda a suíte completa.
- **Decision Engine**: decide `approved_for_merge` vs `blocked`.
- **Audit Logger**: persiste tudo.

### Dependências lógicas

```text
PR Context -> Quality Runner -> Failure Classifier -> Repair Planner -> Critic
      -> Executor -> Revalidation Runner -> Decision Engine -> Audit Logger
```

---

## Máquina de estados

```text
idle
  -> prepare_context
  -> validate_quality
  -> classify_failures
  -> propose_repair
  -> critic_review
  -> apply_repair
  -> revalidate_all
  -> approved_for_merge
  -> blocked
```

### Estados detalhados

| Estado | Objetivo | Saída principal |
|---|---|---|
| `prepare_context` | Montar contexto operacional completo do PR | `pr_context` |
| `validate_quality` | Rodar/consultar checks obrigatórios | `quality_report` |
| `classify_failures` | Estruturar as falhas | `failure_report` |
| `propose_repair` | Definir patch mínimo | `repair_plan` |
| `critic_review` | Validar diagnóstico e patch | `critic_verdict` |
| `apply_repair` | Executar a correção | `applied_patch` |
| `revalidate_all` | Rerodar a suíte completa | `revalidation_report` |
| `approved_for_merge` | Liberar próximo step de merge | `merge_release` |
| `blocked` | Encerrar com falha explicada | `block_report` |

### Transições permitidas

- `prepare_context -> validate_quality`
- `validate_quality -> approved_for_merge` quando todos os gates obrigatórios estiverem verdes.
- `validate_quality -> classify_failures` quando qualquer gate obrigatório falhar.
- `classify_failures -> propose_repair`
- `propose_repair -> critic_review`
- `critic_review -> apply_repair` se `approved` ou `approved_with_conditions`.
- `critic_review -> propose_repair` se `rejected`.
- `apply_repair -> revalidate_all`
- `revalidate_all -> approved_for_merge` se suíte completa verde.
- `revalidate_all -> classify_failures` se qualquer gate obrigatório falhar.
- Qualquer estado crítico -> `blocked` em caso de erro operacional não recuperável.

### Transições proibidas

- `validate_quality -> apply_repair` sem classificação mínima.
- `apply_repair -> approved_for_merge` sem revalidação completa.
- `critic_review -> approved_for_merge` sem reexecução da suíte.
- `blocked -> approved_for_merge` sem nova execução do step.

---

## Contrato do step

```yaml
name: pre_merge_quality_repair
version: 1
purpose: >
  Garantir que nenhum PR siga para merge sem passar integralmente
  pelos gates obrigatórios de qualidade e sem revisão crítica das correções.

inputs:
  pr_number: integer
  repository: string
  head_branch: string
  base_branch: string
  expected_checks:
    type: array
    items: string
  merge_strategy:
    type: string
    allowed: [squash, merge, rebase]
  changed_files:
    type: array
    items: string
  branch_protection_rules:
    type: object
  max_attempts:
    type: integer
    default: 3
  retry_policy:
    type: object
  execution_mode:
    type: string
    allowed: [read_only_assess, repair_and_revalidate]

outputs:
  status:
    type: string
    allowed: [approved_for_merge, blocked]
  attempt_count: integer
  checks_report: object
  failure_report: object
  repair_history: array
  critic_history: array
  final_verdict: object
  audit_log_ref: string

invariants:
  - no_merge_when_required_check_failed
  - full_suite_rerun_after_any_change
  - critic_must_review_final_repair
  - all_decisions_must_be_logged
  - diff_scope_must_not_expand_without_explicit_justification
```

---

## Entradas obrigatórias e derivadas

### Entradas obrigatórias

- `repository`
- `pr_number`
- `head_branch`
- `base_branch`
- `expected_checks`
- `max_attempts`
- `execution_mode`

### Entradas derivadas

- `changed_files`
- `diff_stats`
- `has_merge_conflicts`
- `is_stacked_pr`
- `parent_pr_reference`
- `required_reviews`
- `branch_protection_snapshot`
- `latest_commit_sha`
- `check_run_urls`

### Regra importante

Se `expected_checks` não for informado, o step deve tentar inferir a partir de branch protection e histórico recente de CI. Se ainda assim houver ambiguidade, deve bloquear por falta de contrato explícito, não assumir silenciosamente.

---

## Saídas e artefatos

### Saída primária

```json
{
  "status": "approved_for_merge",
  "reason": "all_required_checks_green_after_repair_loop",
  "attempt_count": 2,
  "merge_recommendation": {
    "allowed": true,
    "strategy": "squash"
  }
}
```

### Artefatos persistidos

1. `pr_context.json`
2. `quality_report.initial.json`
3. `failure_report.attempt-N.json`
4. `repair_plan.attempt-N.json`
5. `critic_verdict.attempt-N.json`
6. `patch_summary.attempt-N.json`
7. `quality_report.revalidation.attempt-N.json`
8. `final_decision.json`
9. `execution_log.md`

---

## Classificação de falhas

A robustez depende muito mais da **classificação correta** do que da correção em si. O sistema deve distinguir pelo menos:

| Categoria | Exemplos | Tratamento padrão |
|---|---|---|
| `lint_format` | ruff, eslint, import order | corrigir automaticamente se seguro |
| `type_error` | mypy, pyright, tsc | corrigir com atenção a contratos |
| `unit_test_failure` | assertion, regression, contract mismatch | investigar causa raiz |
| `build_failure` | packaging, transpilation, asset pipeline | reparar e validar saída |
| `merge_conflict_residue` | marcadores de conflito, arquivos inconsistentes | correção prioritária |
| `flaky_test_suspected` | falha intermitente | confirmar por rerun controlado |
| `environmental` | rede, registry, timeout externo | classificar como não determinística |
| `policy_failure` | branch base errada, commit message rule, missing review | corrigir fluxo, não código |

### Severidade

- `S0`: bloqueio total de merge.
- `S1`: quebra de qualidade obrigatória.
- `S2`: problema não bloqueante, mas precisa registro.
- `S3`: observação ou melhoria.

### Confiabilidade diagnóstica

- `high`: log aponta causa clara.
- `medium`: sintomas fortes, causa provável.
- `low`: múltiplas hipóteses plausíveis.

O crítico deve aumentar o nível de exigência quando a confiabilidade diagnóstica for `low`.

---

## Política para flaky e ambiente

Um erro recorrente em automação é tratar falha intermitente como falha de produto, ou o oposto. A spec deve forçar distinção.

### Heurística mínima

Classificar como `flaky_test_suspected` apenas se:

- o mesmo commit já passou antes no mesmo teste; ou
- o erro não é determinístico; ou
- há assinatura típica de timeout/race/rede; ou
- rerun isolado muda o resultado sem mudança de código.

### Regra operacional

- Flaky suspeito não autoriza merge automaticamente.
- Exige rerun controlado e parecer do crítico.
- Se o teste continuar instável, o step retorna `blocked` com motivo `quality_signal_unreliable` ou abre exceção formal governada externamente.

---

## Loop principal de execução

```text
1. Preparar contexto do PR
2. Validar/checkar todos os gates obrigatórios
3. Se tudo verde -> approved_for_merge
4. Se houver falhas -> classificar
5. Gerar plano de correção mínimo
6. Submeter plano e evidências ao crítico
7. Se crítico rejeitar -> revisar plano
8. Se crítico aprovar -> aplicar patch
9. Rerodar suíte completa
10. Se tudo verde -> approved_for_merge
11. Se falhar novamente -> repetir até max_attempts
12. Se não convergir -> blocked
```

### Condições de parada

Parar com `blocked` quando:

- `attempt_count > max_attempts`
- o crítico rejeitar repetidamente por baixa qualidade da correção
- o diff sair do escopo original sem autorização
- houver falha ambiental persistente que torne o sinal de qualidade inconfiável
- houver conflito estrutural entre base branch e head branch

---

## Papel do Executor

O executor é responsável por transformar diagnóstico em mudança concreta.

### Obrigações

- Ler logs completos.
- Isolar a causa mais provável.
- Propor patch mínimo.
- Explicar por que a mudança resolve o problema.
- Listar riscos da correção.
- Aplicar somente mudanças justificadas.
- Reexecutar a suíte completa.
- Não “silenciar” erro sem explicar o trade-off.

### Antipadrões do executor

- Desabilitar teste sem governança.
- Relaxar type-check sem justificativa.
- Inserir `# noqa`, `type: ignore` ou equivalente como resposta default.
- Corrigir build alterando escopo funcional do PR.
- Fazer patch grande quando um patch focal resolveria.

---

## Papel do Crítico

O crítico precisa ser verdadeiramente independente da primeira solução proposta.

### Perguntas que o crítico deve responder

1. A falha foi corretamente classificada?
2. A causa raiz está suficientemente demonstrada?
3. O patch resolve a causa raiz ou só o sintoma?
4. O patch amplia o diff além do necessário?
5. Existe regressão provável em contratos, API, tipagem ou build?
6. Há forma menor, mais segura ou mais reversível de corrigir?
7. A correção está alinhada à arquitetura do repositório?
8. A mudança deveria virar ADR/refactor separado em vez de “fix de CI”?

### Veredictos possíveis

```json
{
  "verdict": "approved | approved_with_conditions | rejected",
  "confidence": "high | medium | low",
  "reasoning_summary": "string",
  "required_changes": ["..."],
  "risk_flags": ["..."]
}
```

### Regra crítica

Se o crítico marcar `rejected`, o patch não pode ser aplicado.

---

## Decisão de merge

A decisão final não deve ser um booleano simples. Deve conter justificação estruturada.

```json
{
  "allowed": true,
  "strategy": "squash",
  "basis": [
    "all_required_checks_green",
    "critic_approved_final_patch",
    "no_merge_conflicts_detected",
    "diff_scope_within_expected_bounds"
  ],
  "warnings": []
}
```

### Critérios mínimos para `allowed: true`

- Todos os checks obrigatórios verdes.
- Nenhum conflito de merge pendente.
- Crítico aprovou a última correção relevante.
- Branch base correta ou explicitamente aceita para stacked PR.
- Sem evidência de instabilidade não resolvida.
- Audit log persistido com sucesso.

---

## Tratamento de stacked PRs

Isso é especialmente importante no contexto descrito anteriormente para bolts empilhados.

### Campos adicionais

```json
{
  "is_stacked_pr": true,
  "parent_branch": "feature/002-domain-core",
  "expected_future_base": "main",
  "requires_post_parent_merge_revalidation": true
}
```

### Regras

1. Um PR filho pode ser validado contra a branch pai atual.
2. Após merge do PR pai, o PR filho deve ser **revalidado** contra a nova base.
3. O step deve distinguir:
   - `approved_against_parent_branch`
   - `approved_for_final_merge_to_main`
4. Nunca assumir que o diff permanece correto após retarget automático.

### Motivo

Quando PRs estão empilhados, um diff aparentemente verde pode esconder dependência indevida ou duplicação de mudanças já integradas.

---

## Observabilidade e trilha de auditoria

Cada execução precisa deixar rastros suficientes para responder depois:

- O que falhou?
- Em qual commit?
- Qual foi a hipótese de causa raiz?
- Quem aprovou a correção?
- O que mudou no patch?
- Qual suíte rodou depois?
- Por que o merge foi liberado ou bloqueado?

### Estrutura de log sugerida

```json
{
  "run_id": "pmqr-2026-09-03T22:00:00Z-0007",
  "repository": "tablitomax-dev/Desafio_5_Insurminds_Meteorologico",
  "pr_number": 7,
  "state_transitions": [
    {"from": "prepare_context", "to": "validate_quality", "at": "..."},
    {"from": "validate_quality", "to": "classify_failures", "at": "..."}
  ],
  "attempts": [
    {
      "attempt": 1,
      "failed_checks": ["lint", "type_check"],
      "critic_verdict": "approved_with_conditions",
      "patch_files": ["app/pipeline.py", "tests/test_cli.py"],
      "revalidation": {
        "lint": "passed",
        "type_check": "passed",
        "unit_tests": "failed",
        "build": "passed"
      }
    }
  ],
  "final_status": "approved_for_merge"
}
```

---

## Idempotência e retomada

A implementação robusta no Trae precisa ser retomável.

### Requisitos

- Mesmo `run_id` deve poder retomar do último estado consistente.
- Patches não devem ser reaplicados sem checagem de SHA/diff.
- Reexecuções devem detectar se a branch já mudou desde a última tentativa.
- Se o commit SHA mudar fora do step, a execução deve invalidar contexto anterior e reiniciar a partir de `prepare_context`.

### Regras de consistência

- Toda tentativa é vinculada a um `head_sha`.
- `critic_verdict` vale apenas para o patch daquele `head_sha`.
- Mudou o SHA, mudou o contexto de verdade.

---

## Timeouts, retries e budget de execução

Uma spec robusta precisa declarar limites. Sem limites, o step vira fonte de custo e loop infinito.

### Sugestão

```yaml
limits:
  max_attempts: 3
  max_total_runtime_minutes: 45
  max_single_check_runtime_minutes: 15
  max_repair_diff_files_without_escalation: 10
  max_repair_diff_lines_without_escalation: 300
```

### Política

- Retry automático para falha de rede/infra: até 2 vezes.
- Sem retry automático para falha determinística de código.
- Se patch exceder limites de diff, exigir escalonamento ou aprovação humana.

---

## Segurança e governança

### Regras mínimas

- Não vazar segredos nos logs.
- Sanitizar paths e comandos.
- Não executar comandos destrutivos fora da branch do PR.
- Não fazer push forçado como comportamento padrão.
- Não editar arquivos fora do escopo do repositório/PR sem justificativa explícita.
- Registrar qualquer uso de bypass ou override como evento de governança.

### Overrides excepcionais

Casos como “merge mesmo com flaky conhecido” devem existir apenas por mecanismo separado:

```json
{
  "override_requested": true,
  "override_reason": "known_flaky_test_with_external_approval",
  "approved_by": "human",
  "expires_at": "2026-09-10T00:00:00Z"
}
```

O step em si não deve inventar override.

---

## Estrutura de dados recomendada

### `pr_context.json`

```json
{
  "repository": "tablitomax-dev/Desafio_5_Insurminds_Meteorologico",
  "pr_number": 7,
  "head_branch": "feature/002-collection-pipeline",
  "base_branch": "main",
  "head_sha": "abc123",
  "is_stacked_pr": false,
  "changed_files": [
    "app/pipeline.py",
    "tests/test_pipeline.py"
  ],
  "expected_checks": ["lint", "type_check", "unit_tests", "build"],
  "has_merge_conflicts": false
}
```

### `failure_report.attempt-N.json`

```json
{
  "attempt": 1,
  "head_sha": "abc123",
  "failed_checks": [
    {
      "name": "type_check",
      "category": "type_error",
      "severity": "S1",
      "diagnostic_confidence": "high",
      "summary": "Argument type mismatch in pipeline orchestration",
      "evidence": ["mypy output line 42", "changed contract in app/pipeline.py"]
    }
  ],
  "global_assessment": "single_root_cause_likely"
}
```

### `repair_plan.attempt-N.json`

```json
{
  "attempt": 1,
  "strategy": "minimal_contract_alignment",
  "target_files": ["app/pipeline.py", "tests/test_pipeline.py"],
  "planned_changes": [
    "align function signature with declared protocol",
    "update unit test fixture to match contract"
  ],
  "risks": [
    "possible regression in CLI integration if protocol assumptions are stale"
  ]
}
```

### `final_decision.json`

```json
{
  "status": "approved_for_merge",
  "attempt_count": 2,
  "head_sha": "def456",
  "checks": {
    "lint": "passed",
    "type_check": "passed",
    "unit_tests": "passed",
    "build": "passed"
  },
  "critic_final_verdict": "approved",
  "merge_recommendation": {
    "allowed": true,
    "strategy": "squash"
  }
}
```

---

## Prompting e contexto para o Trae

A implementação será muito melhor se o Trae receber contexto operacional explícito, e não só um pedido genérico como “faça um step que resolve CI”. Abaixo está o contexto recomendado.

## Contexto completo para implementação no Trae

### Contexto executivo

O sistema precisa implementar um step chamado `pre_merge_quality_repair` para o pipeline de Pull Requests. Esse step existe para impedir merges prematuros e criar um loop de convergência de qualidade antes do merge. Ele deve operar sobre PRs potencialmente normais ou stacked, consultar/rodar checks obrigatórios de qualidade, classificar falhas, coordenar um executor e um crítico, aplicar correções mínimas na branch do PR, rerodar a suíte completa e emitir decisão auditável de liberação ou bloqueio.

Não é um “wrapper de CI” e não deve ser tratado como um job linear simples. Trata-se de uma máquina de estados com persistência, retomada, limites de tentativa, trilha de auditoria, distinção entre falha determinística e falha ambiental, e regras explícitas para decisão final de merge.

### Contexto de domínio

O repositório trabalha com Pull Requests, quality gates explícitos (`Lint`, `Type-check`, `Testes unitários`, `Build`) e uso de stacked PRs em alguns fluxos de desenvolvimento. Portanto, a implementação precisa suportar:

- PR comum com base em `main`
- PR empilhado sobre branch pai temporária
- retarget após merge do pai
- revalidação integral após mudança de base

### Objetivos funcionais

1. Carregar contexto completo do PR.
2. Descobrir ou validar checks obrigatórios.
3. Obter estado inicial de qualidade.
4. Se tudo estiver verde, emitir `approved_for_merge`.
5. Se houver falhas, classificá-las.
6. Gerar plano mínimo de correção.
7. Submeter plano e patch ao crítico.
8. Aplicar correção apenas se o crítico aprovar.
9. Rerodar a suíte completa.
10. Repetir até convergir ou bloquear.
11. Persistir artefatos estruturados de cada tentativa.

### Requisitos não funcionais

- Determinismo operacional.
- Idempotência e retomada por `run_id`.
- Auditabilidade forte.
- Limite de custo e tentativas.
- Segurança de execução.
- Separação clara entre correção e autorização de merge.
- Baixo acoplamento a um CI específico.

### Requisitos arquiteturais

Implementar preferencialmente como componentes desacoplados:

- `PRContextService`
- `QualityCheckService`
- `FailureClassifier`
- `RepairPlanner`
- `CriticService`
- `PatchApplier`
- `RevalidationService`
- `DecisionService`
- `AuditRepository`
- `StateMachine`

Evitar um arquivo monolítico “god object” que faça tudo.

### Contratos recomendados entre componentes

```ts
interface PRContext {
  repository: string;
  prNumber: number;
  headBranch: string;
  baseBranch: string;
  headSha: string;
  changedFiles: string[];
  expectedChecks: string[];
  hasMergeConflicts: boolean;
  isStackedPR: boolean;
  parentBranch?: string;
}

interface QualityReport {
  headSha: string;
  checks: Record<string, "passed" | "failed" | "pending" | "skipped">;
  failingDetails: FailedCheck[];
  allRequiredGreen: boolean;
}

interface FailedCheck {
  name: string;
  category: string;
  severity: "S0" | "S1" | "S2" | "S3";
  diagnosticConfidence: "high" | "medium" | "low";
  summary: string;
  evidence: string[];
}

interface CriticVerdict {
  verdict: "approved" | "approved_with_conditions" | "rejected";
  confidence: "high" | "medium" | "low";
  requiredChanges: string[];
  riskFlags: string[];
}
```

### Invariantes que o Trae deve respeitar

- Nunca autorizar merge com check obrigatório falho.
- Nunca aplicar patch aprovado para um SHA diferente daquele revisado.
- Sempre rerodar a suíte completa após patch.
- Nunca pular o crítico na correção final.
- Nunca tratar stacked PR como PR simples sem checagem da base.
- Nunca assumir que falta de dados significa sucesso.

### Antipadrões que o Trae deve evitar

- Job linear com `if failed then fix then merge` sem state machine.
- Retry infinito sem bloqueio por não convergência.
- Correção automática sem trilha de decisão.
- Uso de bypass silencioso para flaky/infra.
- Falta de separação entre consulta de checks e decisão de merge.
- Acoplamento rígido a nomes de jobs específicos quando eles deveriam ser configuráveis.

### Estrutura sugerida de persistência

- Um diretório por `run_id`
- JSONs estruturados por tentativa
- Log markdown legível por humano
- Índice resumido para dashboards

Exemplo:

```text
runs/pre-merge-quality-repair/
  pmqr-2026-09-03T22-00-00Z-0007/
    pr_context.json
    quality_report.initial.json
    attempt-1.failure_report.json
    attempt-1.repair_plan.json
    attempt-1.critic_verdict.json
    attempt-1.patch_summary.json
    attempt-1.revalidation.json
    final_decision.json
    execution_log.md
```

### Estratégia de implementação incremental

Fase 1:
- leitura de contexto do PR
- leitura/execução de checks
- decisão read-only `approved_for_merge` vs `blocked`

Fase 2:
- classificador de falhas
- planejador de reparo
- crítico
- aplicação de patch

Fase 3:
- retomada/idempotência
- suporte pleno a stacked PRs
- observabilidade avançada
- políticas refinadas para flaky/infra

### Estratégia de testes

O Trae deve implementar testes em camadas.

#### Unitários

- classificação de falhas
- transições da state machine
- decisão final
- política de retries
- validação de invariantes

#### Integração

- PR verde desde o início
- PR com lint falhando e convergência em 1 tentativa
- PR com type-check + teste falhando e convergência em 2 tentativas
- PR com flaky suspeito e bloqueio
- PR stacked que precisa revalidação após retarget
- mudança externa de SHA durante a execução

#### Testes de contrato

- schema dos JSONs de artefato
- compatibilidade entre `CriticService`, `RepairPlanner` e `DecisionService`

### Critérios de aceite

A implementação só deve ser considerada pronta quando:

1. Exista state machine explícita.
2. Haja persistência de artefatos por tentativa.
3. O sistema rerode a suíte completa após patch.
4. O crítico participe formalmente do loop.
5. O sistema bloqueie por não convergência.
6. O sistema trate stacked PRs explicitamente.
7. Haja testes cobrindo sucesso, falha, flaky e retomada.
8. A decisão final seja estruturada e auditável.

---

## Análise crítica da própria proposta

Antes de implementar, é importante criticar esta própria spec.

### Risco 1: excesso de complexidade

A spec é deliberadamente robusta. Isso melhora confiabilidade, mas aumenta custo de implementação. Mitigação: construir em fases e começar com modo `read_only_assess` + state machine mínima.

### Risco 2: crítico virar gargalo burocrático

Se o crítico for sempre síncrono e detalhista em excesso, o fluxo pode ficar lento. Mitigação: limitar criticidade obrigatória a patches relevantes e permitir `approved_with_conditions` em correções pequenas e bem justificadas.

### Risco 3: classificador de falhas simplista

Se a classificação for fraca, todo o restante degrada. Mitigação: separar classificação, confiança diagnóstica e política de retry; não usar uma taxonomia rasa demais.

### Risco 4: stacked PRs mal modelados

Esse é um ponto onde muita automação quebra. Mitigação: modelar estados `approved_against_parent_branch` e revalidação obrigatória após retarget.

### Risco 5: custo operacional alto

Rerodar suíte completa a cada patch custa tempo e dinheiro. Ainda assim, esse custo é defensável porque reduz risco de regressão oculta. Mitigação: permitir seleção de suíte “obrigatória completa” e otimizações internas, sem quebrar a invariante lógica de revalidação global.

### Risco 6: falsa sensação de segurança

Mesmo com tudo verde, pode haver bugs sem cobertura. Mitigação: deixar claro que o step garante qualidade de gate, não perfeição funcional absoluta.

---

## Recomendação final de implementação

A implementação robusta no Trae deve começar com uma state machine explícita, contratos tipados, persistência por `run_id` e separação rígida entre contexto, validação, correção, crítica, revalidação e decisão. O maior erro seria tentar “entregar rápido” com um job linear acoplado ao CI atual, porque isso criaria dívida técnica exatamente no mecanismo que deveria proteger a qualidade do repositório.[page:12]

A prioridade correta é: primeiro a arquitetura do step, depois a integração com o provedor de CI, depois a sofisticação do reparo automático. Em outras palavras, é melhor um sistema inicialmente mais conservador e auditável do que um “auto-fixer” agressivo que faça merge com confiança artificial.[page:12]

---

## Implementação neste repositório (status 2026-09-03)

Adotada como fonte conceitual do step no repo `Desafio_5_Insurminds_Meteorologico`.
Estado: **Fase 1 implementada** (`read_only_assess`) — bolt 001-pre-merge-quality-repair do
intent `001-repository-quality-foundation`.

- **Step Fase 1**: `tools/ai-dlc/pre_merge_check.py` — máquina de estados mínima
  (`prepare_context -> validate_quality -> decide`), checks locais canônicos
  (`ruff check .`, `mypy app`, `pytest`), classificação por categoria/severidade
  e decisão auditável `approved_for_merge` | `blocked` (exit 0/1).
- **Artefatos por `run_id`**: `tools/ai-dlc/runs/pre-merge-quality-repair/<run_id>/`
  (`pr_context.json`, `quality_report.initial.json`, `failure_report.attempt-1.json`
  quando bloqueado, `final_decision.json`, `execution_log.md`) — local, não
  versionado (mesmo padrão do `runs.jsonl`).
- **Fonte da verdade dos checks**: o gate canônico do repo
  (`.github/workflows/ci.yml` + `ruff.toml`), executado localmente — enquanto
  `expected_checks` não existir como checks na plataforma, a execução local é a fonte.
- **Sem loop de reparo** nesta fase: nenhum patch é aplicado; o step observa,
  classifica e decide. Fases 2/3 (repair loop completo, retomada total, flaky
  refinado) ficam para bolts futuros, reusando o padrão executor→crítico de
  `ai_dlc_orchestrator.py`/`run_bolt.py`.

Uso:

```bash
python tools/ai-dlc/pre_merge_check.py --base origin/main
# exit 0 = approved_for_merge | exit 1 = blocked
```
