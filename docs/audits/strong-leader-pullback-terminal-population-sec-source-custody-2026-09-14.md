# Strong-Leader Pullback Terminal-Population SEC Source Custody Audit — 2026-09-14

## Chronology correction

The first private plan/source pair was rejected from current authority because
its manually supplied `planned_at=2026-09-14T10:30:00Z` followed the actual
source acquisition at approximately 06:36Z. All three response payloads were
physically valid, but the provenance order was not.

Revision `77c6058cedf1d41584171ad5149a2f3c36e05925` adds two fail-closed rules:

1. a plan cannot be constructed with a future time; and
2. acquisition and formal reread reject a first source observation that
   precedes the bound plan.

The superseded V1 plan and source remain rejected private lineage. They do not
feed current status, fact adjudication, outcomes, coverage, or research.

## Authoritative V2 result

Plan V2 was frozen at `2026-09-14T06:43:39Z`. Source V2 began at
`2026-09-14T06:44:26.624111Z` and completed at
`2026-09-14T06:44:27.750244Z`, preserving the required order.

The stable-ID-bound package contains all three planned SEC primary documents:

- one Form 25-NSE dated 2025-12-10;
- one structured Form 8-K dated 2025-12-11; and
- one Form 15-12G dated 2025-12-22.

It used three network requests, zero retries, and retains 73,520 document
bytes. Each response is `text/html`. Direct byte comparison confirms that all
three V2 documents equal their V1 response bytes; the correction changes the
provenance clock and binding, not source content.

## Exact evidence

- Plan implementation revision:
  `77c6058cedf1d41584171ad5149a2f3c36e05925`
- Plan V2 SHA-256:
  `6986c5e1f2b5c9eb863f1db6284c65a47d25edb977dddee2633b8b34547a27f5`
- Plan V2 logical fingerprint:
  `3acbd745b320301c3aeb52db89e06ac58b07e64511ed13f348f5f1f0e61ab84a`
- Source V2 manifest SHA-256:
  `f0f2ab15129bd3acf4d8ef7d88ca04edf6df84cf625964aa8ab401d23fe96188`
- Source V2 logical fingerprint:
  `62e4d1d01cf9cd8215267e980fb8694820f51880cdcd2f176d5336e32f4b81b1`
- Source V2 artifact-binding fingerprint:
  `4a962b4a8c7eaed0e4148a2f5046047e98c0e64685a5896d4e58eaa89643ab9f`
- Plan V2:
  `/home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v2/terminal-population-sec-source-plan.json`
- Source V2:
  `/home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content/source=20260914-v2`

Exact source replay returned `already_present` with zero network requests.
Directories have mode `0700`, files have mode `0400`, and no symlink, partial,
or staging residue exists.

## Verification and authority

Eight focused chronology tests passed. The complete API regression passed
2,758 tests in 272.10 seconds with two unchanged dependency warnings.

The next gate is a deterministic content census and field adjudication over
only these three files. Raw custody does not prove a listed-security identity,
event, cessation, legal delisting, consideration, terminal value, strategy
outcome, or return.

Credential material was neither printed nor retained. No canonical `/data`,
Historical Coverage, research admission, Candidate, publication, deployment,
or scheduler state changed.
