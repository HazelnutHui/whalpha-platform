# ADR 0116: Quarantine low-ratio stable-identity collisions

## Status

Accepted.

## Date

2026-09-01.

## Context

The authorized 2026-08-31 Identity package completed 14 pages and 13,141
records. Every existing quality gate passed except the absolute requirement
that stable-identifier collision count equal zero. One group contained two
active Common Stock observations with the same Share Class FIGI, Composite
FIGI, provider identifier, exchange, currency and status but different ticker,
name and source-update time. One ticker existed in the prior snapshot and the
other was newer.

Choosing either observation would infer ticker lifecycle truth that the source
did not explicitly provide. Rejecting the entire 13,141-record snapshot also
prevents 9,965 independently resolved instruments from advancing even though
the existing mapper already quarantines both conflicting observations as
ambiguous and emits neither an Instrument nor Resolver row for them.

## Decision

Keep every stable-identifier collision quarantined. Do not choose the newest,
the prior ticker, or any other winner. Include collision observations in the
eligible identity denominator so coverage cannot improve by excluding them.

Replace the absolute-zero snapshot gate with a maximum collision-observation
ratio of 0.001 (0.1%), matching the existing ticker-ambiguity ceiling. A ratio
above that limit still blocks the entire snapshot. Preserve collision count
and ratio in quality evidence.

This narrowly supersedes ADR 0009's absolute-zero collision gate. It does not
change stable identity priority, establish ticker lifecycle, merge listings,
or make ambiguous records Universe-eligible.

## Consequences

- Isolated provider conflicts no longer block unrelated resolved securities.
- Every conflicting observation remains visible as ambiguous provider identity
  evidence and absent from canonical Instrument and Resolver outputs.
- Coverage is slightly more conservative because quarantined collisions enter
  its denominator.
- A systemic collision increase above 0.1% still fails closed.
- Downstream consumers continue to receive only resolved stable identities.

## Alternatives considered

- Select the record with the latest source-update time. Rejected because update
  recency is not explicit ticker-validity evidence.
- Preserve the prior ticker. Rejected because it would suppress a potentially
  valid change without lifecycle evidence.
- Keep absolute zero. Rejected because it converts two safely quarantined
  observations into loss of the whole market snapshot.
- Allow collisions without a bounded ratio. Rejected because systemic provider
  or mapping defects must still stop publication.
