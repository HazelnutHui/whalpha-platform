# Quant Research Market-State Qualification V1

## Purpose

`quant-research-market-state-qualification/1.0` determines whether the
outcome-blind Market-State Vector 1.1 is sufficiently complete, variable,
temporally supported, and reproducible to support the design of a finite third
Factor Discovery campaign. It does not test returns or select a market regime.

## Frozen partition and inputs

- 287 consecutive XNYS sessions: 2025-06-23 through 2026-08-12;
- 21 aligned close sessions for every metric value;
- stable identities for SPY, QQQ, IWM, and DIA throughout the source range;
- effective-dated reconstructed Primary Membership by stable `instrument_id`;
- split-adjusted price paths with unresolved action evidence quarantined; and
- exact EOD, Membership, action, adjustment, census, code, protocol, vector,
  population, and session-partition identities.

Every reconstructed member is either complete or explicitly unavailable. A
declared member may not disappear silently. Each session retains the exact
Membership logical fingerprint, manifest hash, declared-ID-set fingerprint,
declared count, complete count, and all ten metric values or reasons.

## Frozen data-support gates

| Evidence | Gate |
| --- | --- |
| Six benchmark metrics | available on all 287 sessions |
| Four reconstructed metrics | jointly available on at least 250 sessions |
| Chronological support | at least 120 joint sessions in each half |
| Variation | at least 20 distinct values overall and 2 in each half |
| Temporal support | at least 4 full-panel-median crossings |
| Persistence warning gate | no same-side run longer than 100 sessions |

The report also retains lag-one autocorrelation, episode counts, longest runs,
distribution summaries, unavailable reasons, joint coverage, and all 45
pairwise Pearson correlations. Correlation and quantile outputs are diagnostics
only. They cannot choose Campaign Three axes, thresholds, or interactions.

## Status semantics

- `ready_for_campaign_protocol_design`: all frozen data and implementation
  gates pass. Only outcome-blind hypothesis selection and finite protocol
  design may follow.
- `rejected_data_or_implementation`: one or more gates fail. Campaign Three
  remains unregistered and outcomes remain closed.

Neither status is an Alpha conclusion. The report contains no forward returns,
performance metrics, selected states, interactions, model weights, Candidate
authority, or option-return evidence.

## Custody and replay

The formal runner disables network access, reads `/data` without writing it,
and writes one owner-only immutable report under a direct `report=<id>` child
of a `0700` custody directory. The report file is canonical JSON with mode
`0400`. A second full run must use a distinct report directory and match the
first report's canonical bytes and logical identity.

Mandatory limitations are:

- close-only price state is not total return;
- daily bars do not observe intraday state;
- historical classification is unavailable; and
- reconstructed Membership is not `as_operated`.
