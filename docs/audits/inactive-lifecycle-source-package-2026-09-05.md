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

## Unchanged canonical state

The network-free context report after acquisition still found 3,958 `/data`
files / 1,877,724,006 bytes, inventory fingerprint
`12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`,
zero symlinks and zero publication residue. Active EOD, Identity, Activation,
Market Intelligence, and Snapshot identities were unchanged.
