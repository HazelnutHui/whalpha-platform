# ADR 0249: Reuse Hardened SEC Custody for the Single Residual Document

## Status

Accepted.

## Context

The frozen residual plan requires only one new document: the exact Fifth Third
424B3 identified in retained SEC Submissions metadata. Building another broad
download framework would add duplicate code and operational risk.

The existing listed-consideration source path already enforces bounded SEC
transport, private User-Agent handling, request rate and retry ceilings,
response URL/type/size/hash checks, atomic per-document checkpoints, owner-only
permissions, formal reread, and restart-safe adoption.

## Decision

Reuse those hardened document-artifact and transport mechanics behind a new
one-document manifest bound to the residual plan. The only allowed request is
sequence 174 and its frozen URL, accession, CIK, target stable ID, and proposed
consideration stable ID.

Permit no more than two requests per second, three retries for the one document,
or 64 MiB of retained content. A changed response URL, content metadata, bytes,
hash, plan fingerprint, or custody layout fails closed. A completed checkpoint
must be formally reread before resume or zero-network adoption.

## Consequences

The new path adds only a small plan-specific manifest and orchestration layer;
it does not duplicate the transport implementation. The exact source can be
retrieved once and then replayed without network access.

Acquisition itself grants no identity, terminal value, outcome, strategy
label, return, `/data` or Historical Coverage write, research admission,
Candidate result, publication, deployment, or scheduler change. Credential
material is neither printed nor retained in the source package.
