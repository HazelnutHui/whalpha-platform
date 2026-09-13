# ADR 0235: Measure Cross-Document Case Coverage Before Adjudication

- Status: Accepted
- Date: 2026-09-13

## Context

The frozen document population is fully acquired and form-aware extraction is
complete, but its 219 documents are unevenly distributed across 64 lifecycle
cases. Sixty-one cases have a structured 8-K completion scope. One has only
Form 25/Form 15 notices, one has a 6-K that references an absent completion
exhibit, and one has only unrelated-form proxy materials. Other cases contain
repeated notices, tender amendments, multiple Commission file numbers, or
additional issuer events.

Candidate contexts still mix different legal semantics, securities, dates,
amounts, parties, and revisions. Counting a keyword, joining on CIK, or finding
one source document does not establish a complete security-level field.

## Decision

1. Join only by the stable-ID locator already frozen in the outcome-blind
   source sample and require the exact 64-ID population across all packages.
2. Require the Form 25, Form 15, and transaction packages to share identical
   plan, source, and content-census identities and total exactly 219 documents.
3. Record form-family and structure coverage, repeated-document conditions,
   referenced-body gaps, and partial candidate counts for every case.
4. Keep candidate presence separate from complete result state. All eight
   fields for all 64 cases remain `unsupported` until typed candidate values,
   security identity, and cross-document semantics are adjudicated.
5. Keep matched, absent, ambiguous, conflicting, and irrelevant counts at zero
   rather than claiming those states before evaluating them.
6. Prohibit network, `/data`, fact, outcome, research, Candidate, publication,
   deployment, and scheduler authority.

## Consequences

- The exact residual review population becomes measurable without overstating
  what source acquisition achieved.
- Missing last-tradable and bankruptcy/liquidation/OTC evidence can be
  distinguished from fields with abundant but unadjudicated candidate text.
- Any commercial sample can be scoped to the measured residual rather than a
  new global vendor search.

## Rejected alternatives

### Mark candidate presence as a matched field

Rejected because a source fragment may concern another class, a proposed
transaction, a revision, a debt exchange, or a different effective date.

### Treat a missing candidate as an absent event

Rejected because primary documents may reference exhibits or omit external
exchange, OTC, liquidation, and market-status evidence.
