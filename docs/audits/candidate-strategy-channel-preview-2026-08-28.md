# Candidate Strategy Channel Preview Review — 2026-08-28

## Result

`MECHANICS_IMPLEMENTED_NOT_VALIDATED`

This was an offline Dell calculation over the existing formal 2026-08-26
Candidate and Entry Geometry audits. It wrote one immutable shadow audit under
`/tmp/whalpha-candidate-strategy-preview-20260826`; it wrote no `/data`,
publication, Snapshot, bundle, deployment, or Production state.

## Bound source evidence

- Candidate audit fingerprint:
  `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
- Entry Geometry audit fingerprint:
  `b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`
- Strategy parameter fingerprint:
  `13312df3e5b132223878582b8cd3af533a880e9f2f0d520f8520b46b97138ac9`

Both existing audit readers completed before calculation. The preview then
passed typed full-population reconciliation and the bounded consumer retained
at most eight records per channel.

The independent Oracle does not import the Production strategy calculator. It
recomputed every technical-channel score, status, and within-channel rank from
the typed Candidate and Entry Geometry inputs. Both Universes returned zero
mismatches and input-permutation equivalence.

- Strategy audit fingerprint:
  `1c2036a6266647482de12d1ed7a1f9adf0f41311bc886979324ba3a0859c2877`
- Primary Oracle fingerprint:
  `ec27bbdb21c124b37bf02d4432518f5ec459f1a206df059e943a965ac6cf1464`
- Secondary Oracle fingerprint:
  `36bf1370d8f07150c26021c7b05e4c2666c0d0d2bef2cf084e8e699fc5a81c1f`
- Audit custody: directory mode `0700`; five canonical artifacts mode `0400`;
  atomic directory rename; formal reread passed
- External requests: `0`; Production writes: `0`

## Primary Universe

Batch fingerprint:
`da1562a01c0fef2eff14d092616c2a61b6939dfb845fde0a156759bd5c8227f1`

Consumer fingerprint:
`6bcf90d634d9c62eaff7292372affeccfe3654b478bd1741c5278909325fbdd0`

| Channel | Advance | Watch | Deprioritized | Unavailable | Displayed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Momentum breakout | 10 | 232 | 1,454 | 19 | 8 |
| Strong-stock pullback | 43 | 98 | 1,555 | 19 | 8 |
| Trend continuation | 130 | 295 | 1,271 | 19 | 8 |
| Technical reversal | 0 | 0 | 0 | 1,715 | 0 |
| Fundamental value reversal | 0 | 0 | 0 | 1,715 | 0 |
| Defensive rotation | 0 | 0 | 0 | 1,715 | 0 |

## Secondary Universe

Batch fingerprint:
`1ecd747e3436bcf8ad0f215e697cd0f78b41289bdc15664dac88e4766fa8f83e`

Consumer fingerprint:
`76f3ed783de3c179d933991f02d83cbb4cc495d729e7d0b265320212a85a5ea1`

| Channel | Advance | Watch | Deprioritized | Unavailable | Displayed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Momentum breakout | 11 | 250 | 1,548 | 19 | 8 |
| Strong-stock pullback | 47 | 108 | 1,654 | 19 | 8 |
| Trend continuation | 138 | 313 | 1,358 | 19 | 8 |
| Technical reversal | 0 | 0 | 0 | 1,828 | 0 |
| Fundamental value reversal | 0 | 0 | 0 | 1,828 | 0 |
| Defensive rotation | 0 | 0 | 0 | 1,828 | 0 |

## Review findings

- The first prototype incorrectly made ETF/sector-driver alignment a required
  score input. The real cross-section made 560 Primary and 618 Secondary
  technical rows unavailable. The accepted baseline removed that hidden
  environment dependency and keeps market/sector fit separate.
- The first pullback prototype reused general volume participation, which can
  penalize an orderly quiet pullback. The accepted formula relies on Entry
  Geometry's explicit pullback volume rule instead.
- Full Watch populations remain large, confirming that raw results must not all
  reach the first screen. The bounded consumer cap of eight is therefore a
  product requirement, not a claim that only eight setups exist.
- Nineteen rows in each Universe still lack complete governed technical inputs
  and correctly remain unavailable.
- The cross-section is implementation evidence only. No forward labels,
  success rates, option returns, weight fitting, or threshold tuning occurred.

## Remaining limitations

The current 29-session/current-constituent history is not performance eligible.
The Oracle proves implementation agreement and deterministic ordering, not
economic validity. Nothing in this review authorizes publication, frontend
integration, deployment, threshold tuning, performance claims, or trade action.
