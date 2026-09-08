# Corporate-Action Source Audit — 2026-09-08

## Scope

This audit records the first real Massive V1 split and dividend source packages
created by ADR 0169. The inclusive provider-date range is 2025-06-23 through
2026-09-04, matching the complete current canonical EOD interval.

Execution used clean Dell main revision
`08eb33c60896be783547aae55704b57caafca49c`. Source custody remains owner-only
under `/tmp/whalpha-corporate-actions-20260908T082632Z`. No raw row is copied
into this document.

## Result

| Evidence | Split | Dividend |
| --- | ---: | ---: |
| Endpoint | `/stocks/v1/splits` | `/stocks/v1/dividends` |
| Requests/pages | 1 | 14 |
| Records | 1,949 | 68,150 |
| Last-page rows | 1,949 | 3,150 |
| Sanitized source-page bytes | 440,130 | 24,033,055 |
| Valid in-range dates | 1,949 | 68,150 |
| Invalid dates | 0 | 0 |
| Duplicate nonempty source IDs | 0 | 0 |
| Unexpected source fields | 0 | 0 |
| First/last event date | 2025-06-23 / 2026-09-04 | 2025-06-23 / 2026-09-04 |
| Distinct provider tickers | 1,668 | 13,759 |
| Manifest SHA-256 | `536235ba0c2e56b2975b32901f0175fb2a63ff0ced01cfbc2e39bdaeac9fc790` | `a53aa90c79a77d455cb6cc97668535799106c47560d874706d30b53f8c8ce1cc` |
| Logical fingerprint | `48df7798303c3a3214ad1cd680471c8ecef79e9a4343499adaf4cf444026e1cf` | `7aecd9f6584a0d77d5a0b3a2ff024743170c38716c6aab849767624aaa765d39` |

The split source contains 337 forward splits, 1,384 reverse splits, and 228
stock dividends. Every documented split field is present on every row.

The dividend source contains 65,113 recurring, 1,013 special, 640 irregular,
157 supplemental, and 1,227 provider-`unknown` distributions. Cash amount,
currency, distribution type, ex-date, frequency, ID, and ticker are present on
all 68,150 rows. Declaration date is present on 66,676; pay date on 67,831;
record date on 67,984; and both provider historical factor and split-adjusted
cash on 56,324. Missing optional fields remain null evidence, not imputed
values.

## Custody proof

- Natural pagination completed for both sources below the 16-page and
  80,000-row ceilings.
- A separate credential-free formal reread passed after acquisition and after
  moving the containing temporary namespace to its observation-time label.
- The temporary tree contains 19 regular files / 24,489,297 total bytes. All
  three directories are mode `0700`; all completed files are mode `0400`; no
  symlink is present.
- Request IDs, pagination URLs, API credentials, and Authorization material
  are absent from retained pages. Credential-free pagination parameters remain
  only in the owner-only page/checkpoint chain.
- The post-run network-prohibited current-context report kept `/data` at 4,060
  files / 2,009,699,645 bytes with inventory fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks, and zero publication residue. Production remains unchanged.

## Interpretation and remaining gates

The result verifies current V1 technical access, real response fields, full
pagination for this date range, and recoverable source custody. It does not
verify source completeness outside the requested range, historical revision
availability, or when each fact first became knowable.

The 13,759 dividend tickers exceed the same-day active Identity count because
the endpoint covers a broader security and historical listing population.
Ticker therefore cannot be used as a canonical key or silently filtered to the
current active Universe. The next adapter must resolve each row against the
exact event-date Identity view, preserve one source observation per provider
event/revision, and quarantine zero/multiple stable-ID matches.

No canonical Corporate Action, Adjustment Ledger, Historical Coverage,
analytics, performance result, Snapshot, bundle, OCI deployment, scheduler, or
Production transition is authorized by this audit.
