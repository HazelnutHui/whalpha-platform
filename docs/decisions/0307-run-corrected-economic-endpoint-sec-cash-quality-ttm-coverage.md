# ADR 0307: Run Corrected Economic-Endpoint SEC Cash-Quality TTM Coverage

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0305 produced a closed, owner-only V2 selection package containing
120,473 canonical issuer endpoints and 361,419 query rows. The superseded V1
TTM run used filing `fy` as an economic identity and therefore cannot govern
coverage. The corrected run must consume only the V2 package and must not
reopen its target index or the normalized Company Facts source.

## Decision

Adopt `quant-research-sec-cash-quality-ttm-coverage/2.0` as an issuer-level
coverage contract keyed by `(Company Facts CIK, duration origin, fiscal
period, period end)`. Reported `fy` remains lineage only.

Within one origin, the only permitted order is Q1, Q2, Q3, FY. Across fiscal
years, the next Q1 origin must be exactly one day after the prior FY end. Each
FY duration must be 350 through 378 days inclusive, admitting evidenced 52-
and 53-week years while rejecting stubs and unexplained gaps. Multiple period
ends for one `(CIK, origin, fp)` are quarantined before sequencing.

Q1 is its reported duration. Q2, Q3, and FY discrete CFO and net income are
respectively YTD less Q1, YTD less Q2, and FY less Q3 within the same origin.
A TTM observation requires five consecutive endpoint boundaries: opening
Assets at the endpoint before the four included discrete quarters, closing
Assets at the ending endpoint, and four fully provable discrete quarters.
Negative and zero flow values are valid; zero average Assets is blocked.

Every output retains duration origin as part of its economic identity, plus
the maximum knowledge clock across all fifteen component
rows, every contributing accession, and every source occurrence ID. CFO and
net income accession coherence is required at each input endpoint. No value,
date, origin, period, amendment, or missing quarter may be inferred.

The plan binds the V2 selection verification and result fingerprints plus the
input Arrow logical hash, Parquet physical hash, schema fingerprint, byte size,
and exact row count. Forward/reverse issuer traversal must produce identical
results and Arrow hashes. Owner-only atomic custody and exact reread are
required.

This is issuer-level source coverage only. It grants no listed-security
identity or applicability conclusion, factor materialization, outcome,
Validation, Holdout, Candidate, canonical-research, Product, or Production
authority.

## Execution evidence

The bounded V2 run read only the 361,419-row direct-origin package. An initial
replay check exposed that the inherited V1 output schema omitted duration
origin and could not deterministically order two economic endpoints sharing an
issuer and period end. No package was published. V2 now retains origin and
sorts by the full economic identity before replay.

The corrected run produced 75,391 TTM-ready endpoints across 6,724 of 8,260
input issuers. It blocked 45,082 endpoints: 31,345 for insufficient prior
endpoints, 11,327 for a non-consecutive quarter sequence, 1,418 for ambiguous
period endpoints, 800 for annual duration outside the registered range, and
192 for zero average Assets. Forward and reverse result fingerprints and
Arrow hashes were identical, and owner-only exact reread succeeded.

This 62.6% endpoint coverage and 81.4% issuer coverage is sufficient to begin
a separately governed, outcome-blind listed-security applicability census. It
is not itself evidence of listed-security identity, domicile, operating
structure, or universe eligibility, and it does not authorize projection.
