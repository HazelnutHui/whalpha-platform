# ADR 0182: Falsify Split Coverage with Price Discontinuities

## Status

Accepted

## Date

2026-09-09

## Context

The canonical sparse split-adjustment publication covers only EOD paths that
cross known active, quarantined, or possible-unresolved split evidence. Its
omitted rows deliberately do not imply a neutral factor. Promoting those rows
requires evidence about missing corporate actions, not merely a larger factor
table.

The current Massive source is a bounded query snapshot with unavailable source
availability and incomplete independent coverage evidence. Price discontinuity
can reveal a likely missing action, but price alone cannot prove that a split
occurred or did not occur.

## Decision

Add a network-prohibited, read-only historical discontinuity diagnostic over
the exact canonical EOD family evidence and canonical split-action
publication.

For each stable `instrument_id`, compare the current session open with the
previous close only when both observations are on adjacent XNYS sessions.
Pre-register a severe raw discontinuity as a ratio less than or equal to 0.5
or greater than or equal to 2.0, matching the existing Dashboard guard.

For a current-session canonical active split group, compose the exact event
ratios and divide the observed open/previous-close ratio by the expected price
multiplier. Classify the event as bounded-consistent when that residual lies
strictly between 0.5 and 2.0; otherwise retain an extreme-residual review flag.
Canonical quarantine and unresolved possible-impact evidence always remain
quarantined and take precedence over numerical fit. Known event groups without
an adjacent two-sided EOD transition remain explicitly untested.

A severe discontinuity with no same-date active, quarantined, or possible-
impact split evidence becomes an `unexplained_price_discontinuity` review
candidate. It is not a split, a mapping, a correction, or positive evidence.
No ticker or name heuristic can attach an event to an instrument.

The diagnostic binds input paths, physical/logical fingerprints, explicit
source revision and calculation time, scanned session and adjacent-transition
counts, all classifications, and a deterministic report fingerprint. It emits
no new canonical or temporary dataset; the CLI prints a summary and bounded
flag identities for audit.

Absent-row neutrality, full corporate-action coverage, total return,
point-in-time signal eligibility, Historical Coverage, research performance,
analytics, publication, deployment, and scheduler authority all remain false.

## Consequences

- Negative-space split coverage becomes measurable instead of implicit.
- Unexplained severe gaps identify where a second source or manual evidence is
  most valuable.
- A clean diagnostic result would still not prove complete source coverage;
  it only fails to find a contradiction above the registered threshold.
- The scan is local and read-only, so it can proceed while the latest EOD and
  paid classification/lifecycle sources remain unavailable.

## Alternatives Considered

### Fill every omitted row with factor one

Rejected because it turns absence from one provider snapshot into unsupported
neutrality.

### Infer and publish split events from price ratios

Rejected because ordinary price gaps, distress, stale bars, and market events
can resemble split ratios. Price behavior is a review flag, not corporate-
action evidence.

### Add a dense adjustment ledger now

Rejected because it would duplicate millions of rows without resolving the
underlying evidence gap.

## Execution Evidence

The first clean-revision real scan and its non-authorizing interpretation are
recorded in the
[2026-09-09 canonical split coverage diagnostic audit](../audits/canonical-split-coverage-diagnostic-2026-09-09.md).
