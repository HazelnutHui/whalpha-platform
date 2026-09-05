# Inactive Lifecycle Source Package Audit — 2026-09-05

## Completed source custody

| Evidence | Value |
| --- | --- |
| Anchor | `2026-07-16` |
| Implementation revision | `0c957d72d599179af425be6a59a225071947dabb` |
| Status | `published` in owner-only temporary custody |
| Requests / pages | 24 / 24; natural completion |
| Records | 23,260; all `active=false` |
| Last page | 260 records |
| Sanitized page bytes | 6,622,891 |
| Complete physical package | 26 files / 6,644,157 bytes |
| Duplicate ticker values | 132 |
| `delisted_utc` present | 22,754 |
| `last_updated_utc` present | 23,260 |
| CIK present | 19,159 |
| Composite FIGI present | 5,786 |
| Share-class FIGI present | 5,223 |
| Package logical fingerprint | `5b298512378f80fc5e72eb90bf05b588feb91c1ea1caedd802c8d54ac8cee7fb` |
| Manifest SHA-256 | `71d8e20c97b4df91467768386585e13f097b2ae92ff21782987a356ea499b879` |

All package directories are mode `0700`; all 26 files are mode `0400`; the
formal independent reread found zero symlinks. Provider request IDs and
pagination URLs were removed, and credential-bearing material was rejected.
Credential-free cursor parameters remain inside the owner-only package solely
for request-chain proof.

## Boundary

This proves complete physical observation of the exact provider query at Dell
observation time. It does not prove when each historical record first became
available, last tradable session, terminal reason, merger consideration, or
successor identity. Ticker duplicates and records without stable security
identifiers must not be joined by ticker alone.

The package is `outcome_reconciliation_only`. It has not been normalized,
resolved, applied to `/data`, published as Historical Coverage, consumed by a
model, transferred to OCI, or exposed to the website.

## Latest-history anchor and comparison

The same boundary then acquired the latest canonical EOD anchor `2026-09-03`
under clean implementation revision
`87e753e2389b118c878e09d096849aacb0ae7694`:

| Evidence | Value |
| --- | --- |
| Requests / pages | 24 / 24; natural completion |
| Records | 23,469; all `active=false` |
| Last page | 469 records |
| Sanitized page bytes | 6,692,893 |
| Complete physical package | 26 files / 6,714,161 bytes |
| Duplicate ticker values | 143 |
| `delisted_utc` present | 22,963 |
| `last_updated_utc` present | 23,469 |
| CIK present | 19,348 |
| Composite FIGI present | 5,933 |
| Share-class FIGI present | 5,361 |
| Package logical fingerprint | `8ae15be74aa8c554ab83075346f93c3d966cec72811d47375f53a91a8734ff98` |
| Manifest SHA-256 | `93d60ef65c5a5095954af996a04a4a69d9b4bc84dbae1a87fe773f12596a67b8` |

An anonymous offline comparison found 262 full source rows added and 53 old
rows absent or revised, for net growth of 209. Exactly 262 latest-anchor rows
carry a `delisted_utc` date from 2026-07-17 through 2026-09-03. Of the full
latest package, 17,536 rows lack an accepted stable FIGI, 5,361 select
share-class FIGI, and 572 select composite FIGI; only 1,631 selected IDs match
an instrument seen in the 303 canonical Instrument snapshots. Within the new
window, 135 rows have such an exact stable-ID match.

These are resolution-census counts, not accepted lifecycle rows. The 53
removed/revised observations prove that provider history can revise, and the
large no-stable-ID population makes a ticker-based shortcut unacceptable.

## Unchanged canonical state

The network-free context report after both acquisitions still found 3,958 `/data`
files / 1,877,724,006 bytes, inventory fingerprint
`12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`,
zero symlinks and zero publication residue. Active EOD, Identity, Activation,
Market Intelligence, and Snapshot identities were unchanged.
