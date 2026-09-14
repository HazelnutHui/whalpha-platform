# ADR 0248: Reuse Complementary SEC Evidence before Requesting One Residual Registration Document

## Status

Accepted.

## Context

Three listed-stock consideration identities remain unresolved after the first
registration-document adjudication. Their evidence gaps are not equivalent.

The IonQ/SkyWater and Boeing/Spirit registration documents prove the exact
transaction, target common security, and issuer common-share class, but state a
variable exchange-ratio formula rather than the final closing ratio. Their
already retained target completion 8-K filings independently state the final
ratio and both security terms.

The retained Fifth Third 424B3 is an unrelated senior-notes offering. The
retained SEC Submissions snapshot also contains an earlier Fifth Third 424B3
row dated 2025-11-25 whose accession and primary-document identity differ from
the notes filing and align with the merger registration sequence.

## Decision

Freeze a three-case residual plan with two paths:

1. IonQ/SkyWater and Boeing/Spirit require no new source request. A later
   adjudicator may combine the existing issuer-filed registration document
   with the target-filed completion disclosure, but only after proving the
   transaction, both security classes, final ratio, and existing CIK-to-stable-
   security chain together.
2. Fifth Third/Comerica requires exactly one replacement source document: the
   official 2025-11-25 424B3 identified by accession
   `0001193125-25-297171` and primary document `d942117d424b3.htm` in the
   retained Submissions archive.

Do not repeat a global filing or vendor scan. Do not let company names, tickers,
an expected ratio, or a unique-looking candidate assign security identity.

## Consequences

Only one network document request remains in this identity subproblem. Two
cases can be adjudicated entirely from retained official evidence, reducing
both latency and source sprawl.

This plan assigns no identity and creates no terminal value, outcome, strategy
label, return, `/data` or Historical Coverage write, research admission,
Candidate result, publication, deployment, or scheduler change.
