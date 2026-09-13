# ADR 0230: Retain Transition-Period SEC Primary Documents in Resumable Private Custody

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0229 froze 219 distinct SEC primary-document requests across 22 batches.
The documents are needed to measure which first-strategy lifecycle fields the
official issuer filings can actually support. A shell loop would not provide
durable request identity, per-document integrity, safe restart, or a formal
boundary between raw content and interpreted facts.

The source package may be interrupted by a network failure or operator stop.
Completed responses must not be downloaded again, while an incomplete or
altered response must never be silently adopted.

## Decision

Implement one source-custody contract for the exact ADR 0229 plan.

1. Bind every artifact to its plan sequence, stable instrument ID, CIK,
   accession, form, exact URL, and plan-item fingerprint.
2. Use one independently bounded transport per document while sharing one
   serial two-request-per-second limiter. Allow at most two retries for that
   document and 64 MiB of response content.
3. Write each response into a private staging directory, hash it, write a typed
   artifact, synchronize both, and atomically rename the request directory.
4. On resume, formally reread and hash every completed request before skipping
   it. Remove only an exact, owner-controlled per-request staging directory
   left by interruption; reject every unknown member.
5. After all 219 documents exist, write one aggregate manifest and atomically
   rename the package. A complete manifest-bearing partial package may be
   formally reread and adopted without another network request.
6. Keep directories/files at `0700/0400` in owner-only Dell state outside
   `/data` and Git. Load the SEC contact identity only through the existing
   protected configuration loader; never retain it in an artifact or log.
7. Acquisition retains uninterpreted source bytes only. It grants no listed-
   security identity, lifecycle or terminal fact, Historical Coverage,
   research admission, Candidate, publication, deployment, or scheduler
   authority.

## Consequences

- An interruption loses at most the currently staged response; every completed
  request remains independently verifiable and reusable.
- The immutable package can support a later deterministic field-extraction
  census without repeating the network acquisition.
- The package is deliberately not a general SEC archive and cannot expand
  beyond the 219 frozen requests.

## Rejected alternatives

### Download a whole batch before checkpointing

Rejected because interruption could repeat already successful requests and
would weaken response-level provenance.

### Treat filing presence as a lifecycle fact

Rejected because issuer filings, listed securities, transaction completion,
and terminal return are different facts requiring explicit resolution.
