# Universe Pre-Activation Review Audit — 2026-08-19

## Outcome

The offline review completed and published a versioned shadow override/review boundary. Production Universe, Dashboard, API, frontend, snapshots, bundles, OCI, and deployment remain unchanged.

The only `--apply` invocation ran from 2026-08-20T07:11:12Z to 07:14:58Z. It atomically published all three targets, then exited 1 because the CLI's final formal-reader call lacked one repository import. No second apply occurred. The one-line import repair was tested; a separate read-only formal-reader invocation then validated every target and source reference. This is an operational postflight defect, not a partial publication.

## Formal inputs

- analysis session: 2026-08-19
- membership evidence: 2026-08-14
- trailing window: 2026-07-22 through 2026-08-18, exactly 20 sessions; analysis day excluded
- descriptor: `705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a`
- metric/decision/logical: `8abe29f4deb064acea974590fe965ecb166405381e7632762eb2ecba783ea7fc` / `9f27f7babaf347cab590386d9229d97f1f4348e32e483a35deffddc25d0a3254` / `89b58983f8c51680d77662dee7e2bfbf25406e160039d1a842d624396b08e65a`
- Candidate A/B source audits: `1b8b9757054130c04ac21266d3660107c0b38d37db0ba8e510a0dcb2ed9583fd` / `2404a29b818ac365db19dff9734eea10cbda7b88f16b93610ea49297bb03aa95`

## Stable-ID comparison

| Set | Members | Fingerprint |
| --- | ---: | --- |
| Legacy Liquid Screen | 1,864 | `0b5977991605bf8d3d930c7eb04b352f018260ba6dbe0515ced8e7dc86a2e067` |
| Candidate A passed | 1,641 | `aaa1f596c489ea2d73e21e01aa604fc9782f3ea20d17436ff8f52b8f0292b54f` |
| Candidate B passed | 1,747 | `7e4b9d587a7b2052d87cffa19a61ef2a5c926659d1c07654b5c83afab548ec88` |

Candidate B's requested 1,864 stable IDs exactly equal Legacy; equal count was not assumed. After trailing gates, A retains 1,641/removes 223/adds 0 and B retains 1,747/removes 117/adds 0. B minus A is 106 passed ADRCs; A minus B is zero.

A removals are 113 `adrc_not_in_common_share_universe`, 97 `below_trailing_liquidity`, 4 `below_previous_close`, 8 `insufficient_history`, and 1 `missing_previous_bar`. B removals are 103, 4, 9, and 1 for the latter four reasons. All sums reconcile.

## Reviewed overrides and final proposals

Two existing, explicitly reviewed authoritative records qualified:

- VCX instrument `4acc30c6-9461-588d-a0cc-a66d4d23d0d0`: exclude, closed-end fund, effective 2026-08-13.
- AKAN instrument `d8839d68-59a8-5525-a67d-676203ebea3a`: allow, operating ordinary share, effective 2026-08-12.

The effective date never precedes the source document date. Ticker is not stored as an override key. VCX was already `below_liquidity` and AKAN was already `below_price`, so neither row changes this analysis session; `allow` does not bypass upstream gates.

Primary remains 1,641 `CS`, fingerprint `aaa1f596c489ea2d73e21e01aa604fc9782f3ea20d17436ff8f52b8f0292b54f`. Secondary remains 1,747 (1,641 `CS`, 106 `ADRC`), fingerprint `7e4b9d587a7b2052d87cffa19a61ef2a5c926659d1c07654b5c83afab548ec88`.

Recommended policy: **Provider-Classified Common Shares (Provisional)** / **供应商分类普通股（暂定）** as primary; **Provider-Classified Common Shares + ADRs** / **供应商分类普通股及ADR** as optional secondary; Legacy only for compatibility, comparison, and rollback. This does not claim a verified U.S.-domestic operating-company Universe.

## Edge and gap evidence

- VCX: canonical provider `CS`, Legacy and both requested sets; authoritative reviewed exclusion exists; trailing status already removes it.
- AKAN: canonical provider `CS`, Legacy and both requested sets; reviewed foreign ordinary-share allow exists; below-price remains binding.
- BCPC/TPC: resolved canonical `CS` IDs remain isolated from `expected_unjoined` `SP`/`PFD` siblings and are not requested members.
- VXT: no canonical instrument/evidence; no override or inference.
- AZ: canonical `CS`, Legacy and both requested sets; below-liquidity; issuer structure remains unresolved and no override was created.

The ten unique gaps formally recompute as nine insufficient-history plus AVB missing-previous. Evidence categories are six `missing_canonical_bar`, three `identity_not_resolved_for_session`, and one `no_previous_session_bar`. Candidate A excludes ADRC YXT and therefore has eight insufficient-history records. No zero/forward fill or corporate-event inference was used.

## Publication

| Component | Rows | Bytes | Content fingerprint | Parquet SHA-256 |
| --- | ---: | ---: | --- | --- |
| Overrides | 2 | 6,029 | `970d502da6ddfc2889d801a018a19ee249ad979fff7ac95bf9f1f87a7693cc0b` | `f5ae117b8b977be0d5c15b1888b9544419c5a8556bfe53e6a6bc6fb862b8c07c` |
| Review decisions | 3,388 | 70,825 | `9b87e252417ea7a21ff5d2db4b563dd998d01b7a75b461c3dd5ed935443cbabe` | `27e48778cd8b274ce80d2a54c3c047b5e194a1ba2e30ba9446a6bf33dfd94e3e` |

Logical fingerprint: `3d895fd1217abddde132509f2ddf5c12f089152e987140d4927d3c58d5e33bad`. The formal reader validated schemas, counts, component hashes/fingerprints, the Trailing Liquidity source, and Legacy 08-13/14 EOD fingerprints.

The original 235-file/82,097,219-byte inventory remained byte- and metadata-identical, digest `23919cf17e991a4eebe426dc4e888732608605d69afed7390642c7c6ca918ecb`. Five new derived files yield 240 files/82,177,128 bytes, digest `5adbdadfb1f01c31a28ed51b5393cf93da41c8e504f8c2114da012a9b2871dce`. Staging, partial targets, raw payloads, and secret artifacts are zero.

No network request, credential access/stat, provider, SEC, OCI, ingestion, scheduler, Dashboard/API/frontend modification, snapshot/bundle, deployment, or production activation occurred.
