# ADR 0229: Freeze Transition-Period SEC Primary-Document Acquisition

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0228 retained 2,144 SEC filing locators for the first strategy's 64 frozen
lifecycle cases. Of those, 219 were filed on or after the last canonical price
observation. They are the smallest complete transition-period population that
can be selected without reading document contents or strategy outcomes.

Fetching all 2,144 documents would add mostly pre-transition history before
the 219 closest official filings have been tested. Fetching only convenient
forms or hand-picked cases could hide unsupported or conflicting evidence.

## Decision

Freeze one no-request acquisition plan containing every 219 transition-period
candidate and no pre-last-observation candidate.

1. Bind the plan to the exact ADR 0228 pilot hash and fingerprint.
2. Construct the official archive URL from the filer CIK, accession without
   hyphens, and safe relative `primaryDocument` path. CIK and accession remain
   separate identifiers.
3. Require 219 distinct accessions and URLs. Order deterministically by stable
   instrument ID, filing time, and accession.
4. Divide requests into 22 deterministic batches: 21 batches of ten and one
   batch of nine. No batch may be expanded dynamically.
5. Cap request rate at two per second, retries at two per document, and one
   document at 64 MiB. Allow only HTTPS GET to `www.sec.gov` with identity
   encoding and the separately configured SEC User-Agent.
6. The plan itself makes no request, reads no credential, and writes no
   document. Execution requires a separate resumable source-custody contract.
7. Document content remains source evidence. It does not itself authorize a
   security assignment, terminal fact, Historical Coverage, research,
   Candidate use, publication, or deployment.

## Consequences

- The next network stage is finite, reproducible, and can resume by exact
  batch without rescanning the SEC archive.
- The 219 requests preserve all transition-period forms rather than selecting
  only Form 25 or Form 15 after inspecting coverage.
- Pre-transition merger and tender documents remain retained in ADR 0228 and
  can be added later only when the transition documents prove that a specific
  fact requires them.
- A commercial lifecycle source is evaluated only after this official
  document subset produces a measured residual field gap.

## Rejected alternatives

### Fetch all 2,144 candidates immediately

Rejected because the transition-period subset is complete for the first
document-content pilot and is materially smaller.

### Fetch one preferred form per security

Rejected because form availability is not uniform and convenience selection
could hide conflicting evidence.
