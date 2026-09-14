# ADR 0261: Model Corrected-Terminal Election as Default plus Sensitivity

## Status

Accepted.

## Context

SCS has a matched daily cessation boundary, but each target common share could
receive one of three source-stated consideration alternatives: mixed cash and
HNI shares, primarily cash plus a small HNI-share component, or HNI shares.
The retained completion filing says that a holder who made no valid election
received the mixed alternative. It also says the alternatives were subject to
automatic adjustment but does not state proration mechanics in the bounded
completion scope.

A daily research engine does not model or submit holder elections. Selecting
the highest-valued alternative would add look-ahead bias; selecting a supposed
population average without election results would invent data. Keeping the
case wholly unresolved would discard an explicit contractual default.

## Decision

1. Independently bind the source-local HNI/Steelcase party relation and target-
   absorption topology without assigning any global counterparty or listed-
   consideration stable ID.
2. Normalize the five exact common-share payoff terms into three alternatives:
   mixed, cash, and stock. Preserve fractional-share cash separately.
3. Retain the source-stated reference price only as calculation context; it is
   not the later daily terminal reference price.
4. Identify `mixed_election` as the contractual outcome for no valid election.
   The future daily backtest convention is therefore
   `default_no_valid_election_mixed_with_alternative_sensitivity`: use the
   no-action default as the primary reproducible path and report all three
   alternatives as sensitivity, never as three realized outcomes.
5. Preserve actual holder election as unknown. Preserve proration and automatic-
   adjustment mechanics as unresolved when absent from the retained completion
   scope. Do not silently infer either from the word `election`.
6. Keep listed HNI security identity, daily market value, payoff value, terminal
   outcome, canonical lifecycle facts, `/data`, Historical Coverage, research
   admission, Candidate, publication, deployment, and scheduler state outside
   this evidence package.

## Consequences

The case gains a deterministic and explicit future backtest convention without
claiming to know an actual holder's election. The next gate is strict HNI
listed-security identity at the event boundary, followed by valuation of the
default mixed path and the full alternative range on the first absent target
session. Until then the terminal-gap count does not change.
