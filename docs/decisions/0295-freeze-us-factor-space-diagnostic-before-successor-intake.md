# ADR 0295: Freeze the U.S. Factor-Space Diagnostic Before Successor Intake

## Status

Accepted

## Date

2026-09-17

## Context

The first three U.S. Factor Discovery campaigns are closed with 17 counted
formal trials, zero admitted Alpha, and zero model inputs. Their outcome-blind
qualification reports checked coverage, distributions, concentration, and
pairwise same-session correlation, but they did not answer the multivariate
question: how many independent information directions exist across the
registered factor library?

Low pairwise correlation is not enough. Several momentum, trend, volatility,
or liquidity variants can occupy one latent direction even when no pair meets
a near-duplicate threshold. Starting another campaign without measuring that
structure would encourage repeated variants and waste the finite outcome
budget.

The registered stock-level factors and the Market-State vector also live on
different statistical axes. Stock factors vary across instruments within a
session; Market-State metrics vary across sessions. Repeating one session-level
state value across every stock and placing it in the same PCA would inflate its
apparent sample size and create a false factor geometry.

## Decision

1. Before a successor U.S. campaign freezes hypotheses, run one outcome-blind
   factor-space diagnostic over previously registered inputs. It may influence
   deduplication and input design, but it is not an Alpha trial.
2. Keep two independent panels:
   - `security_cross_section`: the 12 V1 and 8 V2 stock-level factors on the
     exact previously governed Development session boundary; and
   - `market_state_time_series`: the 10 qualified Market-State metrics on the
     same Development dates when available.
   The panels must never be row-expanded and combined into one PCA.
3. The stock panel uses same-session midranks computed only from that session's
   available point-in-time population. Midranks map to centered percentile
   scores, followed by column scaling fitted only on the Development panel.
   The market-state panel uses Development-only robust location/scale. No
   Validation or Holdout observation may fit either transform.
4. Missing values remain missing. Pairwise diagnostics disclose their exact
   shared support. PCA, VIF, and condition diagnostics use an explicitly
   counted complete-case matrix; no mean, zero, forward, backward, or model-
   based imputation is permitted in version 1.
5. Report Pearson and rank dependence, missingness co-occurrence, the existing
   economic family, deterministic average-linkage clustering on
   `1 - abs(correlation)`, VIF or an explicit singular disposition, condition
   number, eigenvalues, explained variance, loadings, and effective-dimension
   summaries.
6. Effective dimension is not one cherry-picked number. Report at least:
   positive numerical rank, participation ratio, Kaiser count, and component
   counts reaching 80%, 90%, and 95% explained variance.
7. PCA is fitted by deterministic SVD. Component signs are fixed by making the
   largest-absolute loading positive, with factor order breaking ties. Exact
   replay must reproduce canonical report bytes.
8. The diagnostic cannot read forward returns, Development labels, screening
   decisions, Validation, or Holdout; grant model input, strategy, Candidate,
   publication, broker, or trading authority; or erase the 17 consumed trials.
9. The website continues to show `not computed` until the real report and an
   independent exact replay complete. After completion it may show compact
   human-readable factor families, clusters, heatmaps, PCA loadings, explained
   variance, effective dimension, and retained/rejected input reasons without
   exposing private custody identifiers.
10. The workstation may use bounded multi-core numerical computation. The
    concurrently running A-share source acquisition is I/O/provider-limited
    and does not by itself require throttling U.S. numerical work. Concurrency
    is reduced only after observed memory pressure, I/O wait, swap growth, or
    reproducibility failure.

## Consequences

The next U.S. hypothesis intake begins from measured information geometry
rather than factor-name counts. Economically distinct ideas remain welcome,
but superficial window or formula variants can be rejected before consuming
outcomes. Market-State structure remains interpretable without pretending that
repeated stock rows create independent macro observations.

The diagnostic may conclude that the existing library has few effective
dimensions or unstable clusters. That is useful evidence, not a failed Alpha
test. It does not reopen or reinterpret any closed campaign.

## Rejected alternatives

- treat pairwise correlation alone as proof of independence;
- place stock-level and session-level inputs in one row-expanded PCA;
- fit standardization or PCA on all historical, Validation, or Holdout data;
- impute structural missingness to maximize the displayed sample;
- use PCA components directly as Alpha without a separately registered test;
- rerun closed factors against outcomes after observing the geometry; or
- reserve workstation CPU merely because a provider-limited download is active.
