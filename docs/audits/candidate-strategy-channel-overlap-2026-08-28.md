# Candidate Strategy Channel Overlap Review — 2026-08-28

## Scope

This offline, read-only review formally reread the completed 2026-08-26
strategy audit at `/tmp/whalpha-candidate-strategy-preview-20260826` and built
set diagnostics from the full Advance + Watch population. It made no external
request, Production write, score comparison, or outcome/performance claim.

## Results

| Universe | Breakout | Pullback | Continuation | All three | Union | Exclusive B / P / C | Multi-channel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary | 242 | 141 | 425 | 98 | 425 | 0 / 0 / 140 | 285 |
| Secondary | 261 | 155 | 451 | 108 | 451 | 0 / 0 / 143 | 308 |

| Universe | Pair | Intersection | Jaccard | Subset result |
| --- | --- | ---: | ---: | --- |
| Primary | Breakout / Pullback | 98 | 0.3439 | neither |
| Primary | Breakout / Continuation | 242 | 0.5694 | Breakout is a subset of Continuation |
| Primary | Pullback / Continuation | 141 | 0.3318 | Pullback is a subset of Continuation |
| Secondary | Breakout / Pullback | 108 | 0.3506 | neither |
| Secondary | Breakout / Continuation | 261 | 0.5787 | Breakout is a subset of Continuation |
| Secondary | Pullback / Continuation | 155 | 0.3437 | Pullback is a subset of Continuation |

Diagnostic logical fingerprints are
`bdaada830c713cad59f1f84517caed17d5cdaac8b251df1dcc3487b0093b14d2`
for Primary and
`9c59c8c3934c66f17ddb1f50381069e49d20c0dc63dba20b0874d41b72a7e4ea`
for Secondary.

## Conclusion

Momentum breakout and strong-stock pullback remain meaningfully different from
each other, but the current trend-continuation baseline is a broad superset of
both qualifying populations. It is not yet independent enough to present as a
fully mature continuation setup detector.

The current 20-session Entry Geometry facts can describe trend strength,
bounded breakout, orderly pullback, and extension. They do not yet establish
the continuation-specific sequence of trend efficiency, consolidation or
volatility contraction, shallow retracement, and recovery quality. Adding
those governed facts is preferable to tuning existing weights on this single
cross-section. Any revised formula or gate requires a new frozen parameter
version and chronological evaluation.
