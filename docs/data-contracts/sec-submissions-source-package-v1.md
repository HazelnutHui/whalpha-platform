# SEC Submissions Source Package V1

## Purpose

`sec-submissions-source-package/1.0` retains one exact observed version of the
official SEC `submissions.zip` archive before accession and filing-time
normalization. It supplies source custody only.

## Profile and transport boundary

| Field | Value |
| --- | --- |
| Package | `sec-submissions-source-package/1.0` |
| Checkpoint | `sec-submissions-source-checkpoint/1.0` |
| Source family | `submissions_bulk_archive` |
| URL | `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip` |
| Archive file | `submissions.zip` |
| Range chunk | 128 MiB |
| Maximum archive / chunks | 8 GiB / 64 |
| Maximum members | 1,000,000 |
| Maximum expanded bytes | 128 GiB |
| SEC request rate | at most two per second, serial |

The exact profile is part of formal reading. A Company Facts package cannot be
read as a Submissions package even though both reuse the same transport and
checkpoint implementation.

HEAD freezes content type, length, Last-Modified, ETag, range support, and
observation time. Ranges use `If-Match`, exact Content-Range, ETag,
Last-Modified, content length, consecutive offsets, and per-range SHA-256. A
remote nightly change stops the run rather than combining versions.

## Custody and recovery

The package contains `submissions.zip`, `checkpoint.json`, and `package.json`.
Completed files are mode `0400`, the directory is `0700`, and the sibling lock
is `0600`. An interrupted uncommitted tail is truncated to the last bound
range on resume. A completed orphan may be adopted only after full formal
reread.

Central-directory validation requires unique root
`CIK##########.json` members and optional historical
`CIK##########-submissions-###.json` shard members, with exactly one root for
every observed CIK, supported compression, no encryption, and bounded
member/total expansion. One exact bounded printable `placeholder.txt` member
is allowed; every other non-CIK member is rejected. Full decompression, CRC, JSON,
parallel-column consistency, accession uniqueness, acceptance timestamps, and
older shard coverage are deferred to the payload census.

## Authority boundary

The snapshot observation time does not prove when historical records were
known. Downstream normalization must preserve accession, filing date,
acceptance datetime, form, amendment state, report date, file metadata, former
names, tickers/exchanges, and root/shard relationships as provided.

CIK remains a filer key rather than a stable security key. This source package
creates no stable identity, canonical lifecycle or fundamental fact, research
readiness, Candidate result, publication, deployment, or scheduler authority.
