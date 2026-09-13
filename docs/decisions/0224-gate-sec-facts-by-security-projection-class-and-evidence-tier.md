# ADR 0224: Gate SEC Facts by Security Projection Class and Evidence Tier

- Status: Accepted
- Date: 2026-09-13

## Context

The five-year filer/security candidate contains 10,681,604 daily stable-
security decisions. A CIK identifies an SEC filer, not a listed share class.
Broadcasting every filer fact to every linked security would duplicate issuer
evidence, misstate per-share semantics, and create a hidden selection rule.

An outcome-blind projection-readiness scan found 6,244,758 admitted common-
stock row-sessions. Of those, 6,122,451, or about 98.0%, belong to a session-
local CIK with one admitted common stock. The remaining 122,307 rows belong to
59,440 multi-common-stock CIK/session groups, with at most seven common stocks
in one group. Separately, 5,977 common-stock rows lack CIK and 9,129 lie on the
two missing source-custody sessions.

Historical knowledge time is a distinct problem. Only 11 of 1,255 link
sessions have a retained source-observed timestamp no later than the next XNYS
open. The other 1,244 sessions cannot be represented as links known at that
historical trading cutoff merely because their date-scoped reconstruction now
exists.

## Decision

1. Preserve normalized SEC facts at filer/CIK grain. A filer observation is
   never silently rewritten as a security or share-class fact.
2. Every security-level fundamental query must register its concept,
   namespace, unit, period/form semantics, filing availability, revision
   selection, projection class, and missing/conflict behavior before feature
   materialization.
3. The conservative first projection class is
   `single_common_security_per_cik_v1`. It requires an admitted daily link,
   `instrument_type=common_stock`, and exactly one admitted common stock for
   that CIK on that session. It may carry an explicitly named issuer-level fact
   to that security for a registered query; it does not convert the underlying
   fact's economic grain.
4. ETF rows, missing-CIK rows, missing-source rows, same-instrument CIK
   conflicts, and identity mismatches are ineligible. They remain in coverage
   denominators.
5. Multi-common-stock CIK groups are not eligible for the default projection.
   A later issuer-shared sensitivity may retain the same issuer fact on each
   member only with explicit group identity, duplicate-exposure controls, and
   a separately registered use. Per-share, share-count, market-cap, and
   class-specific facts require defensible class-level evidence and may not use
   that sensitivity shortcut.
6. Evidence tiers remain separate:
   - `as_operated_next_open` requires the retained source observation no later
     than the registered next-open cutoff;
   - `reconstructed_latest_vintage_development_only` may use an exact dated
     reconstruction only in disclosed exploratory/development sensitivity;
     it is barred from sealed validation, holdout, headline performance, model
     activation, and Production Candidate authority; and
   - `outcome_reconciliation_only` and `source_custody_missing` cannot create a
     predictive fundamental feature.
7. No projection mode authorizes a current CIK, current liquidity, current
   share class, or later filing revision to be pushed backward. Unknown and
   insufficient evidence stays quarantined.

## Consequences

- The first conservative projection covers nearly all currently admitted
  common-stock link rows without hiding the smaller multi-class problem.
- Historical SEC research can continue as clearly labelled development
  sensitivity, but it cannot claim fully point-in-time out-of-sample evidence
  from the current link source.
- Prospective daily source custody accumulates `as_operated_next_open`
  evidence. A commercial or official historical security-master source may
  later expand the admissible history through the same gates rather than
  replacing stable IDs or rewriting the SEC ledger.
- The next implementation step is a small registered issuer-level query set
  and a projection-readiness result, not a broad daily fact Cartesian panel.

## Rejected alternatives

### Broadcast one CIK's facts to every linked security

Rejected because it confuses filer and security grain and duplicates exposures
without a share-class rule.

### Require the current download timestamp for all development work

Rejected as an unnecessarily strong ban on disclosed reconstruction studies.
The reconstructed tier remains barred from validation and performance claims.

### Treat a dated provider response as proof it was historically knowable

Rejected because effective date and source availability are different facts.
