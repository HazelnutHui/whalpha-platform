# ADR 0233: Extract Form 15 Fields Without Inferring Effective Status

- Status: Accepted
- Date: 2026-09-13

## Context

The frozen first-strategy transition package contains 66 Form 15 documents:
63 Form 15-12G and three Form 15-15D. Unlike the standardized Form 25
population, their HTML varies. Bounded structure nevertheless exposes
Commission file-number candidates, security-class text, selected rule
controls, and certification dates.

Two documents legitimately contain two Commission file numbers. One
certification predates its filing by one calendar day. Security descriptions
may span multiple text nodes or cover multiple classes. These differences must
not be forced into a single-value Form 25 schema.

Form 15 concerns termination of registration or suspension of reporting duty.
It does not by itself establish the last tradable date, exchange-delisting
effective date, security-level identity, transaction outcome, or terminal
return required by the historical research database.

## Decision

1. Extract each field independently through fixed labels, ordered text nodes,
   bounded look-ahead, and exact adjacent selected-control marks.
2. Preserve zero, one, or multiple candidates and an explicit field state.
   An unrecognized template is `unsupported_template`, never a guessed value.
3. Keep ordered security-class text fragments as source text; do not assert
   that each fragment is a distinct listed-security class.
4. Preserve the certification date and its relationship to filing date. Do
   not require equality or promote either date to effective status.
5. Normalize only the six registered Form 15 rule codes and accept only known
   selected marks adjacent to the code. Do not borrow a neighboring checkbox.
6. Bind the report to the immutable plan, source package, and content census;
   prohibit network access and all canonical/research/Production authority.
7. Keep all eight complete lifecycle fields and every terminal field null.

## Consequences

- The full Form 15 population becomes machine-reviewable without pretending
  its legal and security-level semantics are complete.
- Template differences and multi-value filings remain visible for later
  adjudication.
- Transaction filings and corroborating market/lifecycle sources remain
  necessary before terminal outcomes can be admitted.

## Rejected alternatives

### Reuse the strict Form 25 schema

Rejected because it would either discard legitimate multi-value Form 15
evidence or force false single values and date equality.

### Treat filing or certification as the effective lifecycle date

Rejected because registration/reporting status, exchange trading status, and
terminal security outcome are separate facts with separate effective dates.
