# Strong-Leader Pullback Listed-Consideration Source V1

## Purpose

`strong-leader-pullback-listed-consideration-source/1.0` retains the exact 12
424B3 documents frozen by the listed-consideration source plan. It is private
raw-source custody, not an identity decision or terminal-payoff dataset.

## Package layout

~~~text
source=*
  manifest.json
  request=000001/
    document.bin
    artifact.json
  ...
~~~

Directory names use the frozen plan sequence and therefore need not be
contiguous. The package and request directories use mode `0700`; files use
`0400`. A `.source=*.partial` sibling is resumable state, not a completed
package.

## Artifact binding

Each `artifact.json` records and validates:

- clean implementation revision and exact plan-decision fingerprint;
- target and proposed consideration stable IDs, candidate CIK, accession,
  form, and exact request URL;
- UTC observation time, normalized content type, byte count, physical SHA-256,
  and retry count; and
- explicit zero authority for identity assignment, terminal value, canonical
  data, Historical Coverage, and research admission.

Formal reread requires canonical JSON, exact plan agreement, owner-only
metadata, the exact two request members, matching file size, and a fresh
document hash.

## Completion manifest

Completion requires every one of the 12 frozen decisions. The manifest binds
the source-plan report SHA-256 and logical fingerprint, all implementation
revisions, first and completion times, request and retry counts, total bytes,
content-type counts, and a fingerprint over all artifacts.

A manifest-bearing partial package is adoptable without a network request only
when it contains the exact complete member set and every document, artifact,
aggregate, permission, and plan binding passes formal reread. Final and partial
packages may not coexist.

## Network and authority boundary

- HTTPS `GET` only to the exact SEC archive URLs frozen in the plan;
- a shared maximum of two requests per second;
- at most three retries and 64 MiB per document;
- private SEC User-Agent loaded but never retained or printed;
- no content interpretation in this contract; and
- zero security assignments, terminal values, lifecycle facts, strategy
  labels, `/data` writes, Historical Coverage writes, admissions, Candidate
  writes, publications, deployments, or scheduler changes.
