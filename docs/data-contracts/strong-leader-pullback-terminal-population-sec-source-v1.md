# Strong-Leader Pullback Terminal-Population SEC Source V1

## Purpose

`strong-leader-pullback-terminal-population-sec-source/1.0` retains every SEC
document in the corrected-population source plan as one immutable private raw-
source package. It does not interpret content.

## Package

```text
source=*
  manifest.json
  request=000001/
    document.bin
    artifact.json
  ...
```

Directories use mode `0700`; files use `0400`. Each artifact binds the source-
plan item fingerprint, stable ID, CIK, accession, form, URL, observation time,
content type, size, response hash, and retry count. The manifest binds the
complete artifact set and exact source-plan physical and logical identities.

## Acquisition and restart

Only exact planned HTTPS URLs on `www.sec.gov` may be requested. One shared
limiter enforces at most two requests per second; each response has at most two
retries and 64 MiB. The protected User-Agent is never persisted or printed.

The complete small package is built under one exact owner-only staging path.
Any ordinary failure removes only that staging path. Publication is one atomic
rename after all planned documents are complete. Exact replay performs formal
readback with zero network requests; a conflict fails closed. Acquisition and
formal reread both require the first source observation to be on or after the
bound plan time.

## Non-authority

Source custody proves bytes and provenance only. It grants no listed-security
fact, event, last-trade time, legal delisting, consideration, terminal value,
strategy outcome, return, `/data`, Historical Coverage, research admission,
Candidate, publication, deployment, or scheduler authority.
