# U.S. Quant Research Factor-Space Diagnostic V1

## Purpose

`quant-research-factor-space-diagnostic/1.0` is the zero-outcome contract for
measuring redundancy and effective dimensionality before the next U.S. Factor
Discovery campaign. [ADR 0295](../decisions/0295-freeze-us-factor-space-diagnostic-before-successor-intake.md)
is authoritative for the decision.

## Frozen scope

| Panel | Rows | Inputs | Statistical unit |
| --- | --- | --- | --- |
| `security_cross_section` | stable instrument/session observations on the exact prior Development dates | 12 Catalog V1 plus 8 Catalog V2 factors | one point-in-time eligible instrument within one session |
| `market_state_time_series` | the same Development sessions with qualified state evidence | 10 Market-State V1.1 metrics | one market session |

The two panels have separate transforms, dependence matrices, clusters, PCA,
and effective-dimension summaries. They cannot be concatenated or weighted as
one matrix.

## Stock-panel transform

For factor `j` and session `t`, available raw observations receive deterministic
average ranks. With `n(t,j)` available values and midrank `r(i,t,j)`:

```text
u(i,t,j) = (r(i,t,j) - 0.5) / n(t,j)
c(i,t,j) = 2 * (u(i,t,j) - 0.5)
z(i,t,j) = (c(i,t,j) - mean_dev_j) / std_dev_j
```

Ties receive their average rank. `mean_dev_j` and sample `std_dev_j` are fitted
only from available Development rows after same-session ranking. A zero or
non-finite scale blocks that factor from multivariate admission.

## Market-state transform

Each metric is ordered by session. Development-only median and scaled median
absolute deviation are frozen:

```text
robust_z(t,j) = (x(t,j) - median_dev_j) / (1.4826 * MAD_dev_j)
```

If MAD is zero, a Development-only sample standard deviation may be reported
as a named fallback; zero fallback scale blocks the metric. The exact fallback
must be visible in the report.

## Missingness and support

- No missing value is silently filled.
- Pairwise statistics carry shared row/session counts.
- Missingness co-occurrence is reported separately from value dependence.
- PCA, VIF, and condition diagnostics use only rows complete for the exact
  reported input set.
- Complete-case counts and shares are mandatory; a reduced input set requires
  a new registered diagnostic version, not an implicit column drop.

## Dependence and clustering

For each panel report Pearson correlation on frozen standardized values and a
rank-dependence matrix on raw available values. Deterministic average-linkage
clustering uses:

```text
distance(j,k) = 1 - abs(correlation(j,k))
```

Every merge records members, distance, and deterministic lexical tie-break.
Economic families remain visible beside data-driven clusters; neither silently
overrides the other.

## Multicollinearity and PCA

On the complete-case standardized matrix:

- report numerical matrix rank and singular values;
- report the correlation-matrix condition number, or `singular`;
- report each VIF from the inverse correlation matrix, or an explicit
  non-identifiable disposition;
- compute PCA by deterministic SVD;
- fix each component sign so its largest-absolute loading is positive, using
  registered input order for ties;
- report every eigenvalue, explained-variance ratio, cumulative ratio, and
  factor loading; and
- report participation ratio, Kaiser count, and the minimum components needed
  for 80%, 90%, and 95% explained variance.

These diagnostics describe input geometry only. No component is Alpha, no
factor is admitted as a model input, and no future return is accepted by the
contract.

## Replay and authority

The report binds catalog, qualification, population, chronology, source,
implementation, and protocol identities. One independently created replay
must match canonical report bytes. A mismatch blocks use in successor intake.

The contract authorizes zero external requests, zero `/data` writes, zero
future-return reads, zero Validation/Holdout reads, and zero Product writes.
Private workstation custody is the only permitted result location until a
separate reviewed Product projection is created.

## Product projection

After exact replay, the trilingual Lab projection must place this diagnostic
inside the complete market-specific research lifecycle, not render PCA as an
isolated feature. The U.S. view identifies the preceding data and closed-trial
evidence, this diagnostic's role before successor intake, and every still-
locked downstream stage. The A-share view shows the same conceptual step as
`not started` until its independently admitted factor inputs exist. Internal
fingerprints, custody paths, host names, and raw identifiers remain private.
