# ADR 0264: Extend Terminal-Gap Census with Local Daily Reference Evidence

## Status

Accepted.

## Context

Terminal-gap census V3 leaves 22 securities and 105 five-session paths
without a daily reference. Retained, already-adjudicated SEC evidence and
canonical EOD contain enough information to close five cases without an
external request. Rewriting earlier reports would erase evidence vintage.

## Decision

1. Create immutable census V4 as an extension of the exact V3 report.
2. Add fixed-cash references for RNAM, TERN, and PLYM only where source-stated
   halt timing and stable-ID EOD absence agree.
3. Use the contractual no-valid-election default for THR and FL. Value THR's
   listed CECO component from the same-session unadjusted close only after SEC
   profile and canonical stable-ID identity agree. Do not treat either value
   as an observed holder election or execution price.
4. Preserve SNV as unresolved because the retained successor filing and the
   canonical PNFP stable-ID identity do not form a strict CIK chain.
5. Recompute remaining states and path impacts from the full V3 decision set.
6. Keep outcomes, labels, `/data`, Historical Coverage, research admission,
   publication, deployment, scheduler changes, and network requests at zero.

## Consequences

Reference evidence increases from 43 to 48 of 65 securities. Seventeen cases
remain quarantined. V4 measures narrower terminal-reference coverage; it does
not complete lifecycle evidence or authorize strategy returns.
