# ADR 0268: Admit Reconstructed Research Only with Adversarial Missingness Bounds

- Status: Accepted
- Date: 2026-09-15

## Context

The first-strategy method diagnostic has 274 complete same-session feature
cross-sections inside its frozen 287-session population, exceeding the
pre-registered 252-session floor. Thirteen whole sessions remain excluded
before outcomes: twelve because a 21-session input window intersects
quarantined split evidence and one because the reconstructed Regime cannot be
initialized. No partial cross-section was ranked.

The prior admission gate nevertheless reports zero complete sessions because
it requires every sparse adjustment omission, lifecycle field, and terminal
outcome to be exact. The remaining terminal gap is 88 of 302 crossing paths
across 18 securities. Those gaps are non-random, so silently dropping them is
not acceptable. Requiring a single commercial source before any result is
also stronger than normal retrospective research practice and has led to a
stop without improving the method.

## Decision

Create a separate **reconstructed research** admission. It does not relabel
the data as observed `as_operated` and does not weaken Production or live-signal
knowledge-time rules.

1. Feature ranks still require an all-member same-session cross-section. A
   missing or hazardous member rejects that complete feature session; no
   coverage-selected stock subset is allowed.
2. At least 252 complete feature sessions remain required. Exclusion reasons,
   sessions, paths, and fingerprints are fixed before any outcome is read.
3. A naturally completed and independently range-reconciled split source may
   establish a neutral mechanical adjustment only inside its exact frozen
   source range when repeated economic rows agree, known terms alone are
   applied, unresolved action-hazard sessions are excluded, and adjustment is
   never used as a predictor. This grants no historical announcement-time
   claim and never turns a price jump into an inferred action.
4. Every terminal-crossing path must have either an exact terminal reference
   value or a finite pre-outcome reference interval before a return label can
   be constructed. The lower floor for a long underlying-stock return is
   -100%. An upper bound must be supported by transaction terms or retained
   market evidence; otherwise the path stays unbounded and admission fails.
5. Interval-censored labels are never point-imputed or omitted from a headline
   statistic. Development selection and later validation must be repeated
   adversarially over the allowed endpoints. A parameter choice or gate that
   changes under the adverse assignment fails rather than being rescued by a
   complete-case result.
6. A positive V2 admission may open development-label construction and
   development-only parameter selection. Validation remains a separate locked
   transition and the holdout remains sealed and single-use. Performance
   claims, Candidate activation, Production, publication, and deployment stay
   unauthorized.
7. Lab disclosure must say `reconstructed latest-vintage retrospective
   research`, show exact versus interval-censored counts separately, and never
   describe an underlying-stock result as an option return.

## Consequences

ADR 0195 remains authoritative for the stronger claim that every historical
row is exact and as-operated. It no longer prevents a separately labelled,
adversarially bounded retrospective research run. This decision does not
guarantee admission: the existing 88 terminal-gap paths first need finite
interval evidence. A free source or official filing that narrows an interval
is useful, but no vendor name is mandatory and no unresolved value may be
guessed.

The new pure evaluator contains no return, provider transport, credential,
canonical write, parameter selection, holdout access, or Production action.
It makes the next blocker finite: construct and verify bounds for the 18
remaining terminal cases, then rerun this gate.
