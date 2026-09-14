# ADR 0240: Adjudicate Source Party Relations before Resolving Global Identities

## Status

Accepted.

## Context

The first-strategy SEC sample has 61 stable-security links, typed transaction
completion dates, merger/acquisition termination reasons, and primary
common-share consideration clauses. The same filings use source-local labels
such as `Company`, `Parent`, `Purchaser`, `Merger Sub`, and `Surviving Entity`.
Those labels prove a transaction topology only inside the filing; they are not
global issuer or security identifiers.

Ticker matching, current company names, and generic role labels cannot safely
assign a predecessor, acquirer, successor, or consideration issuer. Complex
two-step mergers and a new-holding-company combination make that distinction
material to terminal-return research.

## Decision

Adjudicate the frozen 61-case population through a finite, source-hash-bound
review registry. For each case, retain both:

- the exact bounded clause that defines the agreement parties; and
- the exact bounded clause that states the merger direction and surviving
  legal entity.

Classify only three source topologies:

- the target legal entity survives as an owned subsidiary;
- the target legal entity is absorbed into another surviving entity; or
- the target and a peer are absorbed into a new holding company.

Bind the target security through the already adjudicated cover identity,
transaction event, termination reason, and common-share consideration. Keep
source-local party names and role labels inside the retained evidence. Do not
assign a global stable ID to the acquirer, successor, merger vehicle, or
consideration issuer in this stage.

## Consequences

The `predecessor_successor_and_acquirer` evidence field can be resolved at the
source-topology level without manufacturing canonical party identities. A
later identity-resolution stage may map the retained parties to stable issuer
and security IDs using point-in-time evidence. Tradability, terminal pricing,
canonical lifecycle facts, terminal outcomes, and research admission remain
separate gates.
