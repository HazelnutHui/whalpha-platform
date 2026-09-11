# ADR 0206: Roll the Initial Feature Warm-Up Inside Starter Source Coverage

- Status: Accepted
- Date: 2026-09-11

## Context

ADR 0196 defined a rolling five-calendar-year source foundation and initially
froze 2021-09-09 through 2026-09-09 as a 1,255-session acquisition interval.
The completed bounded backfill retained 1,253 EOD sessions beginning
2021-09-13. Massive Stocks Starter subsequently denied both 2021-09-09 and
2021-09-10 through REST and denied the older Flat File object while a current
Flat File control succeeded. The stop is the provider's wall-clock rolling
history boundary, not a corrupt package, credential failure, or unexplained
data gap.

Buying deeper history solely to preserve two expired boundary sessions and a
separate pre-window warm-up would add cost without changing the main remaining
research blockers: corrected EOD source custody, point-in-time Membership,
lifecycle and terminal evidence, corporate-action reconciliation, and sealed
Historical Coverage. The owner selected the no-upgrade route for this initial
program.

## Decision

Keep the five-calendar-year **source foundation** in ADR 0196, but do not claim
that every session in its first retained window is performance-eligible.

1. Do not reacquire or repeatedly retry 2021-09-09 or 2021-09-10 under Stocks
   Starter. Preserve the stopped 1,255-session run and its gaps as historical
   execution evidence.
2. Let normal daily EOD/Identity updates advance the latest canonical session.
   When the latest completed session reaches 2026-09-11, the ordinary ADR 0196
   calculation anchors at 2021-09-11 and selects 2021-09-13 as the first XNYS
   session. A fresh network-disabled census, not this ADR, must verify the
   resulting target and counts.
3. Retain the first 20 sessions of the available target as outcome-free feature
   warm-up for the first registered strategy. With the expected 2021-09-13
   start, those sessions end 2021-10-08 and the earliest eligible signal and
   performance session is 2021-10-11. An experiment needing a longer lookback
   starts later; it may not backfill features from unavailable history.
4. Describe the resulting performance interval as the available rolling
   window after declared warm-up, not as a full five-year performance test.
   The five-year label applies to retained source scope.
5. Retain the already published 2021-09-10 Identity partition and all source
   evidence append-only even after they fall outside the active target. Do not
   delete or project them into an in-scope session.
6. Leave the optional external warm-up fields and separate workspace mechanics
   available for a future explicitly deeper dataset, but do not populate the
   reserved 2021-08-11 through 2021-09-08 workspace in the current Starter
   program.

The five-year census remains source-incomplete while its latest canonical EOD
is 2026-09-09. No date is removed from an already emitted census merely to make
it pass. Completion may change only after a normal daily append moves the
calculated rolling target and formal readback succeeds.

## Consequences

- No subscription upgrade or second price provider is required for the initial
  rolling source window.
- Approximately one trading month at the left edge is used for feature
  initialization rather than performance measurement. This limitation is
  explicit and reproducible.
- Historical audits and fixed-interval acquisition artifacts remain truthful;
  they are no longer the active retry plan.
- Corrected EOD edition construction and the other point-in-time evidence
  families remain required. This decision does not authorize backtesting,
  performance claims, Candidate activation, `/data` writes, publication, or
  deployment.

## Supersession scope

This decision supersedes ADR 0196 and ADR 0197 only where their initial frozen
dates or external pre-window warm-up are treated as the active next action for
the first Starter-backed research program. It does not weaken their point-in-
time, complete-session, stable-identity, retention, quarantine, or source-
governance requirements. It supersedes the pending purchase/reconciliation
recommendation in the 2026-09-11 terminal and Flat File pilot audits; those
recommendations remain preserved as dated history.
