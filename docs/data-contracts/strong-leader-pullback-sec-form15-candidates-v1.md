# Strong-Leader Pullback SEC Form 15 Candidates V1

## Purpose

`strong-leader-pullback-sec-form15-candidates/1.0` extracts bounded, field-
level candidates from all Form 15 documents in the frozen transition-period
package. It preserves template variation and does not convert a certification
or notice into a security lifecycle fact.

## Inputs

The network-disabled builder formally rereads and binds the ADR 0229 document
plan, ADR 0230 source package, and ADR 0231 content census. Their plan and
source identities must reconcile exactly.

## Record fields

Each of the 66 records retains:

- request sequence, stable-ID and issuer-CIK locators, accession, form, filing
  and acceptance times, and physical document hash;
- zero, one, or multiple Commission file-number candidates with an explicit
  extraction state;
- ordered security-class text fragments bounded by the form's address and
  class-title labels;
- zero, one, or multiple certification-date candidates, including their
  relationship to the filing date; and
- rule provisions only when an exact adjacent selected-control mark is
  present.

The known template marks `☒`, `☑`, `x`, `X`, `[x]`, and `[X]` are selected.
Unchecked or unknown marks are not. A field that cannot be recognized is
`unsupported_template`; it is never populated by narrative inference.

## Population and authority

Completion requires 66 documents (63 Form 15-12G and three Form 15-15D), 62
stable-ID locators, three repeated IDs, a maximum of three documents for one
ID, full aggregate reconciliation, canonical JSON, and `0700/0400` custody.

Security-class values are deliberately retained as text fragments rather than
asserted class identities. Multiple Commission file numbers remain multiple
candidates. Certification and filing dates may differ legitimately.

All eight complete lifecycle fields, listed-security identity assignments,
terminal outcomes, strategy outcomes, `/data`, Historical Coverage, research
admission, Candidate, publication, deployment, and scheduler counts remain
zero.
