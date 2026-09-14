# ADR 0263: Extend Terminal-Gap Census with Corrected Listed Reference

## Status

Accepted.

## Context

Terminal-gap census V2 classified SCS as a newly in-scope unadjudicated case.
ADR 0262 subsequently established one strict HNI listed-security assignment
and three SCS daily reference alternatives. Rewriting V2 would destroy its
evidence vintage, while treating three alternatives as three cases would
overstate coverage.

## Decision

1. Create terminal-gap census V3 as an immutable extension of the exact V2
   report and the exact corrected listed-reference report.
2. Replace only the stable-ID-bound SCS decision, from newly in-scope source
   review to documented gross listed-consideration reference evidence.
3. Count SCS once at instrument/path level despite retaining three valuation
   alternatives. Use the SCS filing acceptance time as label maturity and keep
   the unverified-adjustment flag visible.
4. Recompute every state and horizon impact from the full 65-decision set.
   Preserve all other V2 decisions byte-logically unchanged.
5. Keep terminal outcomes, forward labels, performance, `/data`, Historical
   Coverage, research admission, Candidate, publication, deployment, and
   scheduler state at zero.

## Consequences

The corrected scope remains 65 securities and 302 five-session paths.
Documented references become 43 securities and 197 paths; 22 securities and
105 paths remain. SCS still requires the later lifecycle/label policy before
it can become a terminal outcome.
