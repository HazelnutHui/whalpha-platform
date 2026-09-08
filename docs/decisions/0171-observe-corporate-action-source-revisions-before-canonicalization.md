# ADR 0171: Observe corporate-action source revisions before canonicalization

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0170 resolves the first retained split/dividend source observation against
exact event-date Identity, but the provider endpoints do not expose a
defensible historical publication timestamp or provider revision sequence.
Assigning canonical source revision `1` from one late historical snapshot would
therefore confuse WH Alpha's observation order with provider history.

A second complete observation of the identical endpoint, action kind, and
inclusive date range can show whether provider action IDs and payloads are
stable over the observed interval. It cannot prove that earlier corrections
did not occur, that a removed row is a cancellation, or when a changed fact was
first knowable.

## Decision

Add one disconnected, network-prohibited, owner-only `/tmp` repeat-diff
boundary with the following rules:

- formally reread two distinct, complete ADR 0169 source packages for the same
  provider, action kind, and exact date range;
- require the repeat package to start strictly after the baseline package
  completed and require comparison time not to precede repeat completion;
- require every row to have one unique nonempty provider action ID; stop rather
  than invent correlation keys for missing IDs;
- compare canonical JSON payload fingerprints by provider action ID,
  independent of pagination and row order;
- classify rows only as unchanged, changed under the same ID, added, or
  removed, and report changed field names plus event-date/ticker changes;
- retain no copied raw payload in the diff; bind both source manifests and
  content fingerprints, while leaving the immutable source packages as the
  evidence of record;
- call every difference an observed snapshot delta, not a confirmed provider
  revision, correction, cancellation, or availability timestamp; and
- publish atomically below `/tmp`, use owner-only modes, and formally reread
  exact output files, hashes, logical fingerprints, and aggregate counts.

The report records zero external requests of its own, canonical writes,
Adjustment Ledger writes, analytics, publication, deployment, and scheduler
changes. Source acquisition remains a separate explicit operation.

## Consequences

- A no-change result supports short-interval source stability only.
- Same-ID changes are candidates for append-only revision semantics but still
  require field-level interpretation and another observation policy.
- Added and removed IDs remain ambiguous until source semantics or independent
  evidence distinguish genuine event additions/cancellations from provider
  snapshot behavior.
- No canonical Corporate Action or adjustment transition follows automatically
  from one repeat comparison.

## Rejected alternatives

- **Treat the first retained package as provider revision 1:** invents
  unobserved history.
- **Use payload hash as the correlation key:** turns every change into an
  unrelated removal/addition and loses provider event identity.
- **Correlate missing IDs by ticker/date/amount:** can merge distinct events or
  revisions and violates the no-heuristic identity boundary.
- **Interpret a missing repeat row as cancellation:** overstates what an
  endpoint snapshot alone proves.

## Execution evidence

The first real repeat observation and both split/dividend diffs completed on
clean Dell main `1f07c53893aa31366f057fd440ed82f9ed49ef87`. All 1,949 split
and 68,150 dividend payloads were unchanged; same-ID changes, added IDs,
removed IDs, effective-date changes, ticker changes, and pagination-shape
changes were all zero. Both later source packages and diff reports passed
independent formal reread. This approximately 69–73 minute stability interval
does not expand the interpretation beyond `observed_snapshot_delta_only` and
does not authorize canonical or Production state.
