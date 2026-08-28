# ADR 0062: Add Descriptive Continuation Facts Before Rescoring

## Status

Accepted

## Date

2026-08-28

## Context

The first full-population strategy diagnostic found that trend continuation is
a broad superset of the implemented breakout and pullback channels. Changing
its weights or gates against the 2026-08-26 cross-section would optimize one
day's membership shape without evidence about later returns, stability, or
false positives.

Professional evidence supports studying trend persistence, the continuity of
the return path, volume as a conditioning variable, and market-state risk, but
the source studies generally use longer horizons than this product's intended
one-to-five-day holding style. In particular:

- [Time Series Momentum](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2089463_code753937.pdf?abstractid=2089463&mirid=1)
  documents persistence primarily over one-to-twelve-month horizons.
- [Frog in the Pan](https://academic.oup.com/rfs/article-abstract/27/7/2171/1578455?login=false)
  distinguishes gradual from discrete information paths.
- [Price Momentum and Trading Volume](https://www.lsvasset.com/pdf/research-papers/Price-Momentum-Trad-Vol-2000.pdf)
  shows that volume can condition momentum persistence and reversal; it does
  not make volume a fund-flow measure.
- [Momentum Crashes](https://kentdaniel.net/papers/published/jfe_16.pdf)
  supports evaluating momentum together with market panic, volatility, and
  rebound state rather than hiding market fit inside one stock score.
- [The 52-Week High and Momentum Investing](https://onlinelibrary.wiley.com/doi/pdf/10.1111/j.1540-6261.2004.00695.x)
  motivates studying high-position, but requires history the platform does not
  yet retain.
- [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)
  motivates preregistration and multiple-testing custody before comparing many
  plausible variants.

The retained Dell history contains only 29 completed sessions. It cannot
replicate the published studies, estimate outcome-fitted thresholds, or
support a 52-week-high implementation.

## Decision

Add a versioned, source-bound descriptive fact contract and pure Dell-local
calculator for future trend-continuation research. Version 1.0 publishes:

- ten-session net return, information discreteness, return-path efficiency,
  largest-day path share, and positive-session share;
- time above the contemporaneous ten-session average and its five-session
  ATR-normalized slope;
- recent-to-long ATR, distance from the twenty-session closing high, and
  recent-versus-prior five-session high/low structure; and
- recent-five versus prior-fifteen median volume.

The facts use only information available through their `as_of_session`, stable
instrument identity, the exact 26-session panel lineage, and the exact
Candidate and Entry Geometry source fingerprints. Missing or invalid history
fails closed for the complete fact row. Decimal scale and round-half-even
behavior are frozen by parameter fingerprint
`91859225d8a9d64fe56243a9e8f977b59e54aca8614ead27d0858d8694730231`.

The contract explicitly states that the facts are not a strategy score,
status, rank, signal, performance claim, fund-flow measurement, or option
return. An independent implementation recomputes every value from raw panel
bars and tests input-permutation invariance.

Keep Strategy Preview 1.0 unchanged. Do not publish these facts to Snapshot or
Dashboard and do not select thresholds from the current cross-section. A
future strategy version may consume only a preregistered subset after the
point-in-time research foundation and chronological evaluation are ready.

## Consequences

- Research can inspect distinct economic facts before combining them into a
  score, preserving the user's ability to see why a security is high or low.
- The ten-session measures are explicitly product-window adaptations, not
  claims to reproduce monthly academic factors.
- A real 2026-08-26 read-only review achieved complete coverage and zero
  independent-Oracle mismatch in both Universes. It also showed that several
  proposed path facts barely separate the existing continuation groups, so
  they must not be promoted merely because they sound professional.
- The existing qualifying group had somewhat higher recent volatility, not a
  universal contraction pattern. Contraction may later define a distinct
  consolidation setup, but it is not automatically a continuation bonus.
- Longer-horizon 52-week-high, fundamentals, events, options, and outcome
  features remain deferred until their governed source histories exist.

## Alternatives Considered

### Tune continuation weights to reduce current overlap

Rejected because one-session overlap is a diagnostic, not an outcome target.

### Copy published monthly factors directly into the short-horizon product

Rejected because the horizons, universe construction, and intended holding
period differ materially.

### Add one opaque continuation-quality score now

Rejected because it would hide the separate path, structure, volatility, and
participation facts before they have chronological evidence.
