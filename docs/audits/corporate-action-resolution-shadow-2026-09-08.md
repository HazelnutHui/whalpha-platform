# Corporate-Action Resolution Shadow Audit — 2026-09-08

## Scope

This audit records the first real ADR 0170 resolution shadow for the complete
Massive V1 split/dividend source range, 2025-06-23 through 2026-09-04.
Execution used clean Dell main revision
`51dd39405fe2576d8eacc553b9fe0f99f788646a` and the published
`point_in_time_identity` family evidence with logical fingerprint
`d2225da8d4ffd2b7e83ff98b72f75647503690a2aff2c87731c00b115b65fefb`.

The process prohibited network access, treated `/data` as read-only, and wrote
only the owner-only temporary tree
`/tmp/whalpha-corporate-action-resolution-shadow-20260908T091222Z`.

## Result

| Evidence | Split source | Dividend source | Total |
| --- | ---: | ---: | ---: |
| Source rows | 1,949 | 68,150 | 70,099 |
| Resolved exact-date rows | 709 | 41,347 | 42,056 |
| Unresolved rows | 1,240 | 26,803 | 28,043 |

All 70,099 source rows produced exactly one output observation. The complete
result has 42,056 `active` records and 28,043 `quarantined` records over 6,682
distinct resolved stable instrument IDs. Action counts are 337 stock splits,
1,384 reverse splits, 228 stock dividends, and 68,150 cash dividends.

The 304 evidence-bound Identity sessions were all used. A total of 70,060
source rows occurred on an available exact Identity session. Thirty-nine rows
occurred on 11 dates without an exact session and carry
`event_date_identity_unavailable`: 2025-07-04, 2025-08-31, 2025-11-30,
2026-01-19, 2026-01-31, 2026-02-16, 2026-02-28, 2026-05-25, 2026-05-31,
2026-06-19, and 2026-07-03. The other 28,004 unresolved rows carry
`unresolved_ticker`. Every row also carries
`source_available_time_unavailable`; none is point-in-time signal eligible.

## Bound evidence

- Split source manifest SHA-256:
  `536235ba0c2e56b2975b32901f0175fb2a63ff0ced01cfbc2e39bdaeac9fc790`;
  logical fingerprint:
  `48df7798303c3a3214ad1cd680471c8ecef79e9a4343499adaf4cf444026e1cf`.
- Dividend source manifest SHA-256:
  `a53aa90c79a77d455cb6cc97668535799106c47560d874706d30b53f8c8ce1cc`;
  logical fingerprint:
  `7aecd9f6584a0d77d5a0b3a2ff024743170c38716c6aab849767624aaa765d39`.
- Identity evidence manifest SHA-256:
  `5046dd6b3b1f8dd028528636a9caf989bcbb53040082ca0060016b07a49d67a2`.
- Used-Resolver binding fingerprint:
  `4ab01eed484d3da1887519eab5cb5716ca08d39f49c4514c6c3f71d32e0e45bc`.
- Shadow manifest SHA-256:
  `547218cf639bf4e06daa216868bd669cd73e4b69a55f7da4fad072077ffcacb8`;
  logical fingerprint:
  `d45b405b5d595755d3ed7342747701d83796ca895c022f2c19aef2af4ae5acb1`.

The two event-year Parquet artifacts contain 31,023 rows for 2025 and 39,076
for 2026. A separate formal reread revalidated the manifests, Parquet hashes,
schemas, logical fingerprints, modes, business keys, observation semantics,
and aggregate counts. The tree contains five regular files / 5,006,834 bytes,
seven directories, mode `0400` files, mode `0700` directories, and zero
symlinks.

## Pre-census reconciliation

ADR 0170 originally recorded a raw, case-sensitive diagnostic of 708 resolved
split rows and 41,341 resolved dividend rows. The formal mapper normalizes both
source and Resolver tickers by trimming and uppercasing, as required by the
existing Massive mapping contract. Seven resolved rows used that normalization:
the two distinct source-to-normalized forms were `AXIAp` to `AXIAP` and `TpC`
to `TPC`. The final formally reread counts above supersede the preliminary
diagnostic; no nearest-session, latest-ticker, name, or Universe fallback was
used.

## Canonical-state proof and remaining gates

The post-run network-prohibited current-context report passed on clean main
`51dd39405fe2576d8eacc553b9fe0f99f788646a`. `/data` remained exactly 4,060
files / 2,009,699,645 bytes with inventory fingerprint
`16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
zero symlinks, and zero publication residue. Latest canonical EOD and Identity
remain aligned on 2026-09-04 with 304 sessions; Production remains unchanged.

The shadow proves exact-event-date technical stable-ID mapping for its resolved
subset. It does not prove historical source availability, provider revision
history, semantic correctness of every action, canonical Corporate Action,
adjustment factors, lifecycle outcomes, Historical Coverage, or strategy
eligibility. Before any canonical or price-adjustment transition, the next
stage must define repeat-observation/revision diffing and review semantic and
cross-event conflicts. No analytics, Snapshot, bundle, OCI deployment,
scheduler, or website transition occurred.
