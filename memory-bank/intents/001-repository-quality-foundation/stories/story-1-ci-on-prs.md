# Story — story-1-ci-on-prs

> Intent: 001-repository-quality-foundation | Unit: ci-and-merge-governance
> Status: `done` (implementação na branch, gate ativa com merge) | Prioridade: P0

## História

Como desenvolvedor, quero que todo PR para `main` execute uma validação
automática, para não depender apenas de revisão manual.

## Critérios de aceite (Given/When/Then)

- **Given** um PR aberto para `main`, **when** qualquer push na branch,
  **then** o workflow `CI / quality` roda e aparece no PR.
- **Given** o job concluído com sucesso, **then** há execução verde em
  GitHub Actions.
- **Given** o check publicado numa execução, **when** o humano o marcar
  como required, **then** PR sem check verde não pode ser mergeado.

## Notas

`npm ci` valida instalação reproduzível; lint/test/build são
`--if-present` no bootstrap (não há scripts ainda — honestidade de gate
documentada no workflow).