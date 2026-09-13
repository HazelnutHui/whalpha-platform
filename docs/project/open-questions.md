# Open Questions

Only unresolved decisions that can change implementation belong here. Resolved
history stays in ADRs, the changelog, and audits.

## First research program

- What exact evidence and threshold make current-market applicability
  supportive, neutral, adverse, or unavailable without selecting the recent
  winner?
- Which prospective-shadow duration and decay thresholds are required before
  an otherwise validated model may become active?
- What portfolio-construction rule, if any, should follow the event study so
  AR, Sharpe, MDD, turnover, and capacity become meaningful rather than
  decorative?

## Missing point-in-time evidence

- After the ADR 0196 Massive/official-free composition is measured across the
  five-year target, which exact lifecycle or terminal facts remain materially
  unresolved, and do they justify a paid cross-venue source?
- Which independent source resolves corporate-action date semantics, dividend
  currency/order handling, unexplained discontinuities, and total-return
  adjustments?
- Can reconstructed Membership ever obtain defensible historical availability,
  or must formal validation begin only with prospective canonical Membership?
- Will a GICS History sample pass the existing identity, knowledge-time,
  inactive coverage, revision, retention, and equal-session-display gates?
  If not, can TRBC close the exact gaps?
- Which point-in-time quote source and calibration method can support realistic
  spread, impact, and capacity evidence?

## Product and model governance

- What quantitative activation scorecard is required in addition to the
  registered research gates?
- How many active models may appear simultaneously before Candidate usefulness
  is reduced by signal overload? The current design ceiling is three.
- When is a model retired versus temporarily marked adverse for the current
  market?
- What evidence is required before a separately validated ensemble may combine
  model ranks?
- What coverage threshold permits formal sector/industry concentration while
  preserving an explicit unknown bucket?
- What measured improvement in unique hypotheses, reproducibility, rejection
  quality, or research time justifies expanding the first small multi-agent
  pilot?
- Which agent roles require technical isolation versus an independent
  deterministic replay, and what minimum evidence shows that apparently
  different agents are not merely repeating the same hypothesis?

## Data and operations

- What is the guaranteed or empirically stable same-evening Grouped Daily
  finality window under Stocks Starter?
- What backup/recovery and source-termination policy governs no-expiry
  canonical history and sealed research evidence?
- When do real query/concurrency needs justify a database rather than current
  Parquet/manifests?
- Which options-chain source is suitable when the options-expression layer
  receives an approved data requirement?

## Later product decisions

- Which point-in-time fundamentals, estimates, guidance, and event sources are
  required for Fundamental Value Reversal?
- Which broker capabilities beyond IBKR are worth supporting?
- What explicit product need would justify guest/credential role differences?
- What strategy and latency requirement would justify intraday data and
  infrastructure?
