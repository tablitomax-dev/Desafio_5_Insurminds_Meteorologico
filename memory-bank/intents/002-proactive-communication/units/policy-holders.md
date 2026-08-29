# Unit — policy-holders

> Intent: 002-proactive-communication | Stage: domain
> Status: `planned`

## Objetivo

Modelo do segurado e catálogo em memória: `PolicyHolder(id, name,
phone, geo_location, insurance_types: {RESIDENTIAL, AUTO, ...})` +
`PolicyHolderCatalog` (Protocol + impl in-memory).

## Fatia técnica

- Entity `PolicyHolder` + VO `InsuranceType` (enum) — domain
- Repository port `PolicyHolderRepository` + impl in-memory — application/infrastructure
- Seeds JSON: `data/policy_holders.json` (5–10 segurados fictícios com
  mix: residencial urbano, auto, litoral, rural) — soma realismo à demo