# ADR 0275: Freeze the Outcome-Blind Factor Qualification Protocol

## Status

Accepted

## Date

2026-09-15

## Context

ADR 0273 registers the first 12 price/volume factors and ADR 0274 separates
Factor Discovery, Model Construction, and Strategy Expression. The formulas
must now be exercised on governed Dell data before any new forward return is
read. Choosing a cohort, outlier rule, correlation minimum, or duplicate
threshold after seeing the values would make the report difficult to reproduce
and could steer later screening opportunistically.

## Decision

Freeze one descriptive, zero-outcome qualification run for Quant Research
Factor Catalog V1.

### Population and source boundary

- Reuse the exact 287-session chronological plan and reconstructed Primary
  Membership census already bound by the retained Pullback method-engineering
  launch evidence: 2025-06-23 through 2026-08-12.
- The first 20 sessions remain feature-window warm-up with no member paths.
  The remaining same-session Membership records determine expected paths; no
  current Universe or ticker list may be projected backward.
- Read canonical EOD and the bound split-action and split-adjustment
  publications locally on Dell with network disabled. Raw facts are never
  overwritten.
- Each calculation uses exactly 21 aligned sessions and split-reconciles price
  and volume to the signal-session basis. A missing or invalid required member,
  missing SPY, unresolved split impact, or quarantined split evidence rejects
  the complete session cross-section. Factor-specific zero denominators remain
  explicit unavailable cells and do not invalidate unrelated factors.
- The evidence tier remains reconstructed latest-vintage research only. It is
  not as-operated Membership, does not prove neutral absent split rows, and is
  not Product or performance evidence.

### Frozen descriptive statistics

For every factor, retain exact expected, available, and unavailable counts,
sorted reason codes, per-session availability, and session/instrument
concentration. Render calculated values to ten decimal places before
diagnostics.

For each finite distribution:

- report minimum, 1st, 5th, 25th, 50th, 75th, 95th, 99th percentiles, and
  maximum using linear interpolation at `(n - 1) * p`;
- define same-session tie excess as `available count - distinct canonical
  values`, aggregated across sessions; and
- define descriptive outliers using the outer Tukey fences
  `Q1 - 3*IQR` and `Q3 + 3*IQR`.

Concentration reports maximum group share, top-ten group share, and HHI over
available cells for both session and stable `instrument_id` axes.

For every one of the 66 factor pairs, calculate average-rank Spearman
correlation separately inside each session. A session is eligible only with at
least 30 shared observations and at least two distinct values for each factor.
The report retains eligible-session count, shared-observation count,
observation-weighted mean correlation, session median/5th/95th percentiles,
high-absolute-correlation count, and dominant-sign share.

A pair receives a descriptive `near_duplicate` flag only when all of these
predeclared conditions hold:

1. at least 60 eligible sessions;
2. absolute observation-weighted mean Spearman correlation is at least 0.90;
3. at least 80% of eligible sessions have absolute Spearman correlation at
   least 0.90; and
4. at least 90% of non-zero eligible sessions share the dominant sign.

Connected components of flagged pairs form the reported near-duplicate
groups. These thresholds manage later trial accounting; they are not Alpha
admission or rejection gates.

### Reproducibility and authority

The report binds the catalog fingerprint, calculation and diagnostic code
SHA-256, chronological plan, EOD, Membership, action, and adjustment source
identities. It is written once to owner-only private evidence custody outside
canonical `/data`; an exact replay must produce identical logical and physical
fingerprints.

The run contains no forward outcome, return, IC, bucket performance, selected
threshold, factor pass/fail decision, model weight, model construction,
strategy expression, Candidate rank, or Product authority. After the report
is retained, a separate ADR must freeze the finite outcome-reading screening
protocol before any factor outcome is read.

## Consequences

- Formula and data defects can be separated from apparent predictive value.
- Redundant formulas can be counted as related hypotheses before formal
  multiplicity control is chosen.
- The report can legitimately end with every factor still unqualified for
  model use.
- Reusing the governed 287-session cohort avoids inventing a new Membership
  history, but limits temporal and Regime coverage; later batches require new
  versions and evidence.

## Alternatives considered

### Inspect plots manually and choose useful diagnostics afterward

Rejected because post-hoc descriptive choices can silently influence the
subsequent outcome-reading protocol.

### Run the first catalog across all five years immediately

Rejected because complete split-neutrality and as-operated Membership are not
available across that interval. The narrower admitted reconstructed cohort is
truthful and sufficient for formula and redundancy qualification.

### Reuse global pooled correlation

Rejected because pooling instruments across time mixes cross-sectional and
time-series structure. Same-session rank correlation matches the intended
equity-selection use.
