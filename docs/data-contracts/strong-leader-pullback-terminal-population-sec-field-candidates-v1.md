# Strong-Leader Pullback Terminal-Population SEC Field Candidates V1

## Purpose

`strong-leader-pullback-terminal-population-sec-field-candidates/1.0` converts
the authoritative corrected-population SEC content into form-aware candidate
records. It is an extraction package, not a fact or outcome report.

## Inputs and binding

The operation formally rereads and binds:

- the authoritative source plan physical and logical identities;
- the complete source manifest, logical identity, and artifact binding; and
- the deterministic content-census physical and logical identities.

All three inputs must agree on the plan, source, three-document count, ordered
sequences, physical document hashes, and one stable `instrument_id`. The form
set must contain exactly one 25-NSE, one 8-K, and one 15-12G.

## Candidate records

- Form 25 reuses the structured exchange-notice parser for issuer CIK locator,
  Commission file number, issuer, exchange, security class, selected rule, and
  notice signature date.
- Form 15 reuses the field parser for Commission file number candidates,
  covered security-class fragments, certification-date candidates, and
  selected rule controls.
- Form 8-K reuses the transaction parser to identify the document structure,
  bounded explanatory-note/Item 2.01 scope, normalized source identity, and
  unresolved transaction-field contexts.

Every nested record retains its original non-authority flags. Partial-field
counts describe candidate coverage only; all eight complete lifecycle-field
support counts remain zero.

## Custody and non-authority

The canonical JSON is exclusively written beneath an owner-only `extraction=*`
directory, atomically published, and formally reread. Directories are `0700`
and the report is `0400`; an exact replay is idempotent and a changed replay
fails closed.

The package assigns no listed-security identity, transaction completion,
lifecycle fact, terminal date, payoff, outcome, trigger, forward return,
performance metric, parameter, `/data`, Historical Coverage, research
admission, Candidate state, publication, deployment, or scheduler state. It
performs zero network requests and reads no credential.
