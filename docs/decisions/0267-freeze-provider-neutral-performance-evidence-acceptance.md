# ADR 0267: Freeze Provider-Neutral Performance-Evidence Acceptance

## Status

Accepted

## Date

2026-09-15

## Context

Strong-Leader Pullback method engineering is complete, while its formal
performance gate remains `rejected_data_blocked`. The frozen source-acceptance
population already contains every unresolved first-strategy action case and
every five-session lifecycle crossing. No real LSEG, ICE, S&P, or other
production-representative sample has been received.

Waiting to define acceptance until after a provider sample arrives would let
the observed coverage, conflicts, or commercial terms influence the rule.
Building a provider-specific adapter from marketing material would also make
the first available source an accidental authority.

## Decision

Implement one pure, provider-neutral acceptance evaluator before any new
sample is opened. It must:

1. bind the exact immutable 20-action / 64-lifecycle sample and reject a
   missing, duplicated, substituted, or reordered case population;
2. distinguish `matched`, `absent`, `unsupported`, and `conflicting` source
   results rather than treating a missing response as evidence of no event;
3. assess every frozen required field for every case as `provided`,
   `explicit_not_applicable`, `missing`, `unsupported`, or `conflicting`;
4. require positive stable-security identity, revision/availability semantics,
   effective lifecycle/action facts, and terminal terms where applicable;
5. evaluate production-sample representativeness and the permissions needed
   for private Dell research, retained evidence, identifier use, and public
   display of derived metrics;
6. return only `sole_primary_candidate`, `corroborator_only`, or `rejected`;
   even the strongest result remains a candidate requiring a separate source
   mapping, canonical promotion, and performance-admission review; and
7. contain no provider transport, credential access, network request,
   canonical write, outcome, parameter selection, Candidate authority,
   publication, deployment, or scheduler action.

`explicit_not_applicable` is valid only when the source positively represents
that state with retained evidence. It is prohibited for stable identifiers,
event identity/revisions, source-availability semantics, trading-status dates,
last-tradable evidence, termination reason, and the exact ratio or
consideration for a frozen action case.

## Consequences

- Every candidate provider is judged by the same pre-outcome rules.
- A partial source can remain a corroborator without being promoted by a
  coverage percentage or first-non-null merge.
- A complete synthetic test proves evaluator mechanics only. It is not a real
  provider result and does not change `rejected_data_blocked`.
- The next external step remains one production-representative sample bound to
  the frozen population. No particular vendor is mandatory.

## Rejected alternatives

### Implement the LSEG adapter immediately

Rejected because no reviewed schema, sample, entitlement, permission, or
delivery contract exists.

### Accept a high coverage percentage

Rejected because the unresolved cases are economically non-random and a
percentage could conceal the exact terminal or corporate-action omissions that
create survivorship bias.

### Treat provider silence as a neutral event

Rejected because no-result, not-covered, unsupported, and true absence are
different facts.
