# ADR 0299: Freeze the SEC Cash-Earnings-Quality Source-Engineering Plan

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0298 closed the U.S. successor intake at `closed_source_blocked`. The SEC
foundation contains as-filed Company Facts, filing clocks, and a conservative
filer/security projection path, but raw CFO, net-income, and Assets concept
presence does not establish the exact cash-earnings-quality formula. The
required four-quarter chain, amendment-time behavior, security identity,
nonfinancial applicability, joint coverage, and replay gates remain
unqualified.

The closed intake cannot be reopened by source engineering. A source plan must
therefore freeze the missing semantics without creating a feature, reading an
outcome, registering a trial, or treating reconstructed identity as strict
point-in-time evidence.

## Decision

1. Adopt
   `quant-research-sec-cash-earnings-quality-source-plan/1.0` as a plan-only,
   outcome-blind contract bound to the frozen cash-quality hypothesis, the
   closed successor source-qualification report, and the current SEC
   fundamental query registry.
2. Freeze the only admitted concepts for this version:
   `us-gaap:NetCashProvidedByUsedInOperatingActivities`,
   `us-gaap:NetIncomeLoss`, and `us-gaap:Assets`, in USD, from admitted
   10-K/10-Q filings and amendments. Concept, namespace, or IFRS fallback is
   not authorized.
3. Construct discrete quarters only as Q1 reported, Q2 YTD minus Q1, Q3 YTD
   minus Q2 YTD, and FY minus Q3 YTD within the same fiscal year. TTM CFO and
   TTM net income are the latest four consecutive discrete quarters known by
   the cutoff. Average Assets is the arithmetic mean of the opening and
   closing TTM-boundary Assets.
4. Use the conservative SEC acceptance clock. A later clean amendment changes
   only cutoffs at or after its own availability and never rewrites an earlier
   snapshot. CFO and net income at each cumulative endpoint must share one
   clean accession. Value, time, period-shape, or amendment-basis conflicts
   quarantine the complete chain.
5. Project only through stable `instrument_id`, an admitted unique CIK link,
   and the single-common-security-per-CIK/session class. Ticker, name, CIK
   broadcast, and multi-common-security projection are forbidden. Strict and
   reconstructed evidence tiers remain separate and cannot be promoted.
6. Require effective-dated, point-in-time nonfinancial applicability evidence.
   Financial or unknown applicability remains quarantined; current sector or
   SIC backfill is forbidden.
7. A later outcome-blind coverage report must use the exact 106 closed-campaign
   Development dates and point-in-time Primary Membership without labels. It
   stops below 96 complete sessions, below 48 complete sessions in either
   chronological half, below 500 complete instruments in any admitted
   session, or below 75% joint formula availability.
8. Any later coverage report must bind every source, identity, applicability,
   formula, session-index, and implementation fingerprint and receive one
   independent byte-identical replay. Replay mismatch stops without feature or
   trial authority.
9. This contract does not authorize source execution, external requests,
   feature materialization, a coverage run, Development outcomes, Validation,
   Holdout, formal trials, model input, Candidate use, canonical writes, or
   Production writes. Every such transition requires a separate review.

## Consequences

Cash-quality source engineering now has one deterministic target and cannot
silently replace TTM values with annual facts, use current restatements or
classifications historically, broadcast filer facts across securities, fill
missing components, or reinterpret raw concept counts as feature coverage.

ADR 0298 remains the authoritative successor-intake state. Even a future
successful source qualification would require a new intake version before any
outcome protocol or formal trial could be proposed.

ADR 0300 now completes the first declarative step through a separate exact
query registry. It deliberately leaves the immutable first SEC registry
unchanged and still authorizes no query execution or occurrence selection.

## Rejected alternatives

- calculate a factor immediately from raw Company Facts presence;
- use annual CFO or annual net income as TTM;
- substitute EBITDA, operating income, or free cash flow for CFO;
- mix concepts from incoherent original/amended filing bases;
- use current industry classification to remove historical financial issuers;
- project one filer value to every linked share class; or
- run coverage or read outcomes as part of approving this plan.
