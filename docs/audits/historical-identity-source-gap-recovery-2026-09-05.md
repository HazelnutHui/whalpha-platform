# Historical Identity Source Gap Recovery Audit — 2026-09-05

## Scope

Recover the 24 historical Identity source dates previously absent from
canonical normalized custody. Acquisition, equivalence, profile routing,
normalization, planning, Apply, and recovery verification remained separate
boundaries. No ticker, response body, URL, request identifier, credential, or
Authorization value was emitted into audit evidence.

## Acquisition and custody

The bounded Dell fetch started under clean `main` commit
`e9ce39b61677f737d0645c04e47481a63da268cf`. A local network outage stopped
the first invocation after 15 completed packages. The same owner-only root was
resumed: all 15 packages were formally reread with zero requests and the
remaining nine were fetched successfully.

The completed temporary custody contains 24 package manifests, 336 response
artifacts, 360 files, and 92,811,718 bytes. Directories are `0700`, files are
`0400`, and symlink/staging counts are zero. Fetching made no canonical,
analytics, publication, deployment, or scheduler write.

## Equivalence diagnosis

The first post-fetch census incorrectly used reacquisition `fetched_at` as
canonical Identity `ingested_at`, making every new package appear to mismatch
all three Identity families. Anonymous field-level comparison showed that the
accepted families preserve a different, shared row-level build timestamp.

Commit `6802886b195b30c11ae1e52542214667c6d2e681` implements ADR 0143. It
retains actual source observation time while requiring one non-null canonical
replay timestamp per family and equality across Instrument Master, Provider
Identity, and Resolver. The 1.1 profile map also reports discovered
dual-profile mismatches as unbound instead of calling them physically missing.

The corrected four-process, network-disabled census covered the complete 303
canonical sessions and all 303 source packages:

| Profile | Exact | Mismatch | Missing | Custody failure | Duplicate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `current_v1` | 58 | 245 | 0 | 0 | 0 |
| `pre_etv_governance_v1` | 243 | 60 | 0 | 0 | 0 |

- Current report SHA-256:
  `955307e349e142caa7bfd7b71bf95028fdce64cb53db5f5430de886e83f2a566`
- Legacy report SHA-256:
  `1f2245fadeb2a8a988528ca9ab0af07411594bcfe53c80b1871a59ba6c09591a`
- Profile-map file SHA-256:
  `888e34e48810c6e6ec99f53a10a3e8fdf61f3e00d7fdc549093293d5225d7803`
- Profile-map logical fingerprint:
  `dfa33698932ad7a1c78de230802c3c61833822194efc841413650e945e7a2d93`

Exactly 301 sessions are bound once: 58 current and 243 legacy. The 22 newly
exact legacy sessions cover 2026-07-17 through 2026-08-18 excluding
2026-08-13. The reacquired 2026-08-13 and 2026-08-19 packages are custody-
valid but remain unbound under both profiles.

The two unbound packages contain genuine later provider revision:

- 2026-08-13 accepted/reacquired counts are 9,932/9,934 Instruments,
  13,106/13,104 Identity rows, and 9,932/9,934 Resolvers;
- 2026-08-19 accepted/reacquired counts are 9,947/9,961 Instruments,
  13,120/13,127 Identity rows, and 9,947/9,961 Resolvers;
- stable IDs, CIK/FIGI fields, names, exchanges, and provider update times also
  differ. No timestamp or ETV-only compatibility rule can make either package
  exact.

## Candidate, plan, and canonical Apply

Only the 22 exact sessions were normalized. The owner-only candidate contains
287,298 observations in 22 Parquet plus 22 manifests, totaling 21,785,110
bytes. All candidates formally reconstruct accepted Identity under the bound
legacy profile.

The no-write append plan records:

- plan SHA-256:
  `f8f733aca792dc46279af937a8cb9c0165732eca10cbefa17f64a7ffd2fa1497`;
- logical fingerprint:
  `969154d7942e231ffc86c03a84ab4c26bd1c5764e5b3c2a8a6309fd85d5cc967`;
- pre-state fingerprint:
  `27dccc3039aed87dce903f41b55f488bd0b07a67c47885449b957c98b4ad49f5`;
- 22 absent partitions, 44 files, and 21,785,110 bytes.

The ordinary Apply published all 22 partitions and formally reread all 22.
It reported zero external requests, overwrites, and deletions. A separate
`verify_then_complete` postflight reused all 22, published zero files/bytes,
and repeated post-state fingerprint
`12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`.

The authoritative current-context reader then reported 301 manifests, 301
Parquet files, 3,687,175 source observations, 3,844 source artifacts, no
source-only dates, and only 2026-08-13 / 2026-08-19 absent from canonical
source custody. Whole `/data` is 3,958 files / 1,877,724,006 bytes with zero
symlinks and zero publication residue.

## Verification and authority

The focused replay/profile/custody suite passed 37 tests. The complete backend
suite passed 2,061 tests with two pre-existing dependency deprecation warnings.
Repository diff and Python compilation checks passed.

This transition changes normalized historical Identity source custody only.
Historical Coverage, point-in-time membership, lifecycle, corporate actions,
adjustments, costs, research readiness, performance claims, Production,
publication, deployment, scheduler, and user access remain unchanged and
unauthorized.
