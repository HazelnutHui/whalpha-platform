# China A-share Local Official-Evidence Reuse and Warning Batch V1

## Purpose

Inventory existing official custody without network access, adjudicate strict
reuse for every frozen priority-plan unit, and prepare a non-executable first
risk-warning acquisition batch.

Versions:

- `china-ashare-local-official-evidence-reuse-census/1.0`;
- `china-ashare-warning-evidence-acquisition-batch/1.0`; and
- `china-ashare-local-official-evidence-reuse-package/1.0`.

## Input and local inventory

The only request-plan input is the final `a58e…` priority-plan package. Local
custody roots must pass their existing owner-only, no-symlink, closed-set,
hash, size, schema, and path-binding readers.

Each inventory descriptor records an official authority, evidence kind,
source package and capture fingerprints, optional source security and stable
subject, exact-binding flag, raw SHA-256, observed publication clock,
effective interval, structured fields, and parse status. Raw bodies are not
searched for positive facts. Fixed challenge markers may be inspected only to
classify a response as blocked.

## Strict reuse

A unit is `reusable` only if one descriptor satisfies all of these conditions:

- exact equality to the request's stable subject, not ticker-only identity;
- an authority admitted by that request;
- retained official raw-byte SHA-256;
- observed UTC publication clock;
- effective interval covering the request interval; and
- every purpose-specific expected field is structurally parsed.

Otherwise the unit remains `network_required`, with deterministic reason
codes and all candidate evidence IDs retained. A zero-result search does not
prove event absence. Text/title heuristics, aggregate sites, challenge bytes,
unknown clocks, partial intervals, and schema failures cannot become positive
evidence.

## Warning acquisition batch

The manifest contains all 492 unresolved risk-warning request IDs in sorted
order with stable subject, source security, effective interval, expected
fields, and one selected primary authority. Shanghai routes to SSE; Shenzhen
routes to CNINFO.

Execution controls are frozen but disabled:

- 492 logical request units;
- sequential execution;
- minimum 1,000 ms request interval;
- maximum 16 MiB response per attempt;
- one initial attempt plus at most one retry for bounded transport/429/5xx
  failure;
- maximum 984 HTTP attempts;
- challenge pages are terminal; and
- no credentials are required or read.

`acw_sc__v2`, `document.cookie`, and `enable javascript` are defensive marker
examples. Detection produces `challenge_blocked`; it never parses an event.

## Raw custody and adjudication input

A raw capture binds batch, request, attempt, authority, requested/final URL,
retrieval time, HTTP metadata, byte count/hash, status, blocker, and challenge
marker. Even HTTP success is only `captured_pending_adjudication`.

An adjudication input additionally requires official document identity/URL
and bytes, exact stable-security binding, observed publication clock,
effective interval, event kind, and warning subtype. Ticker-only and body-
heuristic evidence flags are permanently false.

## Persistence and replay

The closed package contains exactly:

- `local-official-evidence-inventory.json`;
- `official-evidence-reuse-census.json`;
- `warning-acquisition-batch.json`; and
- `official-evidence-reuse-manifest.json`.

Directories use `0700`, files use `0400`, publication uses same-filesystem
atomic rename, and reread verifies canonical JSON, hashes, sizes, schemas,
paths, permissions, symlink absence, and the exact file set. An independent
reverse-input replay must be byte-identical.

## Authority

The package does not authorize network access, outcome reads, return
construction, Factor Discovery, Historical Coverage, backtesting, canonical
Apply, Product publication, deployment, or trading. See [ADR
0309](../decisions/0309-reuse-local-a-share-official-evidence-before-warning-acquisition.md).
