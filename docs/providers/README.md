# Provider Evaluations

Provider evaluations record official-source review, technical fit, entitlement assumptions, licensing boundaries, and implementation status for candidate market-data providers.

## Records

- [Massive Stocks Basic Evaluation](massive-stocks-basic-evaluation.md): Accepted first private EOD development provider.
- [Massive Adapter Boundary](massive-adapter-boundary.md): Adapter configuration, credential loader, HTTPS transport, smoke-test, and mocked mapping boundary.
- [Historical Research Source Capability V1](historical-research-source-capability-v1.md): Evidence-scoped capability and gap matrix for the future point-in-time research foundation.
- [2026-08-28 Massive Historical Research Review](massive-historical-research-review-2026-08-28.md): Official public plan/endpoint/terms review and provider-pilot blockers.

## Rules

- Provider evaluations must link official sources.
- Account credentials, account identifiers, API keys, tokens, and private entitlement details must not be stored in Git.
- Evaluation does not imply account entitlement, public display permission, redistribution permission, real API access, ingestion, or deployment.
- A successful smoke test verifies authentication and reference entitlement only; it does not imply ingestion, persistence, redistribution rights, or public display permission.
