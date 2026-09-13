# Historical Corporate Action Unresolved Census V1

Contract: `historical-corporate-action-unresolved-census/1.0`.

This contract governs an owner-only diagnostic over unresolved typed rows in
one formally retained Corporate Action Resolution Shadow 1.1. It measures the
same normalized provider ticker across every Identity Resolver already bound
to that shadow. It does not resolve, mutate, publish, or admit an event.

## Population and classes

Every typed source row whose `instrument_resolution_status` is `unresolved`
must contribute exactly once to one ticker record. The seven unrepresentable
source rows from the first five-year shadow remain separately counted and are
not given fabricated tickers.

Each distinct provider ticker has exactly one class:

- `zero_historical_candidates`: the ticker appears in no bound Resolver;
- `one_historical_candidate`: all appearances map to one stable
  `instrument_id`; or
- `multiple_historical_candidates`: appearances map to two or more stable IDs.

For every ticker/stable-ID relation, the artifact records first and last
observed sessions and the number of sessions observed. Per-ticker unresolved
source-row counts are also split by exact-date failure reason and action type.
The counts are descriptive evidence only. A unique historical candidate does
not establish ownership of the ticker on the action's effective date.

## Evidence binding and execution

The manifest binds the resolution-shadow physical and logical identity, its
complete source/typed/unrepresentable denominators, the bound Identity evidence
set, all formally scanned Resolver artifacts, the clean implementation
revision, and fixed evaluation time. The ordered Resolver binding fingerprint
covers every one of the bound sessions, not only sessions used by exact-date
resolution.

The scanner uses deterministic contiguous session blocks and one to 32 spawned
workers, with eight as the default ceiling. Workers return only requested-
ticker aggregates and ordered Resolver bindings. Process count is operational
metadata and is excluded from the semantic logical fingerprint; serial and
parallel scans of identical evidence must yield identical records and
fingerprints.

## Output and authority

The package is an absent direct child of an explicitly supplied, real,
owner-owned mode-0700 Dell custody root. It contains only mode-0400
`manifest.json` and `ticker-candidates.json`; creation is staging-first and an
atomic directory rename. Formal reread verifies package membership, ownership,
modes, hashes, logical fingerprints, aggregate denominators, and exact source
bindings.

The manifest fixes stable-ID assignments, source mutations, canonical writes,
Adjustment Ledger writes, Historical Coverage writes, analytics, Candidate
writes, publication, deployment, scheduler changes, and external requests at
zero. The artifact role is `quarantine_diagnostic_only`.
