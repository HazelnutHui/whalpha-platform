# Five-Year FINRA/Massive Action Cross-Source Census — 2026-09-10

## Scope

Formally reread and compare, without network access, the sealed FINRA OTC Daily
List range and the complete Massive split/dividend source packages for
2021-08-11 through 2026-09-09. No stable-ID resolution, canonical write,
adjustment, analytics, publication, deployment, or scheduler change occurred.

## Source bindings

| Source | Rows | Manifest-chain fingerprint |
| --- | ---: | --- |
| FINRA OTC Daily List, 62 packages | 68,714 | `f40142ea94d4c5d43f594fc65e3a616831b0770c8237c09d455e3ba1b1589c0c` |
| Massive splits | 6,491 | `82d1ae4b5cba7e33bddc7e508cf3f9487b7f4cbaacbbf59c46ce80b40b8d4beb` |
| Massive dividends | 235,751 | `319dfa689a2f77478eb3584de613f8d4edce37fa3634608574109a4e6db17839` |

FINRA contained 2,583 split-field rows, 32,688 cash-field rows, 33,443 other
Daily List rows, and zero overlap between the two action-field populations.

## Results

| Measure | Split | Dividend |
| --- | ---: | ---: |
| FINRA action rows | 2,583 | 32,688 |
| Effective date inside action range | 2,522 | 28,571 |
| Candidate key absent / unique / ambiguous | 195 / 2,361 / 27 | 5,211 / 26,314 / 1,163 |
| Numeric match absent / unique / ambiguous | 263 / 2,298 / 22 | 24,475 / 8,205 / 8 |
| Unique key: numeric equal / disagree | 2,293 / 68 | 8,154 / 18,160 |
| Ambiguous key narrowed to one numeric candidate | 5 | 51 |
| Invalid FINRA numeric value | 0 | 0 |

The high split agreement is useful corroboration evidence. The much lower
cash-amount equality is expected to include ADR withholding, fees, currency,
gross/net basis, and revision semantics that this census cannot settle. It is
not treated as a provider-error count.

FINRA flag populations were: 10,375 security additions, 9,386 security
deletions, 4,749 symbol changes, 4,245 description changes, 9,564 security-
attribute changes, and 418 bankruptcy flags. These are source-field counts,
not canonical lifecycle facts.

## Sealed evidence and alignment decision

The owner-only output is 3,772 bytes, mode `0400`, with physical SHA-256
`562d8adf2a09ec1a217953de1215586bf20bf752551e523a0eb24f9335ae2ca1`
and logical fingerprint
`0559b1488ced840d786734b3dfa8b054d3c65dd18365d9d77c7a4616b9cd5317`.

The new fixture cases and the full API regression passed 2,423 tests with the
same two dependency deprecation warnings.

This stage is complete as a candidate agreement census and remains aligned
with ADR 0196 and the branch-local decisions later adopted by main ADR 0215.
It does not make the action or lifecycle family
research-ready. The next admissible transition is stable-ID resolution against
effective-dated Identity, with explicit event/revision semantics and all
unmatched, ambiguous, and contradictory rows preserved in quarantine.
