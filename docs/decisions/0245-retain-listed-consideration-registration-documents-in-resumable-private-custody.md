# ADR 0245: Retain Listed-Consideration Registration Documents in Resumable Private Custody

## Status

Accepted.

## Context

ADR 0244 froze one exact 424B3 registration document for each of 12
non-election listed-stock merger-consideration cases. The plan binds candidate
CIKs and stable security IDs, but those candidates cannot receive identity
authority until the document content proves the transaction, target common
security, consideration share class, and exchange ratio.

A network interruption must not force already verified responses to be fetched
again. Conversely, an incomplete, changed, redirected, or weakly bound response
must never be silently accepted.

## Decision

Retain only the 12 frozen 424B3 documents in a dedicated source-custody
contract.

1. Bind each response to the plan decision, target stable ID, proposed
   consideration stable ID, candidate CIK, accession, exact URL, clean
   implementation revision, observation time, content type, byte count, hash,
   and retry count.
2. Use one shared serial limiter of at most two requests per second, no more
   than three retries per document, and a 64 MiB response limit.
3. Synchronize and atomically rename each completed request directory. On
   restart, formally reread and rehash every completed response before it is
   skipped.
4. Remove only an exact owner-controlled per-request staging directory left by
   interruption. Reject unknown members, unsafe permissions, symlinks,
   coexisting final/partial packages, and changed response metadata.
5. After all 12 documents are complete, write an aggregate manifest and
   atomically rename the package. A complete manifest-bearing partial package
   may be adopted only after a full formal reread, without another request.
6. Keep directories and files at `0700/0400` in owner-only Dell state outside
   `/data` and Git. Load the private SEC contact identity only through the
   existing protected configuration loader and retain none of it.
7. Treat all document bytes as uninterpreted source evidence. Acquisition
   assigns no security identity, terminal value, lifecycle fact, strategy
   outcome, Historical Coverage, research admission, Candidate result,
   publication, deployment, or scheduler authority.

## Consequences

The network operation is finite, restart-safe, and independently verifiable.
The completed package can feed one later deterministic content adjudication
without broad issuer search or repeated downloads.

This remains a first-strategy evidence package, not a general SEC archive or
an issuer master.
