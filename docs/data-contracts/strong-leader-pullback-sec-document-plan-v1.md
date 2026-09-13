# Strong-Leader Pullback SEC Document Plan V1

## Purpose

`strong-leader-pullback-sec-document-plan/1.0` freezes the exact official SEC
primary documents eligible for the first lifecycle-content acquisition. It is
a no-network plan, not source custody or lifecycle evidence.

## Selection and order

The only accepted input is a formally reread ADR 0228 pilot. Every candidate
whose filing date is on or after its last canonical price observation is
included. Every earlier candidate is excluded from this first acquisition.

The initial plan contains exactly 219 unique accessions and URLs. Items are
ordered by stable `instrument_id`, filing date/time, and accession, then
assigned one-based request sequence, batch number, and batch position.

## Request envelope

| Field | Fixed value |
| --- | --- |
| Host | `www.sec.gov` only |
| Method | HTTPS `GET` |
| Encoding | `identity` |
| Batch size | 10 |
| Batch count | 22; final batch has 9 |
| Maximum rate | 2 requests/second |
| Maximum retries | 2 per document |
| Maximum document | 64 MiB |

Each item retains its stable ID, CIK, accession, form, filing/acceptance time,
primary-document relative path, exact URL, structured items, locator
categories, and relation to the last observation. Safe relative subdirectories
are allowed; absolute paths, traversal, backslashes, controls, queries, and
fragments are rejected.

## Custody and non-authority

One canonical `plan.json` is created exclusively and atomically in a new
owner-only `build=*` child. Directory/file modes are `0700/0400`; typed and
canonical-byte reread follows publication.

External requests, credential reads, document writes, security assignments,
terminal outcomes, triggers, forward outcomes, metrics, `/data`, Historical
Coverage, research admission, Candidate writes, publication, deployment, and
scheduler changes are fixed to zero.
