# ADR 0148: Build a disconnected inactive lifecycle resolution shadow

- Status: Accepted
- Date: 2026-09-05

## Context

The completed 2026-09-03 inactive source package contains 23,469 observations,
but only 5,933 select an accepted FIGI under the existing stable-identity
priority. Real-data inspection further found 1,222 observations in 587
conflicting stable-key groups. Of the remaining unique stable keys, some do not
occur in the 303 canonical Instrument snapshots, some lack a parseable
`delisted_utc`, and some canonical instruments still appear after the claimed
delisting date.

Treating all provider inactive rows as lifecycle facts would introduce ticker
joins, stable-key ambiguity, temporal contradiction, survivorship errors, and
false terminal conclusions. Omitting rejected rows would hide the size and
reason for the unresolved population.

## Decision

Create a disconnected, immutable `/tmp` shadow with two one-to-one layers:

1. a normalized source-observation Parquet file preserving the exact thirteen
   reviewed provider result fields, page/row occurrence, source observation
   time, payload fingerprint, and occurrence fingerprint; and
2. a resolution-decision Parquet file referencing every source occurrence and
   assigning explicit identity status, lifecycle disposition, canonical
   history bounds, effective-date candidate, and reason codes.

Resolution uses the existing priority of share-class FIGI, then composite
FIGI. Provider stable ID is absent from this source. Ticker and CIK never create
positive identity.

A row is `review_candidate` only when all of these gates pass:

- exactly one source observation selects the stable identity at that anchor;
- its deterministic `instrument_id` exists in the bounded canonical Instrument
  history;
- `delisted_utc` parses as a date no later than the anchor;
- the source ticker occurs in that canonical instrument's bounded ticker
  history; and
- the canonical instrument is not observed after the effective-date candidate.

Everything else is `quarantined` with one or more fixed reasons, including
missing stable identity, stable-key collision, absence from canonical history,
missing/malformed/future effective date, ticker conflict, or canonical
observation after the claimed date. A review candidate is still not a
canonical lifecycle record: terminal reason, last tradable session, successor,
consideration, and historical source-availability time remain unsupported.

The manifest binds both Parquet files, the exact source package, the complete
canonical Instrument input inventory, counts, schemas, hashes, and logical
fingerprints. Formal reread must prove a one-to-one source/decision relation.
The builder is network-disabled and performs no `/data`, analytics,
publication, deployment, or scheduler write.

## Consequences

- Every one of the 23,469 observations remains auditable; unresolved evidence
  cannot disappear through an inner join.
- The 547 preliminary consistent rows, including 76 in the 7/17–9/3 window,
  remain only expected counts until the implemented shadow reproduces them.
- Source normalization and identity resolution stay separate even though they
  are sealed in one shadow manifest.
- Later canonical lifecycle work can select reviewed candidates and add
  corroborating terminal evidence without rebuilding or silently changing the
  provider observation layer.

## Validation evidence

Clean implementation revision
`62be872aa8c5a8518803204c224cc29312078fa1` passed all 2,088 backend tests.
The two real source anchors then built and independently reread from owner-only
`/tmp` custody:

- 2026-07-16: 23,260 one-to-one rows, 471 review candidates and 22,789
  quarantined, using 268 canonical Instrument sessions no later than the
  anchor; and
- 2026-09-03: 23,469 one-to-one rows, 547 review candidates and 22,922
  quarantined, using all 303 canonical Instrument sessions.

The later source adds 262 exact rows, of which 76 pass the same review gates,
and omits or revises 53 older rows, none of which was a review candidate. No
shared exact source row changes disposition. The formal current-context report
after both builds proves the canonical `/data` inventory unchanged.
