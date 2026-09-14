# ADR 0259: Adjudicate Corrected-Terminal Core Evidence before Terminal Policy

## Status

Accepted.

## Context

ADR 0258 produces form-aware candidates for the one SCS case added by the
corrected EOD boundary. Candidate presence still does not decide point-in-time
security identity, transaction completion, listing-termination reason, or the
ordinary-share consideration structure.

The established 64-case lane has deterministic adjudicators for those four
questions. Its historical outcomes and sequence-specific decisions cannot be
borrowed, but its general evidence rules can be applied independently to the
new stable-ID chain.

## Decision

1. Create a boundary-local identity interval from the last observed stable-ID
   EOD session through the provider delist-date candidate, inclusive. This
   interval is not represented as the security's full lifecycle.
2. Resolve the 8-K common-equity cover only through point-in-time CIK, ticker,
   exchange, security form, and the retained share-class FIGI. Ticker alone is
   forbidden.
3. Require the Form 25, Form 15, 8-K cover, and retained stable-ID chain to
   agree on CIK, Commission file number, Class A Common Stock, and exchange.
   Require the Form 25 notice signature, 8-K report date, and selected
   transaction-completion date to agree, without treating that date as legal
   delisting effectiveness.
4. Reuse the registered bounded transaction-completion rules and Item 3.01
   causal-link rule. Preserve ambiguous or unsupported results rather than
   selecting a date or reason.
5. Classify only the primary ordinary-share consideration clause. Keep holder
   election, listed-stock identity, proration, fractional-share treatment,
   payoff normalization, and valuation separate.
6. Retain typed source evidence without writing canonical lifecycle facts,
   last-tradable dates, effective delisting dates, terminal reference values,
   outcomes, `/data`, Historical Coverage, research admission, Candidate,
   publication, deployment, or scheduler state.

## Consequences

SCS can receive independently reproducible core evidence while its cessation
boundary and complex election consideration remain unresolved. The report does
not reduce the terminal-gap worklist until later policies provide admissible
daily reference evidence.
