---
name: "revisao-critica"
description: "Crítica estruturada de solicitudes, arquitecturas y ADRs antes de implementar. Invocar cuando el usuario pida implementar/planear/arquitectar/refactorar, presente un ddd-02, o pida revisar ADR/design."
---

# Revisão Crítica

Skill de revisão crítica estruturada de solicitudes, arquitecturas e ADRs, antes de qualquer implementación.

## Idioma
- Responder SEMPRE em pt-BR. Nunca em outro idioma.

## Invocación (CONFLITO E — respeta Opción A)
- Esta skill es invocada por el **Master Agent (Opción A)** cuando detecta que el usuario pide implementar, planear, arquitectar, refactorar o elegir entre abordajes.
- También puede ser invocada explícitamente por el usuario con "revisar ADR" o "revisión de design".
- **NUNCA se auto-invoca. NUNCA bypasea al Master Agent.**

## Cuándo disparar
- Cuando el usuario pida implementar, planear, arquitectar, refactorar o elegir entre abordajes de código.
- Cuando el usuario presente un ddd-02 (technical design) o arquitectura completa para validación.
- Cuando el usuario pida explícitamente "revisar ADR" o "revisión de design".

## Cuándo NO disparar
- Correcciones triviales (typo, rename, formateo, cambio de una línea).
- Preguntas conceptuales sin intención de implementación.
- Continuación de trabajo ya analizado y aprobado en esta sesión.

## Modos de operación

### Modo leve (tareas pequeñas y reversibles)
- 1 párrafo por sección.
- 1 alternativa principal + 1 alternativa secundaria.
- Prosigue tras el análisis, sin gate.

### Modo design review (arquitectura completa o ddd-02)

1. **VALIDAR GATE ADR (CONFLICTO A — DELEGAR, NO REIMPLEMENTAR)**
   - **NO reimplementar el gate ADR.** El gate es determinístico y vive en `artifact-validator.cjs` (suite 5). Esta skill NO decide si el gate pasa.
   - Ejecutar (o pedir que se ejecute) `node .specsmd/aidlc/scripts/artifact-validator.cjs` para confirmar que el ddd-02 cumple el gate.
   - Si el validator reporta error `adr-gate.required-missing-reference` → informar al usuario que el ADR es obligatorio y **NO proseguir** hasta que Construction cree/linkee el ADR.
   - Si el validator pasa → cargar el ADR referenciado y revisar su contenido.

2. **REVISAR EL ADR (no recriar)**
   - Alternatives Considered: ¿las alternativas tienen sentido? ¿Falta alguna relevante?
   - Tradeoffs (Consequences → Negative): ¿los tradeoffs asumidos están explícitos y realistas?
   - Riesgos + mitigación: ¿están cubiertos? ¿Falta alguno crítico?
   - Rationale: ¿la justificación es sólida o hay premisas no validadas?

3. **CHECKLIST DE DIMENSIONES (score 1–5 + justificación)**
   - Corrección/adecuación al problema
   - Seguridad
   - Performance/escalabilidad
   - Mantenibilidad/evolucionabilidad
   - Costo (tokens/infra/op)
   - Operación/observabilidad

4. **TRADEOFFS EXPLÍCITOS**
   - Qué se gana, qué se pierde, dónde duele.

5. **ALTERNATIVAS CONSIDERADAS (mín. 2, con tradeoffs en tabla)**

6. **RECOMENDACIÓN GO/NO-GO + CONDICIONES DE INVALIDACIÓN**
   - "Mi recomendación estaría errada si..."

7. **ADR AUSENTE (CONFLICTO B — RECOMENDAR, NO CREAR)**
   - Si el validator reporta que falta ADR, esta skill **NO crea el ADR**.
   - Emite recomendación: "Falta ADR para esta decisión. Construction debe crearlo antes de implementar." (ownership de Construction).
   - No invadir `decision-index`.

## Gate (CONFLICTO F — SÓLO DETERMINÍSTICO)
- El ÚNICO gate que bloquea es el determinístico del validator (ADR ausente).
- El score de dimensiones (seguridad, performance, costo) es **CONSULTIVO**: si score < 3, se recomienda NO-GO, pero **NO bloquea por sí solo**.
- Nunca mezclar gate subjetivo (LLM) con gate determinístico (validator).

## Cache + Budget (CONFLICTOS C y D — OPT-13 + context-budget)
- Esta skill DEBE respetar el `fixed_load_order` de `context-budget.yaml` (OPT-13):
  1. `.specsmd/aidlc/memory-bank.yaml`
  2. `memory-bank/standards/context-budget.yaml`
  3. `memory-bank/standards/decision-index.md`
  4. `memory-bank/standards/keyword-index.md`
  5. `memory-bank/{dir}/_index.csv`
  6. **CONTENIDO VARIABLE POR ÚLTIMO** (ddd-02, ADR)
- NUNCA intercalar contenido variable en medio del prefijo estable (rompe cache).
- Nivel de profundidad: **STANDARD** por defecto. **DEEP** solo con confirmación.
- Respetar los 3 niveles de warning (80% 🟡 / 90% 🟠 / 95% 🔴) de `context-budget.yaml`.

## Formato de salida (modo design review)
Secciones fijas:
1. Validación del Gate ADR (resultado del validator, no juicio propio)
2. Revisión del ADR (alternativas, tradeoffs, riesgos, rationale)
3. Checklist de Dimensiones (tabla con score + justificación)
4. Tradeoffs Explícitos
5. Alternativas Consideradas (tabla)
6. Recomendación Go/No-Go + Condiciones de Invalidación
7. ADR Ausente (recomendación a Construction, si aplica)

## HARD RULES
- Prohibida crítica genérica: toda reserva debe citar riesgo concreto y verificable.
- Autocrítica obligatoria: declarar dónde la propia análisis puede estar errada, **CON EJEMPLO CONCRETO** (no "puedo estar errado" genérico).
- Proporcionalidad: usar modo leve para tareas pequeñas, modo design review para ddd-02 y decisiones arquitecturales.
- No recriar ADR si ya existe: revisar lo que está, apuntar fallas, sugerir mejoras.
- No crear ADR: recomendar su creación a Construction.

## Evals sugeridos
1. Pedido ambiguo ("faz um sistema de login") → debe preguntar antes de codar.
2. Pedido trivial ("corrige esse typo") → NO debe disparar análisis completa.
3. Pedido con solución mala embebida ("senha em texto puro no banco") → debe criticar la solicitud del usuario.
4. Elección de abordaje ("REST ou fila?") → debe comparar alternativas en tabla con trade-offs.
5. ddd-02 con `adr_required: true` y `adr_reference` vacío → DEBE delegar en el validator, reportar el error y NO proseguir (no reimplementar el gate).
6. ddd-02 con ADR válido → debe revisar el ADR (no recriar), generar checklist de dimensiones y recomendación go/no-go.