# Provider Evaluations

Provider evaluations record official-source review, technical fit, entitlement assumptions, licensing boundaries, and implementation status for candidate market-data providers.

## Records

- [Massive Stocks Basic Evaluation](massive-stocks-basic-evaluation.md):
  historical acceptance of the first private EOD tier; Stocks Starter is now
  owner-confirmed and current evidence belongs in
  [current context](../project/current-context.md).
- [Massive Adapter Boundary](massive-adapter-boundary.md): Adapter configuration, credential loader, HTTPS transport, smoke-test, and mocked mapping boundary.
- [Historical Research Source Capability V1](historical-research-source-capability-v1.md): Evidence-scoped capability and gap matrix for the future point-in-time research foundation.
- [2026-08-28 Massive Historical Research Review](massive-historical-research-review-2026-08-28.md): Official public plan/endpoint/terms review and provider-pilot blockers.
- [2026-08-28 Equal-Capability Historical Source Review](equal-capability-historical-source-review-2026-08-28.md): Official SEC, exchange, open-identifier, and representative market-data source compatibility review.
- [2026-09-08 Lifecycle Corroboration Source Review](lifecycle-corroboration-source-review-2026-09-08.md): Official cross-venue and exchange-source comparison, deterministic 30-item diagnostic, and sample-before-adapter gate.
- [2026-09-08 Sector / Industry Source Review](sector-industry-source-review-2026-09-08.md): Repository and official-source audit separating current display from point-in-time research classification; GICS History is the first sample candidate, not a selected source.
- [2026-09-09 Massive Current-Session Access Probe](../audits/massive-current-session-access-probe-2026-09-09.md): Credential-safe historical/current-date comparison that isolates the current-account recency boundary without retaining provider responses or writing data.

## Rules

- Provider evaluations must link official sources.
- Account credentials, account identifiers, API keys, tokens, and private entitlement details must not be stored in Git.
- Evaluation does not imply account entitlement, public display permission, redistribution permission, real API access, ingestion, or deployment.
- A successful smoke test verifies authentication and reference entitlement only; it does not imply ingestion, persistence, redistribution rights, or public display permission.
