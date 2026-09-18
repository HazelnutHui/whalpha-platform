# China A-share Official-Evidence Priority Plan V1

## Purpose

Freeze the candidate-driven, offline-only request inventory that precedes any
full-market official evidence acquisition. The plan consumes exactly one
exact-reread conservative reconstruction package and performs no network call.

Contract version:
`china-ashare-official-evidence-priority-plan/1.0`.

## Input binding

The plan binds:

- conservative package logical fingerprint and manifest physical SHA-256;
- conservative plan, global census, and candidate-set fingerprints;
- effective interval `2021-09-16` through `2026-09-16`; and
- the candidate records retained in the 109 partition censuses.

No separate population, source, normalized, outcome, or Product input is
accepted.

## Stable request unit

Each request contains:

- a stable subject key using `instrument:<UUID>` for resolved identities or an
  explicit `quarantined-source-security:<source_security_id>` namespace when
  no stable instrument identity exists;
- a SHA-256 request ID derived from contract version, stable subject key,
  family, purpose, and effective interval;
- optional resolved `instrument_id` and the source partition index;
- one of the three admitted families and one exact purpose;
- effective start and end dates;
- two ordered candidate official authorities;
- a fixed expected-field set;
- one maximum acquisition attempt across those candidate authorities;
- `source_available_at_must_be_observed=true`; and
- failure disposition `quarantine_unchanged`.

SSE routes use SSE then CNINFO. SZSE routes use SZSE then CNINFO. Authority
candidates are alternatives, not two authorized calls. Actual URLs, query
parameters, rate limits, checkpoints, retries, and captures belong to a later
acquisition plan.

## Families and purposes

| Priority | Family | Securities | Purposes per security | Maximum units |
| --- | --- | ---: | ---: | ---: |
| 1 | Risk warning | 492 | 1 | 492 |
| 2 | Lifecycle | 189 | 4 | 756 |
| 3 | Listing stage | 1,046 | 1 | 1,046 |
| — | Corporate action | 5,196 | 0 | 0 |

Risk-warning requests seek transition kind, subtype, publication clock,
effective interval, official document identity/URL, and raw hash.

Lifecycle is deliberately separated into four purposes:

1. listing-status interval history;
2. relisting or resumption history;
3. termination-decision history; and
4. delisting-period and last-trading-day history.

Listing-stage requests seek original listing date, board, IPO special-stage
interval, applicable special price-limit regime, publication clock, official
document identity/URL, and raw hash.

The plan ceiling is 2,294 request units. The 5,196 factor-change securities and
56,112 candidate windows remain quarantined and generate zero request units.

## Determinism and custody

Candidate input order cannot affect output. Requests are ordered by family
priority, stable security ID, and purpose. Request IDs and plan fingerprints
must match for forward and reverse candidate traversal.

The package contains exactly:

- `official-evidence-priority-plan.json`; and
- `official-evidence-priority-manifest.json`.

Directories are mode `0700`, files mode `0400`, publication uses same-filesystem
atomic rename, and exact reread rejects symlinks, permission changes, unknown
files, non-canonical JSON, size/hash mismatches, path identity changes, schema
changes, or budget/count drift.

## Evidence reuse

A later capture may be reused only when a downstream adjudication binds the
same stable security, official authority, raw byte hash, publication clock,
effective interval, and parsed fields. One document may support more than one
purpose, but every purpose remains separately adjudicated and conflicts remain
explicit. Reuse reduces duplicate downloads; it does not reduce the frozen
maximum request-unit accounting or confer `as_operated` status.

## Authority

This contract fixes all of the following to false or zero:

- network execution;
- outcome reads;
- return construction;
- Historical Coverage;
- Factor Discovery;
- research backtesting;
- canonical Apply;
- Product publication; and
- deployment or trading.

See [ADR 0306](../decisions/0306-freeze-a-share-official-evidence-priority-plan-before-acquisition.md).
