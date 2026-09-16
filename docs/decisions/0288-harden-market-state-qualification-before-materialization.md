# ADR 0288: Harden Market-State Qualification Before Materialization

## Status

Accepted

## Date

2026-09-16

## Context

ADR 0286 separated Campaign Three's market-state input from the Product Regime
and kept outcomes closed. Independent governance, implementation, and method
reviews then found several defects before any real panel was materialized:

- the draft ETF breadth metric had only five possible values while the frozen
  diversity gate required at least twenty;
- a declared member count could not prove that every stable security ID had
  been included or explicitly quarantined;
- calendar continuity, source identity, code identity, limitations, and exact
  Membership manifests were not all bound into one report;
- full-panel quantiles could be mistaken for historical state thresholds; and
- coverage alone did not describe persistence, episodes, or redundancy.

Running the draft against real data would therefore have created either a
guaranteed false rejection or an apparently complete report with an
insufficient population and chronology proof.

## Decision

1. Replace the never-materialized five-level ETF breadth draft with the
   continuous mean log distance of SPY, QQQ, IWM, and DIA from their own
   20-session moving averages. The vector contract advances to 1.1; no prior
   real artifact is rewritten.
2. Freeze the qualification to the exact 287 consecutive XNYS sessions from
   2025-06-23 through 2026-08-12, with an exact 21-session source window and
   stable identities for all four benchmark ETFs.
3. Reconcile every reconstructed session by stable `instrument_id`. Each
   declared member must have one complete adjusted close path or one explicit
   unavailable reason. The report binds the Membership logical fingerprint,
   manifest SHA-256, declared-ID-set fingerprint, and declared count for every
   session.
4. Bind the artifact to the exact EOD, Membership, split-action,
   split-adjustment, census, population, code, protocol, parameter, and session
   partition identities. A coordinated source or implementation change creates
   a new immutable report.
5. Require all six benchmark metrics on all 287 sessions. Require the four
   reconstructed metrics jointly on at least 250 sessions, including at least
   120 sessions in each chronological half. Each metric requires at least
   twenty distinct values overall and two in each half.
6. Report lag-one autocorrelation, median crossings, episodes, longest
   same-side runs, and all 45 pairwise correlations. Require at least four
   median crossings and no same-side run longer than 100 sessions. These are
   data-support gates, not claims of independent observations or Alpha.
7. Keep full-panel quantiles diagnostic-only. They cannot define a historical
   regime, threshold, interaction, or backfilled feature. Any later state axis
   and threshold must be frozen without outcomes and use an explicitly
   chronological rule.
8. Execute through a network-disabled reader on the workstation. It may write
   only one owner-only immutable report outside `/data`, then repeat the full
   calculation to a distinct report directory and require identical canonical
   bytes and logical identity.
9. Keep all forward outcomes, Development evaluation, Validation, Holdout,
   Campaign Three registration, model construction, Product activation,
   deployment, and trading authority closed.

## Consequences

The first multi-Agent pilot can challenge a real outcome-blind panel without
silently changing the trial count or contaminating later evidence. A rejected
qualification is a valid result and stops Campaign Three protocol design. A
passing qualification permits only a finite hypothesis and evaluation protocol
to be designed; it does not admit an Alpha factor or model.

The panel remains close-only price state. Reconstructed Membership is not
`as_operated`, historical classification is unavailable, and daily bars do not
observe intraday state. Those limitations are mandatory report content.

## Rejected alternatives

- lower the diversity gate for the discrete draft after seeing it fail;
- accept only a member count without exact stable-ID reconciliation;
- use full-period quantiles as if they were known at earlier dates;
- treat many persistent daily rows as independent market states;
- allow an Agent narrative or majority vote to override deterministic gates;
  or
- read Development outcomes before the real panel and independent replay pass.
