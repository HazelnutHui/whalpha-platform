# Historical Research Foundation Contracts V1

## Status

Implemented as provider-neutral, immutable Python/Pydantic row and manifest
contracts plus explicit PyArrow schemas and temporary-root Parquet repositories
with synthetic tests. ADR 0100 also adapts the existing canonical Dell EOD and
Identity families into deterministic, read-only, unpublished family evidence.
Canonical Dell now also contains two prospective signal-eligible Membership
partitions, bounded corporate-action source custody and split-only facts, and a
sparse split-adjustment publication for outcome reconciliation. These are
partial families, not complete research-ready evidence. No canonical lifecycle
family or final Historical Coverage publication exists, and no research result
exists.

## Purpose

These contracts make the minimum point-in-time research foundation explicit
before historical strategy formulas or performance claims are allowed. They
implement the typed boundary accepted by ADR 0051 and the Historical Research
Data Foundation V1 architecture.

## Implemented records

### Corporate action source observation (`1.1`)

One provider revision of a split, reverse split, cash dividend, stock
dividend, symbol change, merger, spinoff, or delisting. It preserves source
identifier and revision, stable-ID resolution, action-specific facts,
effective/source-available/first-observed/ingested timing, correction or
cancellation lineage, and explicit quality state. Incomplete action fields are
accepted only as quarantined evidence; heuristics never establish an action.
Provider-reported cumulative adjustment factor, split-adjusted dividend cash,
distribution type, and frequency remain separately named source evidence and
never become canonical ledger factors by field reuse.
This source family is explicitly distinct from the required canonical
`corporate_action` family and cannot substitute for it in `research_ready`.
A completed source partition may contain zero rows so a valid no-event result
can be represented without inventing an action.

### Instrument lifecycle observation

One effective-dated lifecycle or lineage observation keyed by stable
`instrument_id`. It separates ticker/exchange display identity from the key,
supports active and governed terminal states, preserves predecessor/successor
evidence and optional terminal cash facts, and enforces the three-clock rule.
Unknown or unresolved lifecycle evidence must carry review flags.

### Universe membership decision

One Universe, instrument, and session decision. Membership is explicitly
three-state:

- `included` maps to `is_member=true`;
- `excluded` maps to `is_member=false`;
- `quarantined` maps to `is_member=null`.

Every row binds methodology, point-in-time origin, evaluated-base fingerprint,
ordered source fingerprints, source cutoff, evaluation time, and reason codes.
This record does not yet implement the complete daily partition manifest or
the Universe Definition portion of Universe Membership V1.

### Adjustment ledger entry

One projection from a raw source session to an explicit basis session. Split
price, split volume, and total-return multipliers remain separate. Multiplier
direction is fixed as `multiply_raw_value_to_basis`; unavailable or
quarantined adjustments must remain null and cannot use an unexplained neutral
factor of one.

### Historical coverage manifest

One bounded readiness statement referencing exact fingerprints and file hashes
for EOD, point-in-time Identity, membership, corporate action, lifecycle, and
adjustment families. `research_ready` requires:

- at least 252 ordered sessions;
- all six families present, completed, and covering the declared interval;
- a positive mature-signal count consistent with feature warm-up and outcome
  horizon;
- no blocker reason codes.

Other readiness states require explicit reasons. The typed contract alone
cannot prove XNYS continuity, source permission, or semantic completeness.
ADR 0099 now adds the missing physical-validity layer:

- `HistoricalDatasetCoverageEvidenceV1` binds one required family and exact
  sessions to source completion manifests plus every payload file hash;
- evidence self-fingerprints, session coverage, record totals, unique sorted
  paths, safe relative paths, and quarantine counts are validated;
- the immutable Historical Coverage publication binds the typed manifest to a
  separate physical completion envelope; and
- formal reread walks transitively through every family evidence manifest,
  source completion manifest, and payload file before returning the typed
  coverage.

The strategy-readiness CLI can select only an exact coverage ID below the
canonical root; it still cannot accept an arbitrary file path.

## Numeric and temporal safeguards

- Financial ratios, cash values, and multipliers reject binary floating-point
  input and use finite `Decimal` values.
- Operational timestamps must be UTC.
- Provider ticker is normalized but never treated as the permanent key.
- Source availability cannot be later than first observation, and ingestion
  cannot precede first observation.
- Corrections append revisions and identify the superseded source event.
- Unknown, unresolved, and non-clear states require explicit quality flags.

## Public import path

The contracts are exported from
`tip_api.contracts.market_data.v1`. The implementation lives in
`historical_research.py` and is covered by fixture-only contract tests.

## Implemented physical boundary

Corporate-action source observations, lifecycle observations, daily membership
decisions, and adjustment entries have exact Arrow schemas. Their repository:

- uses the proposed schema-versioned family partitions;
- orders rows and rejects duplicate business keys;
- writes a staged Parquet file plus completion manifest and atomically installs
  the immutable partition;
- records logical and physical SHA-256 evidence;
- formally rereads schema, count, ordering, hashes, partition path, and typed
  rows;
- rejects unsafe path segments, symlink boundaries, incomplete partitions,
  corruption, and conflicting reruns.

All repository tests use isolated temporary roots. Saved synthetic Massive
split/dividend mapping and independent adjustment invariants are complete. The
credential-free planner and the bounded EOD/Identity Pilot mechanics are also
complete. Cross-family state is governed by Data Record Governance V1 without
replacing the domain statuses in this contract.

Physical EOD/Identity family evidence and partial Membership, corporate-action,
and adjustment publications now exist under `/data`, as recorded in
[current context](../project/current-context.md). No transitive Historical
Coverage publication yet binds all six required families; that final
publication boundary remains fixture-only. The 2026-08-30 assessment proved
transitive in-memory validation for its then 31 EOD/Identity sessions; current
canonical price depth does not replace the missing families.
