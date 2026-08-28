# Source Resolution Governance V1

## Status

Implemented as provider-neutral immutable contracts and a pure fingerprint
resolver with synthetic tests. No real source policy has been selected or
activated, and no provider, credential, `/data`, publication, deployment, or
scheduler state changed.

## Boundary

This contract answers one narrow question: when permission-cleared normalized
evidence describes the same stable-ID fact, is there enough agreement to
select its fingerprint? It does not acquire, normalize, persist, or publish the
fact body.

Each `DataFamilySourceResolutionPolicyV1` binds one standard data family and
one exact fact scope. Its ordered sources have one evidence role and the exact
`SourcePermissionReviewV1` fingerprint reviewed for that source.

| Mode | Required structure | Resolution rule |
| --- | --- | --- |
| `single_authority` | Exactly one authoritative source | Authority must be usable; any supplied resolving contradiction quarantines. |
| `primary_with_corroboration` | One primary and at least one corroborator | Primary and the configured number of sources must agree; any disagreement quarantines. |
| `unanimous_evidence` | At least two peer corroborators | Every resolving source must be usable and agree. |

`crosswalk_only` evidence can help a separate identity workflow, but it is
always excluded from fact resolution. `rejected` and `pending_review` evidence
is also excluded. Warning-quality evidence remains visible and may participate
only under the already approved exact source policy.

## Outcomes

- `resolved`: one configured source established the fact.
- `corroborated`: two or more configured sources established the same fact.
- `quarantined_conflict`: usable resolving evidence disagreed; no fact selected.
- `unavailable`: the required anchor or matching evidence was absent; no fact selected.

All decisions carry the policy fingerprint, stable subject, effective time,
supporting, conflicting, and excluded source IDs, and reason codes. A selected
fact fingerprint exists only for resolved or corroborated decisions.

## Fixed safety rules

- `first_non_null_allowed` is always false.
- `ticker_join_allowed` is always false.
- Conflict action is always quarantine; missing required evidence is unavailable.
- Evidence must match the policy family, fact scope, stable subject, effective
  time, source, and permission-review fingerprint.
- One source may contribute only one normalized fact revision to one decision.
- Resolution has `operational_authority=none`.

## Public import path

```python
from tip_api.contracts.data_governance.v1 import (
    DataFamilySourceResolutionPolicyV1,
    SourceFactEvidenceV1,
    resolve_source_facts,
)
```

See [ADR 0055](../decisions/0055-resolve-canonical-facts-by-family-specific-source-policy.md)
and [Source Permission Governance V1](source-permission-governance-v1.md).
