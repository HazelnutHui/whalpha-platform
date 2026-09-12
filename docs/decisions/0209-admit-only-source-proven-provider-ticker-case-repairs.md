# ADR 0209: Admit only source-proven provider-ticker case repairs

- Status: Accepted
- Date: 2026-09-12

## Context

The clean Reconciled EOD contract 1.1 build completed its first seven batches
and retained 300 session partitions before batch eight stopped on 20 dates
between 2022-10-27 and 2022-12-16. The stop wrote no interval marker and no
canonical data.

All 20 failed candidates had zero economic-value changes and zero unexpected
additions or absences. Their sole blocker was 30 retained-source provenance
changes. Each change preserved the stable `instrument_id`, timestamp,
observation time, OHLCV, adjustment fields, quality status, quality flags,
revision state, and schema version. Only the provider ticker embedded in
`source_record_id` changed from legacy forced upper case to the exact provider
case, for example `RXOW` to `RXOw`, `FGW` to `FGw`, and `BAMW` to `BAMw`.

Same-session retained Identity source proves that each exact mixed-case ticker
is resolved to the same stable instrument and that the forced-upper-case
ticker is absent from exact Identity. The canonical normalized Resolver also
reproduces the legacy upper-case binding. This is a correction to provenance
spelling, not a security reassignment or an economic revision.

Treating every retained-source provenance change as acceptable would hide
timestamp, observation-time, quality, revision, or source-identity drift. The
accepted class therefore must remain narrower than generic provenance change.

## Decision

Version the Reconciled EOD session, interval, Apply-plan, batch-result, and
build-result contracts to 1.2. Count all provenance-only changes explicitly as
expected or unexpected.

A retained-source provenance-only change is accepted as an exact provider-
ticker case repair only when every condition below is true:

1. the selected price package has retained-original provenance;
2. the base and rebuilt records share the same EOD business key and stable
   `instrument_id`;
3. every economic field is identical;
4. source observation time, quality status and flags, latest-revision state,
   and schema version are identical and reproduce the retained package;
5. the source-record timestamps are identical;
6. the old ticker is exactly the upper-case normalization of a different-case
   rebuilt ticker;
7. same-session exact Identity resolves the rebuilt ticker to the same stable
   instrument and contains no exact entry for the old upper-case ticker; and
8. the canonical normalized Resolver maps that old ticker to the same stable
   instrument, reproducing the legacy behavior.

An accepted repair uses `accepted_case_sensitive_reconciliation`. Session
manifests retain expected and unexpected provenance counts; interval, batch,
build, and Apply-plan summaries retain the total provenance-only count. Any
retained-source change outside the eight conditions remains quarantined.

Later-reacquired packages retain their existing explicit later-source
disposition. Their expected provenance differences are counted but cannot use
the retained-original case-repair proof.

The stopped 1.1 candidate remains immutable non-authoritative evidence. A new
clean revision, edition ID, fixed creation time, and empty candidate root are
required for contract 1.2 construction.

## Consequences

- Exact provider casing is preserved in research provenance without changing
  prices or stable security identity.
- A generic source-record, time, quality, revision, or schema difference still
  fails closed.
- Proven case repairs are distinguishable from later-reacquisition provenance
  and from ADR 0208's proven legacy-security removal.
- This grants no Historical Coverage, research, performance, canonical Apply,
  Production, publication, deployment, or model authority.

## Supersession scope

This decision narrows ADR 0204's retained-source provenance gate only for the
eight-condition case-repair class. ADR 0208 continues to govern proven legacy
record removals. ADR 0203 remains the exact provider-symbol mapping authority.

## Rejected alternatives

- **Ignore source-record casing:** rejected because exact provider identifiers
  are part of reproducible provenance.
- **Accept all provenance-only changes:** rejected because economically equal
  rows can still carry materially different observation or quality evidence.
- **Hard-code dates or symbols:** rejected because evidence conditions, not
  the observed examples, must govern reconstruction.
- **Reuse the incomplete 1.1 candidate:** rejected because completed session
  manifests are revision- and contract-bound.
