# Strong-Leader Pullback SEC Case Adjudication V1

## Purpose

`strong-leader-pullback-sec-case-adjudication/1.0` performs the first finite
field adjudication over the frozen 64-case lifecycle sample. It resolves the
`stable_security_and_listing_identifiers` field only where an event-time 8-K
cover uniquely links the sampled common equity by CIK, ticker, exchange, and
effective window.

It is not a canonical Instrument Master update, lifecycle fact table,
terminal-outcome table, research input, or model admission.

## Inputs and binding

The network-disabled builder formally rereads:

- the immutable 64-case source-acceptance sample;
- the 219-request document plan and completed source package;
- the 89-document transaction candidate package; and
- the 64-case candidate-coverage census.

Plan, source-manifest, transaction, sample, and coverage identities must agree
exactly. Only the 62 retained Form 8-K documents enter this ruleset.

## Cover extraction

Every Form 8-K must expose these inline-XBRL cover facts:

- `dei:DocumentPeriodEndDate`;
- `dei:EntityCentralIndexKey`;
- `dei:EntityRegistrantName`; and
- context-aligned `dei:Security12bTitle`, `dei:TradingSymbol`, and
  `dei:SecurityExchangeName` rows.

Nasdaq names map only to `XNAS`; New York Stock Exchange or `NYSE` maps only to
`XNYS`. Unrecognized exchanges fail closed. Common-equity titles are kept
separate from debt, preferred, and rights disclosures. One incomplete
Purchase Rights context is retained explicitly and cannot affect the target
common-equity match.

## Point-in-time identity rule

The identity resolver considers a source record active only from its first
canonical observation through the provider delist-date candidate, inclusive.
A cover row matches only when one active source record uniquely agrees on:

- issuer CIK;
- trading symbol;
- normalized exchange MIC; and
- common-equity security form.

Ticker-only matching is forbidden. A same-ticker filing outside the effective
window remains unjoined. On the frozen population this excludes one later IPG
debt-exchange Form 8-K while matching 61 structured transaction documents to
61 stable-ID cases.

## Field results and authority

The report contains all 512 case/field cells. Only 61
`stable_security_and_listing_identifiers` cells are `matched`; the remaining
451 cells are `unsupported`. No absent, referenced-only, ambiguous,
conflicting, irrelevant, lifecycle-fact, terminal-outcome, canonical-write,
Historical Coverage, research-admission, Candidate, publication, deployment,
or scheduler authority is granted.

The canonical JSON report is stored in owner-only `0700/0400` custody and is
bound to code, source, ruleset, and prior-report fingerprints.
