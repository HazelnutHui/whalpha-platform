# ADR 0260: Bind Corrected-Terminal Cessation to Stable-ID EOD Presence

## Status

Accepted.

## Context

ADR 0259 matched the SCS point-in-time common-equity identity, transaction
completion, merger/acquisition listing-termination reason, and holder-election
consideration structure. Its retained Item 3.01 text also states an exact
trading-halt boundary, but neither that statement nor a provider delist date
alone proves the last retained daily observation or legal delisting
effectiveness.

The earlier 61-case cessation report used a finite, sequence-specific human
review registry. SCS was discovered only after the EOD boundary correction and
must not inherit a timing decision from that historical population.

## Decision

1. Independently select one realized trading-stop sentence from the SCS Item
   3.01 evidence only when it contains an explicit halt/cessation action, a
   before-open timing phrase, and one unambiguous calendar date.
2. Require the selected boundary date to agree with the already adjudicated
   issuer transaction-completion date. A request to halt is not preferred over
   a sentence stating that trading actually halted.
3. Resolve the immediately preceding and following exchange sessions from the
   canonical EOD session index. Formally reread only the prior, expected-final,
   and next sessions through the stable-ID instrument-presence boundary.
4. Classify the comparison as `matched` only when the target stable ID is
   present on the expected final EOD session and absent on the next exchange
   session. Preserve any disagreement as `conflicting`; preserve missing or
   ambiguous source timing as `unsupported`.
5. Describe the supported result as a source-stated trading-stop boundary and
   last retained EOD observation. It is not a legal delisting-effective date,
   proof of an intraday execution, or a complete lifecycle fact.
6. Write only one immutable owner-only private evidence report. Do not write
   `/data`, terminal values, outcomes, Historical Coverage, research admission,
   Candidate, publication, deployment, or scheduler state.

## Consequences

The corrected SCS case can be compared under the same evidence standard as the
earlier cessation population without importing its sequence registry. A match
resolves the daily cessation boundary needed by later terminal-policy work,
but the holder-election/proration terms still prevent a deterministic terminal
reference value and keep the terminal-gap count unchanged.
