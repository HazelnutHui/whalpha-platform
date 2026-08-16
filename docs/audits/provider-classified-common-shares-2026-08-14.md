# Provider-Classified Common Shares Shadow Audit — 2026-08-14

## Result

The read-only audit passed every defined hard gate. Candidate A contains 1,751 provider-`CS` instruments. Candidate B contains those 1,751 plus 113 provider-`ADRC` instruments, for 1,864 total. This numerical equality with the Legacy Liquid Screen is an observed result, not a target or proof of semantic equivalence.

Neither candidate is production-active. Provider classification does not establish issuer domicile or operating structure; SEC B2 remains paused.

## Validated Inputs

All formal readers reread manifests, Arrow schemas, row counts, content fingerprints, Parquet hashes, logical references, and completed status from `/data/trading-intelligence-platform` without writing it.

| Input | Date | Rows | Content fingerprint |
| --- | --- | ---: | --- |
| Massive type catalog | observed 2026-08-16 | 25 | `48c7106d3e53538159986b6d4a5a18822a4b3c47ae51bcfa0db8423abf19cc0d` |
| Provider observations | as of 2026-08-14 | 13,110 | `bf19d66846406a8d4b77581a2e4ab385b24bb3755fa07499a7b8b90c958119f4` |
| Canonical provider evidence | as of 2026-08-14 | 9,939 | `d8b7873eae825a2782e23d10b958111f04fb46ee5a77ce279a0404e7610c2568` |
| Provider evidence logical marker | as of 2026-08-14 | completed | `f4ad3b09c5ae605790232b824e1b69208ad3a10571b3b66ea265700114855a12` |
| Instrument Master | 2026-08-14 | 9,939 | `16a67c09f3a43a324bc4b88bd4433816e385868229fd9c5ba21f53115868da65` |
| Provider Identity | 2026-08-14 | 13,110 | `23b0a3460c8712b6e0d3d65c749c38ae5bdf6b1ad6bff6b8d880b1148a1fe24b` |
| Resolver | 2026-08-14 | 9,939 | `492b5e90105bfe2b3f64408bb0033e5df0edf000f7378d273652b3e3acd51668` |
| EOD previous | 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` |
| EOD current | 2026-08-14 | 9,912 | `f08033f26d920cc32ce4c12417521a57f45835c316994aae66c1a7da2a8501d2` |

Observations reconcile as 9,939 `canonical_mapped` plus 3,171 `expected_unjoined`; ambiguity, collision, malformed, canonical conflict, and orphan counts are zero.

## Type Distributions

Observation-level: CS 5,320; ADRC 376; ETF 5,374; ETN 51; ETS 111; ETV 90; FUND 332; PFD 429; RIGHT 122; SP 158; UNIT 306; WARRANT 441. Total: 13,110.

Canonical-instrument-level: CS 4,193; ADRC 372; ETF 5,374. Total: 9,939. No canonical unknown or quarantine record exists. The current-session old `common_stock` bucket crosses to 4,172 CS and 366 ADRC; the old ETF bucket crosses to 5,374 ETF. This demonstrates why the binary type is not sufficient evidence for Candidate A.

## Sequential Funnels

| Stage | Candidate A: CS | Candidate B: CS + ADRC |
| --- | ---: | ---: |
| Provider-type classified | 4,193 | 4,565 |
| Both sessions available | 4,164 | 4,529 |
| Supported exchange | 3,970 | 4,328 |
| Previous close ≥ USD 5 | 3,055 | 3,284 |
| Previous close × volume ≥ USD 20M | 1,751 | 1,864 |
| Final shadow candidate | 1,751 | 1,864 |

Mutually exclusive sequential removals are: A — missing session 29, unsupported exchange 194, price 915, one-session liquidity 1,304; B — missing session 36, unsupported exchange 201, price 1,044, one-session liquidity 1,420. The separate overlapping diagnostics are A — missing session 29, unsupported exchange 197, price 1,039, liquidity 2,368; B — missing session 36, unsupported exchange 204, price 1,173, liquidity 2,618.

## Legacy Comparison

Legacy has 1,864 members: 1,751 provider CS and 113 provider ADRC. Candidate A retains 1,751, removes the 113 ADRC, and adds 0. Candidate B retains all 1,864, removes 0, and adds 0. Candidate A fingerprint is `9df75919b217a0035b28222f355e58659be15f573e64df079616762db26d041f`; Candidate B fingerprint is `45a23396c3f3edbab7c05448b3d3a6fc382d72240e4abe1740c8c43d45535830`. The complete audit fingerprint is `9155595915d97e178bdc7a5e08ba92e4fadf3a7df1739450ed7dfa376c4b76eb`.

## Edge Records

- VCX: canonical Massive `CS`, stable-ID mapped, enters both final shadows. Its provider evidence retains `issuer_structure_unresolved` and the existing reviewed code registry identifies a closed-end-fund contradiction. Because no completed reviewed-override dataset exists, the contradiction is reported and not silently applied to membership.
- AKAN: canonical `CS`, stable-ID mapped, enters both final shadows. Provider evidence leaves domicile and issuer structure unresolved; the reviewed registry's foreign-issuer conclusion is reporting context only.
- BCPC: canonical `CS` maps to instrument `25d0d344-ac92-5510-bd2a-806d1c669572`; its same-ticker `SP` sibling is `expected_unjoined` and does not contaminate the resolved instrument. It lacks a current canonical bar and is not final.
- TPC: canonical `CS` maps to instrument `89f65cbb-a121-527d-bfad-beb195b55fff`; its same-ticker `PFD` sibling is `expected_unjoined` and does not contaminate the resolved instrument. It lacks a current canonical bar and is not final.
- VXT: no provider observation/evidence and no current canonical bar in the validated inputs; it is not included.
- AZ: canonical `CS`, stable-ID mapped, enters both final shadows.

## Hard Gates and Boundaries

Included non-CS in A, non-CS/ADRC in B, explicit ETF/ETN/FUND/PFD/WARRANT/UNIT/RIGHT/SP leakage, duplicate IDs, orphans, ambiguity, collision, malformed evidence, canonical conflicts, and unquarantined unknown codes are all zero. Included evidence coverage is 100%; permutation tests reproduce memberships and fingerprints; funnels and Legacy diffs reconcile.

The audit made zero SEC, Massive, or other network requests and did not access credentials. `/data` was read only. It created no production dataset, API/frontend change, snapshot, bundle, deployment, EOD/backfill/scheduler operation, or Core/Broad activation. Test products were limited to pytest temporary directories and the non-production audit result under `/tmp`.
