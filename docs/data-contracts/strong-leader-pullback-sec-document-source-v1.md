# Strong-Leader Pullback SEC Document Source V1

## Purpose

`strong-leader-pullback-sec-document-source/1.0` retains the exact 219 SEC
primary documents frozen by ADR 0229. It is private raw-source custody, not an
interpreted lifecycle dataset.

## Package layout

~~~text
source=*
  manifest.json
  request=000001/
    document.bin
    artifact.json
  ...
  request=000219/
    document.bin
    artifact.json
~~~

The published directory and each request directory use mode `0700`; every
file uses `0400`. A resumable sibling named `.source=*.partial` is not a
published package. Each request becomes resumable only after its response and
artifact have been synchronized and atomically renamed from an exact staging
directory.

## Artifact binding

Every `artifact.json` records and validates:

- the clean implementation revision and frozen plan-item fingerprint;
- sequence and batch, stable `instrument_id`, CIK, accession, form, and URL;
- UTC observation time, normalized content type, byte count, physical SHA-256,
  and retry count; and
- explicit zero/false authority counters.

Formal readback compares all fields with the corresponding plan item, hashes
the retained document again, and requires canonical JSON bytes.

## Completion manifest

Completion requires all 219 sequences, all 22 batches, and an exact binding to
the plan SHA-256 and logical fingerprint. The manifest reconciles first and
completion times, implementation revisions, request/retry counts, total
bytes, content-type counts, and a fingerprint over all artifact records.

A manifest-bearing partial is adoptable only when it already contains the
entire exact package and every document, artifact, aggregate, permission, and
plan binding passes formal reread. Coexisting final and partial packages fail
closed.

## Network and authority boundary

- HTTPS `GET` only to the URL frozen in the plan;
- one shared maximum rate of two requests per second;
- at most two retries per document and 64 MiB per response;
- SEC User-Agent loaded from owner-only configuration and never retained;
- no parsing or interpretation of document content in this contract; and
- zero security assignments, terminal outcomes, triggers, returns, metrics,
  canonical `/data` writes, Historical Coverage writes, admissions, Candidate
  writes, publications, deployments, or scheduler changes.
