# Quant Research Market-State Qualification Audit — 2026-09-16

## Verdict

`ready_for_campaign_protocol_design`

The outcome-blind Market-State Vector passed its frozen qualification and one
complete independent replay. This permits finite Campaign Three protocol
design only. It does not authorize Development outcomes, factor admission,
model construction, Candidate activation, publication, broker access, or
trading.

## Bound execution

- source revision: `1c4f2bbf055492ea11100c79cac28e05698fe8a1`
- target sessions: 287 XNYS sessions, 2025-06-23 through 2026-08-12
- source warm-up: 20 preceding XNYS sessions
- benchmark metrics: 287 / 287 available for all six definitions
- reconstructed metrics: 267 / 287 jointly available
- reconstructed halves: 123 / 143 and 144 / 144 jointly available
- distinct values: 287 for every benchmark metric; 267 for every reconstructed
  metric
- median crossings: 24 to 66 across the ten metrics
- longest same-side run: 16 to 48 sessions
- pairwise correlations: 45; maximum absolute correlation 0.7909587615

The first 20 target sessions have zero reconstructed Primary members in the
frozen census. They remain explicitly unavailable and are never zero-filled.

## Reproduction and custody

The original and replay reports are owner-only directories at mode `0700` with
one canonical report file at mode `0400`. Both report files are 1,104,826 bytes
and have SHA-256:

`8f3ec454b2626b3a2feab79e8f38e3ae014c0d853e7698d9266a32dca224b02a`

Their report logical fingerprint is:

`20b496eb76ba6597b6937bf2e79924a65491631767e7e1c4ac186281bba04ee3`

Formal reread returned equal typed reports and the second runner returned
`replay_match=true`.

## Side-effect proof

Both successful runs reported:

- external requests: 0
- Development outcome reads: 0
- canonical `/data` writes: 0
- Production writes: 0

## Defect found and corrected

The first attempt correctly stopped before report creation because the first
20 sessions have an empty reconstructed population and the session contract
did not reconcile the audit denominator used for explicit unavailability.
The contract now represents these sessions as declared members 0, actual
observations 0, audit denominator 1, and unavailable with reasons. A regression
test fixes this boundary. The runner also retains only validated member UUIDs
rather than complete Membership row objects, reducing the observed same-stage
resident memory from roughly 1.7 GB to roughly 0.9 GB without changing inputs
or gates.

## Next boundary

Campaign Three remains unregistered. The next action is outcome-blind design of
a finite, deduplicated hypothesis set, trial budget, nulls, multiplicity,
stability gates, selection cap, and stop rule under ADR 0287. Validation and
Holdout remain sealed.
