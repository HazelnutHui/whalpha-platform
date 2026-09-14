# Strong-Leader Pullback Terminal Payoff Terms Audit — 2026-09-14

## Verdict

The exact 61-case first-strategy lifecycle population now has a reproducible,
source-literal-bound terminal-payoff term layer. It retains 81 normalized terms
without calculating a terminal return or valuing a complex component.

The source profiles are:

- 37 fully specified fixed-cash structures;
- 13 non-election listed-equity structures;
- seven cash-plus-CVR structures;
- three listed-equity holder-election structures; and
- one cash-or-unlisted-unit election structure.

Sixteen cases contain at least one listed-equity ratio, four contain holder
elections, and eight retain fractional-share cash as a separate adjustment.

## Readiness partition

Combining the source terms with the previously adjudicated cessation state
produces one mutually exclusive next-action partition:

| State | Cases |
| --- | ---: |
| Fixed cash and timing ready | 30 |
| Cessation timing not matched | 9 |
| Listed-security identity and market value required | 12 |
| Contingent-value realization unresolved | 6 |
| Holder election or proration unresolved | 3 |
| Unlisted-unit value unresolved | 1 |

The nine timing cases include one retained conflict and eight unsupported
source timings; their underlying consideration structures remain visible.
None is silently reassigned to another category or treated as a zero payoff.

## Method and bindings

Every normalized value is tied to one exact source literal, character span,
SHA-256 digest, economic kind, and case fingerprint. USD cash is normalized to
cents; share and unit ratios use six decimal places. Binary floats are not
used.

Holder alternatives retain their own cash/ratio terms, source default, and
proration state. Listed-equity issuer names such as source-local acquirer
labels remain locators only; no global issuer or security ID was assigned.
CVRs and unlisted units were not assigned a zero value. A named amount that is
not numeric in the selected primary clause remains unresolved.

Input report SHA-256 values are:

- consideration:
  `834bf44dbc512c70a0722af18fab282c7b885dd881dbf48c126dd01ae0e00120`;
- source-party relation:
  `a44dff5ace2ef6dc9b7cb8487b2bc529732522f215caa482299f0b8c4cd2176a`;
- trading cessation:
  `694e8b01274fdcad9bef2e0178e805df994f2526c190598b665e965541c2fae9`.

The implementation revision is
`fa8f62264ed02078f82ac1b4a9bc4dd2f782aa9a`; the ruleset fingerprint is
`7a9a14f998ffe19d1c8df090c798a711506fd5dc8619dee66bfd9c9ebd2c3de8`.

## Output and verification

The immutable private report is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms/adjudication=20260914-v1/terminal-payoff-terms.json`

- report bytes: 159,804;
- report SHA-256:
  `f0b2e805a46e9f2b3e88432d1c5aa6a8782d095ffdda5790cb8894639d2be1a9`;
- logical fingerprint:
  `00d0651df3da6bcc114a1dbcd270a4a78f41006d741e6fefb1ff2eebabd951fb`;
- custody/output/report modes: `0700` / `0700` / `0400`;
- exact rerun: `already_present` with identical hashes;
- partial directories and symlinks: zero.

Four focused tests, 21 linked tests, and the complete 2,698-test API suite
passed with two unchanged dependency warnings.

## Authority retained at zero

Successor and consideration-issuer stable-ID assignments, canonical lifecycle
facts, terminal outcomes, strategy triggers, forward outcomes, performance
metrics, `/data` writes, Historical Coverage writes, research admission,
Candidate writes, publication, deployment, and scheduler changes remain zero.
The sampled lifecycle field matrix therefore remains 244 / 512.

The next bounded task is to construct terminal cash-amount evidence for only
the 30 fixed-cash cases with matched cessation timing. That fact may later
mature an eligible label; it is not itself strategy performance.
