# ADR 0099: Require Transitive Physical Evidence for Historical Coverage

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0098 prevents an arbitrary Historical Coverage JSON path from entering the
strategy-readiness command. The typed `HistoricalCoverageManifestV1` still
describes referenced family fingerprints and file hashes without providing a
physical publication or a reader that proves those files exist and remain
unchanged.

Accepting a structurally valid manifest would leave a false-readiness route: a
caller could claim 252 sessions and six complete families without binding the
claim to the source completion manifests and payload bytes that were formally
reviewed.

## Decision

Add `historical-dataset-coverage-evidence/1.0`. One immutable evidence manifest
binds an exact required family, ordered sessions, record and quarantine counts,
and one or more source artifacts. Each artifact binds its completion manifest,
all payload files, physical SHA-256 values, logical fingerprint, record count,
and covered interval. Every declared session must be covered.

Publish family evidence only under the Dell-root-relative path:

```text
market-data/historical-coverage-evidence/schema_version=1/
  family=<family>/evidence_id=<logical-fingerprint>/manifest.json
```

Publish the final typed coverage plus its separate completion envelope only
under:

```text
market-data/historical-coverage/schema_version=1/
  coverage_id=<immutable-id>/
```

The formal reader rejects path escape, symlinks, unexpected files, malformed or
oversized JSON, self-fingerprint mismatch, manifest or payload hash drift,
incomplete source manifests, logical/count mismatch, and any discrepancy
between a coverage reference and its family evidence.

The strategy-readiness command may accept an exact `--coverage-id`, never a
caller-selected manifest path. It derives the only possible location below the
supplied canonical root and passes the coverage onward only after the complete
transitive reread succeeds.

All physical publication tests remain limited to isolated temporary roots.
This decision creates no `/data` family evidence, Historical Coverage
publication, provider request, backfill, model run, performance claim,
publication, deployment, or scheduler authority.

## Consequences

- A coverage claim is now transitively bound to the bytes it summarizes.
- Dataset evidence can reuse immutable facts without copying their rows.
- One changed source manifest or payload invalidates every dependent coverage
  reread.
- A complete fixture can prove the mechanics of the transition to
  `ready_for_development_review` without authorizing development.
- Current Dell state remains `data_blocked` because no physical Historical
  Coverage directory exists and only 31 canonical sessions are present.

## Alternatives Considered

### Accept a direct coverage-manifest path

Rejected because path selection and schema validation do not prove source
artifacts or their physical custody.

### Copy all historical rows into the coverage publication

Rejected because Coverage is a manifest layer, not a duplicate canonical data
store.

### Treat a family-level fingerprint as sufficient

Rejected because a logical value without exact source manifests and payload
hashes cannot detect missing or changed physical evidence.
