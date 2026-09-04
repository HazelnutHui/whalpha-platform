# ADR 0125: Separate session discovery from partition validation

## Status

Accepted.

## Date

2026-09-04.

## Context

Canonical EOD now contains 303 completed sessions. Several operational paths
need only the ordered set of completed session dates to select a current
session, evaluate freshness, or choose a bounded calculation window. Those
paths called `list_sessions()`, which reconstructs and fingerprints every EOD
Parquet partition before returning descriptors.

On the unchanged Dell 2026-09-03 baseline, the current-context report took
about 7 to 8 minutes even when the whole-`/data` inventory fingerprint was
disabled. The inventory fingerprint alone took 3.77 seconds, while the
completion index plus a full inspection of the latest partition took 2.14
seconds. The repeated all-history reconstruction, rather than storage size or
network access, is therefore the immediate control-path bottleneck.

ADR 0118 already accepted the completion index for current Snapshot session
selection. The same distinction must be applied consistently without turning
the completion index into proof of partition contents.

## Decision

- Use `list_session_index()` when a path needs only ordered completed dates,
  the first/latest date, a count, freshness, or membership of a requested date
  in the completed set.
- Continue to use `read_bars()`, `read_history_sessions()`, or
  `inspect_session()` for every partition whose contents feed a calculation,
  publication, user response, or current-state integrity claim.
- Keep `list_sessions()` as the deep descriptor/evidence boundary. Research
  evidence builders, the explicit session-descriptor API, and other callers
  that consume record counts, Identity bindings, availability timestamps, or
  quality warnings must continue to use it.
- Advance the current-context report to contract 1.2. Its normal recovery mode
  validates the completion index and fully inspects the latest EOD partition.
  An explicit `--full-history-validation` mode retains reconstruction of every
  completed partition for periodic or investigative audit.
- Keep the whole-`/data` inventory fingerprint and all Apply/publication CAS
  checks unchanged. This decision creates no cache, mutable index, daemon, or
  second source of truth.
- Preserve provider-neutral fallbacks where services may receive a repository
  that does not implement the Parquet completion index.

## Consequences

- Routine context recovery and date-only freshness gates no longer scale with
  all historical Parquet contents.
- Data actually used by analytics remains fully schema-, row-, fingerprint-,
  Identity-, and business-key validated.
- A periodic full-history audit remains available and cannot be confused with
  the faster operational report because the report exposes its history
  validation scope.
- Model formulas, thresholds, Universes, published payloads, canonical data,
  scheduler authority, and OCI state do not change.
- The project reuses the existing immutable completion manifests instead of
  adding another persistent cache or catalog.

## Alternatives Considered

### Cache a whole-history report

Rejected for this phase. A mutable cache would add invalidation, custody, and
recovery state when the existing completion manifests already provide the
bounded discovery evidence needed by operational paths.

### Weaken `list_sessions()` globally

Rejected. Existing callers may rely on its deep descriptor validation, and a
global semantic change would make research and API evidence less explicit.

### Keep reconstructing all history on every gate

Rejected because it adds minutes of repeated work without independently
validating the bounded partitions actually consumed by that operation.
