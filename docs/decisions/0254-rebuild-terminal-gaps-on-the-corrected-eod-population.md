# ADR 0254: Rebuild Terminal Gaps on the Corrected EOD Population

## Status

Accepted.

## Context

ADR 0253 proves that the first terminal-gap census used an Instrument Master
observation boundary where terminal planning required canonical EOD presence.
The corrected five-session population can differ from the frozen 64-security
source sample. Discarding the prior report would erase lineage; continuing to
use it would undercount affected paths and could silently omit a security.

The retained inactive-lifecycle shadows contain stable identifiers and source
locators for any corrected-population addition. Existing payoff and reference-
value reports remain valid evidence for their own cases; only their affected
path counts need to be remapped to the corrected boundary.

## Decision

1. Preserve the V1 terminal-gap report as the immutable prior calculation and
   bind it into a V2 successor.
2. Require the prior 64 IDs and their legacy 1/3/5-session counts to reproduce
   exactly across the source sample, V1 gap report, and ADR 0253 boundary
   report.
3. Define the V2 population as every stable ID with at least one corrected
   five-session EOD-boundary crossing. No legacy case may disappear silently.
4. Recover locators for newly in-scope IDs only from the formally reread
   inactive-lifecycle source/decision chain. Do not use ticker matching or a
   current company lookup.
5. Preserve every prior evidence-state decision for the original population.
   Recalculate only 1/3/5-session impact counts from ADR 0253. Put a newly in-
   scope case into its own primary-source-adjudication state.
6. Keep daily cash or listed-security reference values distinct from terminal
   outcomes. The V2 report remains result-blind and grants no research,
   canonical data, Candidate, publication, deployment, or scheduler authority.

## Consequences

- The terminal worklist is complete under the corrected EOD boundary.
- Existing source and adjudication work is reused rather than repeated.
- Newly discovered cases cannot borrow the authority of the original 64-case
  SEC sample; they must pass their own primary-source chain.
- Future coverage and admission contracts must bind V2, not the superseded V1
  population counts.
