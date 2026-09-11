# ADR 0205: Admit bounded missing-type rows in historical Identity reconstruction

- Status: Accepted
- Date: 2026-09-10

## Context

The exact five-year EOD/Identity continuation stopped before publishing
2022-08-19 Identity. Its immutable 13-page package passed pagination and
custody validation, but 168 of 12,172 observations lacked provider security
type. Their 1.3802% malformed ratio exceeded the prospective 1.0% gate.

All 168 observations had a ticker, U.S. locale, stocks market, active status,
and a recognized primary exchange. Type was the only shared missing field.
They remained rejected before Instrument and Resolver construction. The
remaining evidence resolved 8,373 of 9,173 eligible observations, for 91.2788%
coverage, with zero ticker ambiguity and zero stable-identifier collision.

The retained 2022-08-22 package provides later corroboration of a provider
revision: 94 of the 168 tickers still lacked type, while 73 were then labeled
`SP` and one `FUND`. That later observation explains the discontinuity but may
not be backfilled into 2022-08-19 without creating look-ahead bias.

## Decision

Keep the prospective/current malformed-row ceiling at 1.0%. Extend only the
explicit historical-reconstruction profile to a maximum 2.0% malformed-row
ratio, alongside ADR 0201's separate 1.0% stable-identifier-collision ceiling.

Under this profile:

- every missing-type row remains rejected and absent from Instrument and
  Resolver output;
- no later type, name, security form, or eligibility is projected backward;
- exact raw counts, malformed counts, ratios, and applied gates remain in the
  immutable snapshot and Apply-plan evidence;
- the existing 80% eligible-identity coverage, ticker-ambiguity, pagination,
  request-count, and all other gates remain unchanged; and
- any historical session above 2.0% malformed, or failing another gate, still
  stops for separate review.

The 2.0% ceiling contains the observed 1.3802% missing-type discontinuity with
bounded headroom. It does not reclassify missing evidence as valid or establish
Massive's later-vintage reference endpoint as point-in-time classification.

## Consequences

- One bounded provider classification gap does not discard thousands of
  independently resolved identities or block adjacent EOD acquisition.
- The 168 rows stay visible as rejected source evidence and cannot enter a
  Universe, Membership, signal, validation, or performance population through
  this reconstruction.
- Future lifecycle or classification evidence may resolve an effective-dated
  record append-only; it cannot rewrite this source observation.
- The five-year Identity family remains latest-vintage reconstructed evidence,
  not `as_operated` point-in-time truth.

## Supersession scope

This decision supersedes ADR 0116 only for the explicitly selected historical
reconstruction profile's malformed-row ceiling. It does not change
prospective/current Identity, stable-ID priority, Universe eligibility,
classification authority, research admission, or Production behavior.
