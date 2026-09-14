# Strong-Leader Pullback Terminal Gap Census Audit — 2026-09-14

## Scope and authority

ADR 0252 required an outcome-blind census before changing the first strategy's
coverage or admission contract. The network-disabled run formally reread the
original lifecycle exposure population, complete source sample, terminal-
payoff terms, fixed-cash references, and both listed-consideration reference
reports. It retained all 64 stable IDs whose five-session label windows cross
their last canonical observation.

This report measures reference-value evidence and remaining terminal gaps. A
reference value is not a canonical terminal outcome, strategy label, return,
or admission. No `/data`, Historical Coverage, Candidate, publication,
deployment, or scheduler state changed.

## Exact bindings

- Implementation revision:
  `1b240c466547a113c8fde0c555e1104511c3c459`
- Evaluation time: `2026-09-14T05:03:00Z`
- Report SHA-256:
  `004598ae1d3ee5f93500e2372770ffb82c0c7138230642e37306552e776ad06f`
- Logical fingerprint:
  `148d8822d5b304b2aab9a481642a70fd905bcb16af17f67ec051a3d447d65ace`
- Blocker census manifest SHA-256:
  `63fb6694ef0e6284bea3dc9cd5aafe431353e443a4239eff8f598f1d6baecb15`
- Source sample report SHA-256:
  `17a1c177be65693786a410c1c2107c499e34a88960541a24339644e12ba01416`
- Payoff-terms report SHA-256:
  `f0b2e805a46e9f2b3e88432d1c5aa6a8782d095ffdda5790cb8894639d2be1a9`
- Fixed-cash report SHA-256:
  `e500a6419efee4bb150d5b0cdec85819c9c9aa8749860c4cf0d3b95ce922d429`
- Original and residual listed-reference report SHA-256 values:
  `18e47df490acca529aa3eaebdfaba70c989669ecb83e52a377d6885200913f2c`
  and
  `7ee02be39f2ad89a8a9e84edf030bc69b04101c6676f09d8b6ca46b174ae6e21`.

## Complete result

| Evidence state | Securities | 1-session paths | 3-session paths | 5-session paths |
| --- | ---: | ---: | ---: | ---: |
| Nominal fixed-cash reference documented | 30 | 2 | 62 | 118 |
| Gross listed-consideration reference documented | 12 | 2 | 24 | 44 |
| Cessation timing not matched | 9 | 3 | 20 | 36 |
| CVR realization unresolved | 6 | 1 | 13 | 24 |
| Exceptional primary-source case unadjudicated | 3 | 1 | 7 | 13 |
| Holder election or proration unresolved | 3 | 1 | 7 | 13 |
| Unlisted unit and election value unresolved | 1 | 0 | 2 | 4 |
| **Total** | **64** | **10** | **135** | **252** |

Reference values are documented for 42 securities, covering 4 / 86 / 162
crossing paths at the 1 / 3 / 5-session horizons. Twenty-two securities remain
without reference evidence, affecting 6 / 49 / 90 paths respectively.

The evidence-work order is now fixed as:

1. nine unmatched cessation-timing cases;
2. three exceptional primary-source cases (`LNW`, `REVG`, and `SAND` remain
   locators only);
3. six CVR realization cases;
4. three holder-election or proration cases; and
5. one unlisted-unit and election case.

Resolving the first two groups does not automatically value complex payoff
components. It establishes event identity and timing before valuation.

## Reproducibility

The canonical JSON is 45,386 bytes in one `0700` directory with file mode
`0400`. Exact replay returned `already_present` with identical hashes, zero
network requests, and no symlink, partial, or staging residue.

Six focused tests passed, the combined linked suite passed 29 tests, and the
complete API suite passed 2,740 tests. The two warnings are unchanged
dependency deprecations in the authentication and TestClient paths.

## Decision

Do not rerun the unchanged 2026-09-10 admission decision: it cannot consume
this typed evidence and would only repeat the old rejection. Resolve the nine
timing cases and three exceptional cases next, then reassess the terminal gap.
No real outcome or backtest may open before a later versioned coverage census
and admission decision satisfy every mandatory family.
