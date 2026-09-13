# SEC Company Facts Source Package V1

## Purpose

This contract retains one exact observed version of the official SEC
`companyfacts.zip` archive before normalization. It is source custody only.

## Remote and transport boundary

| Field | Value |
| --- | --- |
| Package | `sec-companyfacts-source-package/1.0` |
| Checkpoint | `sec-companyfacts-source-checkpoint/1.0` |
| URL | `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` |
| Chunk | 128 MiB |
| Archive / chunks | 8 GiB / 64 maximum |
| Successful HEAD observations | 16 maximum |
| SEC request rate | at most 2 per second, serial |
| Credential retention | none |

HEAD metadata must include exact ZIP content type, positive bounded length,
Last-Modified, ETag, and `Accept-Ranges: bytes`. Each range must return 206 and
match the frozen object identity and exact requested Content-Range. Nightly
object drift stops the run and preserves the prior partial separately.

## Custody and recovery

The package contains `companyfacts.zip`, `checkpoint.json`, and `package.json`.
Completed files are mode `0400`, directories mode `0700`, and the sibling lock
mode `0600`. Checkpoints atomically bind every consecutive range and its hash.
On resume, an uncommitted archive tail is truncated to the bound byte count.
A complete orphan is adopted only after the full completed-tree reader passes.

Formal reread validates the exact file set, typed documents, archive size and
SHA-256, every range hash, and ZIP central-directory census. ZIP members must
be unique root-level `CIK##########.json` files, unencrypted, nonempty, use a
supported compression method, and remain within per-member and total expansion
ceilings.

## Time and semantic boundary

Remote Last-Modified and Dell observation time identify the acquired archive
snapshot; neither is an individual fact's historical availability time. Full
member decompression/CRC, JSON validation, concept normalization, duplicate and
amendment handling are explicitly deferred. Downstream facts must preserve
accession, form, filed date, period/frame, unit, and source occurrence.

CIK is a filer key, not a stable listed-security key. No ticker/CIK-only join,
current-value backfill, taxonomy guessing, first-non-null resolution, canonical
fundamental, research-readiness, analytics, Candidate, or Production authority
is created by this package.
