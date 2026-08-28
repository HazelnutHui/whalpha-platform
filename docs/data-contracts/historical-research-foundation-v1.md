# Historical Research Foundation Contracts V1

## Status

Implemented as provider-neutral, immutable Python/Pydantic row and manifest
contracts plus explicit PyArrow schemas and temporary-root Parquet repositories
with synthetic tests. No provider adapter, canonical dataset, `/data` write,
or research result exists.

## Purpose

These contracts make the minimum point-in-time research foundation explicit
before historical strategy formulas or performance claims are allowed. They
implement the typed boundary accepted by ADR 0051 and the Historical Research
Data Foundation V1 architecture.

## Implemented records

### Corporate action source observation

One provider revision of a split, reverse split, cash dividend, stock
dividend, symbol change, merger, spinoff, or delisting. It preserves source
identifier and revision, stable-ID resolution, action-specific facts,
effective/source-available/first-observed/ingested timing, correction or
cancellation lineage, and explicit quality state. Incomplete action fields are
accepted only as quarantined evidence; heuristics never establish an action.
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
cannot prove XNYS continuity, source permission, physical file validity, or
semantic completeness; future readers must do so.

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

All repository tests use isolated temporary roots. The next safe slice is
provider mapping against saved synthetic response fixtures, followed by
independent split/dividend adjustment invariants. A real pilot remains blocked
by source permission, account entitlement, lifecycle-source coverage, and an
exact authorized acquisition plan.
