# Strong-Leader Pullback Reconstructed Replacement Selection Review — 2026-09-15

## Decision

`REJECTED_ENDPOINT_INSTABILITY`

The single replacement attempt registered by ADR 0272 completed exactly once
and did not lock a parameter. Strong-Leader Pullback therefore remains a
development-stage rejected/inconclusive family and cannot enter Validation.
No further selection-protocol variation over this development result is
permitted.

## Fixed bindings

- implementation revision:
  `1492c75297486521f44ec760b712235206909d1e`
- source report SHA-256:
  `c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852`
- source logical fingerprint:
  `f0006fa38a7a729dca5b2cd34369e7c3bd2110aa17096bcd091d72875ce71f7f`
- replacement policy fingerprint:
  `9fa09e0b627aed2c1bb1f108eec2d73bfeb3a5407b3c0850b3605b23ef0991f9`
- protocol logical fingerprint:
  `65e2258153e6f5462a440662826a2a20594d9a889aaaa0761b71531251e07a0d`
- result SHA-256:
  `070f7d8c6e29ad1e5e4c04d02ec3b19c1d0e7720c369d5ffdd991195186184b2`
- result logical fingerprint:
  `086675c82efb4453f9bc71e88ad65fc0f64c411569313cd6ac3795ee0a6baaec`
- fixed creation time: `2026-09-15T07:44:00Z`

The implementation passed the complete 2,904-test backend suite before the
real report was read. The retained result is canonical JSON in owner-only
`0700/0400` private Dell custody. The custody root contains only the fixed
`report=20260915-v1` result and no staging residue.

## Result

All 24 registered parameter combinations remained in the ledger. Twenty-three
were eligible in all three endpoint scenarios. The remaining combination,
`ae3c168078096fa3be9a1c1afc1e0029aebda80c1c15f69f82f810a9df7ac6cd`,
failed the 60-signal and inference floors in every endpoint scenario.

The independently ranked endpoint winners were:

- `all_lower`:
  `d12b26e778426750027adb3d7bd6b918cc224e2575da016286ae0fd8f02543e9`
- `all_upper`:
  `faef177de6f17d24430f593740c3df3f4f228140cdf55e0ada9f8aa495ee0559`
- `contrast_adverse`:
  `d12b26e778426750027adb3d7bd6b918cc224e2575da016286ae0fd8f02543e9`

Because the Upper world selected a different combination, no stable
provisional winner existed. The six winner-specific robustness gates were
therefore correctly not evaluated: applying them to one endpoint-dependent
choice would manufacture a lock after the endpoint-stability gate had already
failed.

The terminal result is `rejected_endpoint_instability`, with no selected
parameter and no parameter lock. An exact rerun returned `already_present`
with the same report SHA-256 and logical fingerprint.

## Boundary review

The result records zero network requests, zero canonical-data writes, and zero
Production writes. Validation and Holdout were not accessed. Validation
transition, performance claims, Candidate activation, Lab publication, and
deployment remain unauthorized. The evidence is reconstructed latest-vintage
development evidence, not as-operated evidence and not an option-return claim.

## Required next action

Retain this failure as research evidence and register a genuinely independent
hypothesis, starting with Momentum Breakout unless a prior review identifies a
better independent family. Reusing the same development outcome to change the
Strong-Leader Pullback selection rules again is prohibited.
