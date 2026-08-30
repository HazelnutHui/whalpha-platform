# Source Permission Governance V1

## Status

Implemented as immutable Python/Pydantic contracts with synthetic tests. No
provider account, credential, endpoint, data, `/data`, publication, deployment,
or scheduler state changed.

## Purpose

This contract binds each external source to the exact uses that official terms
or written permission support. It sits before provider acquisition and beside
Data Record Governance V1; it does not replace data-quality, point-in-time,
coverage, or record-classification checks.

## Use dimensions

| Use | Meaning |
| --- | --- |
| `dell_acquisition` | Dell may request or download the source. |
| `dell_raw_retention` | Dell may retain source material for the required period. |
| `dell_derived_analysis` | Dell may compute WH Alpha analytics from it. |
| `equal_capability_raw_display` | Raw source-derived values may be shown identically to guest and credential Sessions. |
| `equal_capability_derived_display` | Charts, scores, classifications, and other derived works may be shown identically. |
| `equal_capability_machine_delivery` | The required data may be delivered through WH Alpha JSON/API/browser transport. |

Every review contains all six dimensions so silence cannot become permission.
Each use has independent evidence fingerprints, conclusion, and reason codes.

## Assessment rules

- `blocked` and `not_applicable` block a required use.
- `requires_separate_permission` and `unresolved` remain unresolved.
- An expired review fails closed before individual conclusions are used.
- A review covers only its declared standard data families.
- Official evidence URLs must be public HTTPS URLs without embedded
  credentials, query strings, or fragments.
- An eligible assessment still has `operational_authority=none`.

`EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1` is the complete six-use requirement
for a normal market source that supplies stored facts, analytics, displayed
values, and the browser payload. Specialized evidence sources may be assessed
against a narrower caller-declared set only when the downstream data contract
does not use the omitted capabilities.

## Relationship to record governance

Source permission answers whether the source may be used. Data Record
Governance answers whether a specific record is accepted, sufficiently
evidenced, complete, point-in-time eligible, retained correctly, and eligible
for equal-capability serving. Both must pass; neither implies the other.

## Public import path

```python
from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SourcePermissionReviewV1,
    assess_source_uses,
)
```

## Current boundary

The contract has no built-in provider allowlist and deliberately does not
encode volatile terms conclusions as permanent code. Dated provider reviews
hold those conclusions. Historical Pilot approval review 1.1 now consumes
fresh exact assessments for its three source families and derives the
permission gate. It recomputes the assessments from the bound review, so
callers cannot manually mark it satisfied or pair cleared assessments with a
blocked review. No physical
provider access or acquisition integration exists.

ADR 0101 adds one read-only current-pilot consumer. It converts the unchanged
2026-08-28 Massive review documents into an in-memory typed blocked review,
binds their exact file-set fingerprint and repository-record time, and rejects
any later byte drift until a new explicit review is recorded. This does not
publish a permission review or make Massive eligible.

## Immutable repository boundary

Repository source now includes an explicit caller-root review repository. It
publishes one content-addressed directory per source/review fingerprint:

```text
governance/source-permission-reviews/schema_version=1/
  source=<source_id>/review=<sha256>/
    review.json
    assessments.json
    manifest.json
```

The repository has no default `/data` root, active pointer, network client, or
CLI. It stores only typed conclusions, public official URLs, evidence hashes,
and assessments—not source page bodies, credentials, private agreements, or
provider payloads. Publication uses a sibling staging directory, file and
directory fsync, atomic rename, and formal reread. Identical reruns are
idempotent; conflicts, corruption, partial targets, cross-review assessments,
and symlink paths fail closed. Current verification uses pytest temporary
directories only; no canonical physical review has been published.

After permission is established, canonical fact choice is separately governed
by [Source Resolution Governance V1](source-resolution-governance-v1.md).
