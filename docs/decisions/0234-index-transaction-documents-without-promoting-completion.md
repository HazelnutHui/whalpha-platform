# ADR 0234: Index Transaction Documents Without Promoting Completion

- Status: Accepted
- Date: 2026-09-13

## Context

After Form 25 and Form 15 extraction, 89 frozen documents remain. They are not
one homogeneous completion population. Sixty-one 8-Ks contain an Item 2.01
completion section, while one later 8-K for a repeated issuer concerns a debt
exchange and has no Item 2.01. Twenty-four filings are amended tender schedules.
Two DEFA14A filings concern annual-meeting materials. One 6-K cover document
only references an exhibit titled as a completed arrangement; the retained
primary document does not contain that exhibit body.

Broad matching of `merger`, `completed`, or `per share` would mix completion,
proposal, agreement, debt, compensation, boilerplate, and referenced-but-
absent content. CIK-level filing relevance also does not prove that the sampled
listed security is the affected class.

## Decision

1. Classify each document by exact form-aware structure before extracting
   evidence contexts.
2. For 8-K Item 2.01 records, bound the core transaction scan to the last
   preceding Introductory/Explanatory Note through the end of Item 2.01.
   Preserve the sole 8-K without Item 2.01 separately.
3. Treat tender amendments as amendment evidence, DEFA14A as having no
   registered completion scope, and the 6-K as a referenced-exhibit-only
   candidate. Do not fetch or synthesize omitted exhibit content.
4. Register six finite marker families and retain counts plus at most three
   hashed contexts. Every hit is an unresolved source candidate; absence means
   only absence from the retained primary document.
5. Extract date tokens only from retained contexts. Do not decide which date,
   amount, ratio, party, or class is the terminal value at this stage.
6. Recompute the normalized document identity and require exact agreement with
   ADR 0231 before accepting a record.
7. Bind the report to the immutable plan, source, and census; prohibit network,
   `/data`, lifecycle, research, Candidate, publication, deployment, and
   scheduler authority.

## Consequences

- All retained transaction documents become reviewable without flattening
  unrelated forms or duplicated issuer filings into a false completion fact.
- The 6-K referenced-exhibit gap and two non-completion proxy materials remain
  explicit rather than silently ignored.
- A later reconciliation stage must decide supported, absent, ambiguous, or
  conflicting security-level fields and measure the remaining source gap.

## Rejected alternatives

### Mark every retained post-observation filing as completion evidence

Rejected because the frozen plan intentionally maximized source recall and
contains issuer-level documents that are irrelevant to the sampled security.

### Download every referenced exhibit before measuring the primary documents

Rejected because only one explicit referenced-body gap remains. It should be
measured and separately planned instead of silently expanding source scope.
