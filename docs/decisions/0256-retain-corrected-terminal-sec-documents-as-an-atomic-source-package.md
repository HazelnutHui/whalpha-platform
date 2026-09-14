# ADR 0256: Retain Corrected-Terminal SEC Documents as an Atomic Source Package

## Status

Accepted.

## Context

ADR 0255 freezes three exact official SEC primary-document requests for the one
case added by the corrected EOD terminal population. The established 219-file
custody runner is deliberately bound to its immutable original plan and must
not be repurposed or rewritten.

Only three documents are required. A smaller atomic package can preserve the
same host, rate, retry, size, hash, permission, and formal-read guarantees
without duplicating the large batch-resume state machine.

## Decision

1. Consume only the formally reread ADR 0255 plan and the protected SEC User-
   Agent configuration. Never retain or print credential material.
2. Use one shared two-request-per-second limiter, at most two retries per
   request, HTTPS GET to the exact planned URLs, and a 64-MiB response ceiling.
3. Retain each response with a physical SHA-256 and an artifact that binds its
   plan-item fingerprint, stable ID, CIK, accession, form, URL, observation
   time, content type, byte count, and retry count.
4. Build the complete three-document package in one owner-only staging
   directory. On any failure, remove only that exact owned staging directory;
   publish atomically only after all three artifacts and the manifest exist.
5. Formally reread every document and binding after publication. Exact replay
   returns the existing package without a network request; changed or unsafe
   content fails closed. The first source observation must not precede the
   frozen plan time.
6. Do not parse content or create lifecycle facts, terminal outcomes, strategy
   labels, returns, canonical `/data`, Historical Coverage, research admission,
   Candidate, publication, deployment, or scheduler state.

## Consequences

The new case gains complete raw primary-source custody under a bounded and
reproducible process. Because the package is only three files, atomic restart
is simpler and safer than partial batch resumption. Interpretation remains a
separate versioned stage.
