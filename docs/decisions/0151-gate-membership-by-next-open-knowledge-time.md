# ADR 0151: Gate Membership by Next-Open Knowledge Time

## Status

Accepted

## Date

2026-09-06

## Context

Disconnected V3 Universe Membership mechanics cover every one of the 302
Identity-source-available sessions. That physical result is not itself a
point-in-time research population. The 301 historical Identity source
partitions explicitly retain `outcome_reconciliation_only` status, while the
2026-09-04 direct daily partition is eligible only from its actual observation
time. The Membership manifest records `source_data_cutoff` and `evaluated_at`,
but the current Historical Coverage evidence contract does not yet prove that
either occurred before a strategy could act.

The first preregistered strategy observes information through one session's
close and enters at the next session's open. “Information through close” is
not the same timestamp as “signal calculation completed.” EOD data normally
arrives after the close, and the calculation may run later. Treating the close
as both boundaries would either create impossible timing or hide look-ahead.

## Decision

Add an offline, immutable Membership knowledge-time assessment with the
following exact policy:

- market information is bounded through the represented XNYS session close;
- the intended execution boundary is the immediate next XNYS session open;
- the full Membership `source_data_cutoff` and `evaluated_at` must both be
  strictly earlier than that open;
- the bound Identity source must itself be classified
  `eligible_at_source_observed_at`;
- a source classified `outcome_reconciliation_only`, or a Membership
  evaluation completed at or after the next open, remains outcome-only;
- the assessment binds the Membership logical fingerprint, manifest SHA-256,
  Parquet SHA-256, Identity source custody fingerprint, exact timestamps, and
  offline exchange-calendar version.

The formal reader must reread both the Membership partition and canonical
Identity source partition and prove that the Membership source-fingerprint set
contains that exact custody fingerprint. An assessment performs no network
request and no canonical write.

`signal_cutoff=session_close` in the existing preregistration is interpreted
as the market-information boundary, not a claim that calculation or execution
occurs at the closing instant. Any sealed signal must additionally prove its
actual calculation time precedes the declared next-open entry boundary. A
future preregistration revision should name these two clocks separately before
the first performance evaluation.

Historical Coverage must not become `research_ready` merely because
Membership Parquet exists. A later Coverage revision must transitively bind a
signal-eligible timing assessment for every session admitted to a strategy
population. Outcome-only partitions may remain retained evidence but cannot
silently increase eligible signal-session counts.

## Consequences

- The exact 2026-09-04 V3 partition passes the new gate: information cutoff
  `2026-09-04T20:00:00Z`, source cutoff
  `2026-09-06T11:14:35.992620Z`, evaluation
  `2026-09-06T13:15:00Z`, and next XNYS open
  `2026-09-08T13:30:00Z`. Its assessment fingerprint is
  `586cde811b9c26496584f56a89f489d6314dbc00e9ed7c112829238dfebdfedf`.
- The corrected 2026-09-03 V3 partition remains outcome-only because its
  source contract is historical and its evaluation occurred after the 9/4
  open. Its assessment fingerprint is
  `be8b100a0bf595d31032220d62325a909fe9488ef060b313a83d8813279463ce`.
- One passing temporary assessment does not authorize `/data` Apply,
  Historical Coverage publication, a backtest, a performance claim, or a
  Production deployment.
- The two missing Identity sources on 2026-08-13 and 2026-08-19 remain absent;
  no timing policy may fill them by approximation.
- Going forward, the daily chain can create genuinely point-in-time Membership
  only when the same source, evaluation, next-open, custody, and formal-reread
  gates pass before immutable publication.

## Alternatives Considered

### Treat every reconstructed historical partition as point-in-time

Rejected because later source observation and later evaluation would be
mistaken for contemporaneous knowledge.

### Reject every source obtained after the represented calendar date

Rejected because a Friday EOD dataset obtained and evaluated over the weekend
can still be known before the next tradable session on Tuesday. The actionable
boundary is the intended execution time, not midnight.

### Use the next calendar day instead of the exchange calendar

Rejected because weekends, holidays, early closes, and daylight-saving time
must be handled by the same offline XNYS schedule used elsewhere in the
project.
