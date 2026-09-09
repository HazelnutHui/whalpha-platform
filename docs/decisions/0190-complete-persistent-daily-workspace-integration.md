# ADR 0190: Complete Persistent Daily Workspace Integration

## Status

Accepted

## Date

2026-09-09

## Context

The first live Stocks Starter daily chain retained Identity evidence in the
new session workspace and then exposed three integration defects:

- Identity and EOD used the same `acquisition-package` and
  `canonical-apply-plan.json` slots, so preserving the Identity evidence left
  no new target for EOD;
- the offline runner correctly created persistent Market Intelligence and
  Snapshot plans, but the coordinator Apply custody still accepted only a
  direct `/tmp` plan; and
- the Membership sidecar replanned after a completed action using the run
  start time, which could precede the newly created candidate's evaluation
  time and produce a false knowledge-time rejection.

The production data and website remained safe: all failed coordinator
attempts stopped before their write reservation, and the existing exact-plan
direct publication entry points completed the 2026-09-09 chain.

## Decision

Amend ADR 0181's persistent data layout so Identity and EOD have distinct
same-session artifact pairs:

```text
identity-acquisition-package
identity-canonical-apply-plan.json
eod-acquisition-package
eod-canonical-apply-plan.json
```

Keep the original generic pair and direct `/tmp` pair as compatibility inputs,
but never mix roles, custody modes, or sessions. The deterministic workspace
layout exposes both new pairs and advances to 1.2.

Allow Market Intelligence and Snapshot Apply custody to accept their exact
governed persistent same-session plan names as well as the legacy direct
`/tmp` form. Existing SHA-256, logical fingerprint, current-state,
freshness, target-absence, journal reservation, and post-state checks remain
unchanged.

Replan Membership after a workspace action using the action completion time.
This timestamp may advance validation knowledge; it does not change the
candidate's own evaluation or assessment timestamp.

## Consequences

- Daily Identity and EOD evidence can coexist without deletion or temporary
  compatibility paths.
- The coordinator can consume the exact persistent MI and Snapshot plans
  produced by the bounded offline runner.
- A successful Membership candidate no longer becomes falsely invalid solely
  because post-action planning used an earlier clock value.
- Existing historical `/tmp` and generic persistent evidence remains readable.
- No provider request, canonical write, publication, deployment, scheduler
  enablement, formula, Universe, or research-readiness claim follows from this
  decision.

## Alternatives Considered

### Delete Identity evidence before EOD

Rejected because it destroys useful lineage and makes interruption recovery
ambiguous.

### Continue translating every persistent plan through `/tmp`

Rejected because two physical approval plans for one logical publication add
avoidable custody and operator risk.

### Relax all workspace path validation

Rejected. Only exact role names in the existing owner-only session layout are
admitted; arbitrary persistent paths remain invalid.
