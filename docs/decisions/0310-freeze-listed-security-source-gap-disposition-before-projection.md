# ADR 0310: Freeze Listed-Security Source-Gap Disposition Before Projection

## Status

Accepted; historical projection remains blocked

## Date

2026-09-18

## Context

ADR 0308 found zero fully applicable rows among 75,391 issuer-level TTM
observations. The retained daily filer/security links, current provider-form
snapshot, SEC custody, and lifecycle evidence are useful inputs, but none can
be relabeled as complete historical listed-security applicability. In
particular, all historical identity evidence is retrospective relative to the
signal open; the 2026-08-14 provider-form snapshot is not a historical ledger.

The next action must distinguish a source that is locally proven from an
endpoint that is merely registered or described. It must also seek an honest
first research population rather than silently selecting only records that are
easy to resolve.

## Decision

Adopt `quant-research-sec-cash-quality-source-gap/1.0` as the versioned,
outcome-blind source disposition and capability evaluator.

Keep five evidence lanes independent:

1. effective-dated stable `instrument_id` to CIK;
2. effective-dated security form;
3. listing intervals and stable-ID ticker aliases;
4. issuer/security relationship and issuer structure; and
5. multi-common cardinality and policy.

A lane is qualified only when retained local evidence proves a stable key, an
effective interval, and a source knowledge time for the proposed role. SEC
filer identity alone, ticker/name, and a current provider snapshot backcast are
forbidden positive proxies.

## Source disposition

| Source | Verifiable useful role | What it cannot currently prove |
| --- | --- | --- |
| Retained Massive Starter dated Tickers observations | Stable FIGI inputs, CIK/type fields on dated observations, inactive discovery, and limited ticker-change corroboration. Historical PIT Tickers access was observed on three depth-probe dates. | The retained history was observed after the historical signal cutoffs; no complete effective-dated security-form/listing ledger or authoritative issuer structure exists. Ticker Events covered only 6/30 diagnostic instruments and only symbol changes. |
| Retained 2026-08-14 provider-form snapshot | Explicit current provider security form for matched stable instruments. | Any earlier effective date, historical listing interval, issuer operating structure, domicile, or historical source availability. |
| SEC EDGAR/Submissions/Company Facts/Form 25 | Official filing/filer clocks and named filing or termination evidence; filing cover context may corroborate title/ticker/exchange from its acceptance time. | CIK as a listed-security key, a complete share-class ledger, full listing interval, last tradability, or population-wide positive issuer structure. |
| FINRA OTC Daily List | Retained official OTC changes/actions with effective dates. | Stable identity, major-exchange history, complete source-time history, or a cross-venue listed population. |
| Free official venue directories/notices | Prospective current listing observations and targeted venue event corroboration after bounded custody is implemented. | A pre-existing complete five-year ledger, cross-venue stable identity, or facts not actually retained with an observation clock. |
| OpenFIGI / GLEIF | Open identifier/legal-entity crosswalk and ambiguity detection after separate bounded qualification. | Listing validity, knowledge time, security form, or issuer/security applicability by themselves. |
| Paid official venue feeds | Nasdaq Daily List and venue corporate-action products are potential venue-specific listing/event evidence under agreement. | Cross-venue completeness or the five-lane gate without an exact schema, sample, clocks, identifiers, permission, and coverage review. |
| Optional commercial cross-venue source | A candidate point-in-time security-master/lifecycle sample may be tested against the frozen lanes. | No capability is accepted from marketing. Stable share-class and issuer IDs, CIK links, effective intervals, aliases, revisions, availability clocks, structure fields, multi-class relations, and permitted use must all be demonstrated. |

Massive Starter is therefore an important prospective acquisition component,
not a historical proof shortcut. No current source or composition qualifies
all five lanes.

The local coverage evidence is explicit. The applicability denominator has
57,213 same-session admitted CIK links, but zero whose identity evidence is
known by signal open. Of 56,542 unique-common observations, the single current
provider snapshot supplies 48,447 diagnostic form matches and misses 8,095;
none of the matches has a historical effective interval. The Massive depth
probe observed PIT Tickers access on three requested historical dates. Its
separate 30-instrument lifecycle diagnostic returned only six instruments and
nine ticker-change events. The retained FINRA source has 62 monthly packages
and 68,714 OTC observations, but no stable-ID resolution. SEC custody has broad
filer/fact coverage, but its CIK grain does not change these listed-security
counts. No optional commercial source has a locally reviewed sample, so its
verified coverage is zero rather than a marketing estimate.

## Honest first-batch policy

Register `prospective-single-common-core-v1`, but do not activate it yet. Its
activation is the first XNYS session after all five lanes have qualified and
their rules are frozen. Its denominator is all TTM-ready issuer observations
on or after that session, not a hand-picked resolvable list. Each admitted row
must have evidence known by the signal cutoff and exactly one qualified common
security for its CIK. Multi-common, ADR/ADS, foreign ordinary, and unknown or
conflicting structures are quarantined; explicit preferred, fund, unit,
warrant, and right forms are excluded.

This route can provide a smaller honest first research population without
claiming 100% historical coverage. It cannot generate historical Validation or
repair ADR 0308's denominator with later observations.

## Ordered supplementation plan

1. Register a prospective observation schedule and exact signal cutoff, then
   fixture-test a Massive dated-reference capture that retains stable IDs,
   CIK, form, effective date, provider update time, Dell observation time, and
   conflicts. The registered endpoint and current entitlement are useful, but
   a new bounded acquisition still requires separate network/credential
   authorization and cannot be projected backward.
2. Add daily official venue directory/notices from their first retained date
   forward. Preserve source file time, revision, venue, listing event, and
   aliases; resolve them through stable identifiers. Ticker is only a locator
   into quarantine until stable-ID corroboration succeeds.
3. Build a positive issuer-structure ledger from accepted filings and open
   legal-entity evidence. It may admit a conservative documented subset while
   leaving the rest of the fixed denominator quarantined. Absence of a label is
   never an operating-company inference.
4. Run an outcome-blind readiness census over every post-cutover TTM-ready
   issuer observation. Report admitted and quarantined counts by each lane and
   require forward/reverse replay before freezing any research sample.
5. Only if measured residuals make that prospective population unusably small,
   request a production-representative commercial point-in-time security-master
   sample. Test the same fixed rows and fields; do not substitute vendor
   marketing or broaden the requested family.

## Stopping and acquisition gates

1. Do not acquire a source until its exact lane, fields, date range, source
   clock, identifiers, request/file budget, retention permission, and finite
   sample acceptance are registered.
2. Reject any sample whose positive match depends on ticker/name, current-state
   backfill, or SEC CIK alone.
3. Stop a historical route if any of the five lanes lacks effective-dated,
   knowledge-time evidence for the frozen denominator.
4. Prefer prospective capture plus a bounded official/commercial sample when
   it can qualify the fixed future denominator; do not chase 100% coverage by
   weakening evidence.
5. Conflicts, silent omissions, ambiguous share classes, missing revisions, or
   incompatible permission remain fail-closed.

No network access, credential read, canonical write, security projection,
factor, outcome, Validation, Holdout, Candidate, Product, or Production
authority is granted.

## Implementation evidence

The pure registered plan contains 17 source/lane assessments. Its exact plan
fingerprint is
`0958b66c9b69dc031e6e71a64e9ab394559779fe52655ed9210a77aa388bb32e`;
the zero-qualified-lane evaluation fingerprint is
`3b35e9a0e46756e94f03cb23ee1fddc212015a64c2baf36711422d4065791858`.
Focused source-gap and prior applicability tests pass 6 / 6. The evaluator
made zero network requests, read zero credentials or outcomes, and wrote no
canonical data.
