# Root Story Index Placeholder (Modo per-intent)

> **NOTA**: Desde ADR-002, `story-index.mode=per-intent` (ver
> `.specsmd/aidlc/memory-bank.yaml` — fonte local do specsmd, não-versionada).
>
> - **Fonte canônica de metadados GLOBAIS**: `_index.csv` por diretório.
>   - Intents: [intents/_index.csv](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/intents/_index.csv)
>   - Bolts: [bolts/_index.csv](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/bolts/_index.csv)
>   - Operations: [operations/_index.csv](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/operations/_index.csv)
>   - Standards: [standards/_index.csv](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/_index.csv)
> - **Fonte canônica por Intent**: `memory-bank/intents/{NNN}-{intent}/story-index.md` (criado automaticamente no Inception).
> - **Índice invertido keyword → artefatos**: [standards/keyword-index.md](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/standards/keyword-index.md)

## Status Atual

**Intent 002-proactive-communication: `done`** (7/7 stories; PRs #6/#7/#11
squash mergeados em `main`, CI verde). Ver
[intents/002-proactive-communication/story-index.md](file:///c:/Users/pbena/Documents/Cursos/Insurminds/Desafio_5_Insurminds_Meteorologico/memory-bank/intents/002-proactive-communication/story-index.md)

Intent 001-repository-quality-foundation segue `active` apenas por dívidas
de governança opcional (branch protection formal na UI, compactação de bolts).

## Próximo Passo

Para começar a fase de **Inception**, diga ao Master Agent:
> *"Crie um intent {nome-desafio} para {capacidade}"* — ex: *"Crie intent 001-meteorologico-mvp para alertas meteorológicos"*.
