# Strong-Leader Pullback Terminal Reference Bounds Review

## Decision

The first outcome-blind bounds review is `source_evidence_pending`. It reduces
the unbounded terminal population from 88 to 25 five-session crossing paths
without reading an outcome or selecting a parameter.

| Boundary | Result |
| --- | ---: |
| Terminal crossing paths | 302 |
| Prior exact-reference paths | 214 |
| Supplemental exact-reference paths | 0 |
| Finite interval-reference paths | 63 |
| Still-unbounded paths | 25 |
| Residual cases reviewed | 18 |
| Remaining source-pending cases | 5 |

Bounds report logical fingerprint:
`7975716fffe346a432c2a184bbef35cf47e306868ac33e66356edbe652cc5e6f`.

## Ready intervals

Every interval below is gross USD reference value per target common share. The
lower endpoint is zero. The upper endpoint is an adverse sensitivity cap, not
a realized payoff or expected value.

| Locator | Stable `instrument_id` | Paths | Policy | Upper USD |
| --- | --- | ---: | --- | ---: |
| ACLX | `c6c4a32a-49a4-51db-ad16-bfd6d7e58ea0` | 5 | cash + CVR cap | 120.0000000000 |
| AKRO | `39b319b3-e240-5d5f-9fef-1abfa12afa48` | 5 | cash + CVR cap | 60.0000000000 |
| AMED | `98f50e3f-4ec1-5236-83f3-fd4fe009350d` | 5 | fixed cash | 101.0000000000 |
| APLS | `5594a37d-0a8f-528b-a40a-310305d07808` | 5 | cash + CVR cap | 45.0000000000 |
| BLD | `57d24075-0478-5e91-8e22-fceda7700ac1` | 5 | max of cash / listed shares | 505.0000000000 |
| ETNB | `37cc3174-100b-51c0-82e8-cd055d1213b8` | 5 | cash + CVR cap | 20.5000000000 |
| GTLS | `d90fa658-61a6-55b1-ac2a-5bd977a0ea0d` | 5 | fixed cash | 210.0000000000 |
| HOLX | `8164e4a6-705b-5d0f-a93c-4836e08e9278` | 5 | cash + CVR cap | 79.0000000000 |
| SLNO | `beb7b379-364b-5917-ada1-110fb2c19f67` | 5 | fixed cash | 53.0000000000 |
| SNV | `8f99481e-e0e1-5f43-9d0a-dfe0176a3814` | 5 | listed shares | 49.8038700000 |
| THR | `650a846c-bc83-5c8a-adc2-cd05a87abc11` | 5 | max of three elections | 64.0933300000 |
| TMHC | `62620f34-d002-5b43-a731-70f6679ea04e` | 5 | fixed cash | 72.5000000000 |
| VERV | `72108e8d-6854-5266-a8ad-68b83ebceb5a` | 3 | cash + CVR cap | 13.5000000000 |

The listed calculations use canonical closes at the registered daily reference
boundary: QXO 16.54, CECO 79.03, and PNFP 95.10. BLD's contractual cash
alternative exceeds 20.2 QXO shares; THR's 0.811 CECO-share alternative is the
largest of its three gross alternatives; SNV uses 0.5237 PNFP shares. The
canonical content fingerprints and retained payoff/source fingerprints are
bound in the report input; no ticker-only identity assignment was made.

## Five-source official completion plan

The remaining 25 paths need only five official documents. These are exact
source targets, not a general new-provider integration.

| Locator | Missing role | Free official source target | Expected bound if validated |
| --- | --- | --- | --- |
| LNW | foreign continuation and U.S. exit timetable | SEC exhibit `0000950157-25-000856`, `ex99-1.htm` | exact last U.S. close 86.22 under the U.S.-venue exit policy |
| MTSR | final aggregate CVR cap | SEC filing `0001193125-25-273435`, `d94128ddefa14a.htm` | zero to 86.25 |
| REVG | final cash and listed-share terms | SEC exhibit `0001140361-26-003269`, `ef20064508_ex99-1.htm` | zero to cash plus 0.9809 TEX at the frozen boundary |
| SAND | final listed-share ratio | SEC exhibit `0001279569-25-001118`, `ex991.htm` | zero to 0.0625 RGLD at the frozen boundary |
| SKX | official private-unit acquisition value | parent SEC Form 10-K `0001193125-26-126281`, `ck0002066659-20251231.htm` | zero to the greater contractual alternative using the source-stated unit value |

Availability was located without selecting a commercial vendor. None of these
documents is treated as retained evidence by this review.

The exact zero-request plan was subsequently published in private Dell custody
as `plan=20260915-v1`, bound to implementation revision
`ebf58010651642e6cf1221be03c2a5258864e4ff` and the formally reread 2026-09-10
SEC Submissions archive. Plan report SHA-256:
`68e47bdb57f94edcb9143baa659d26174092502cb12573e3355dd1c363f8e3a1`;
logical fingerprint:
`385178ea480fc5813719a2fa924ba0a5abfd1efe046d37fbf6f28bc5c593c410`.
An independent plan reread matched with zero external requests, credential
reads, and document writes.

Acquisition remains subject to the project's separate live-SEC authorization
and private User-Agent rule; a downloaded response must match the frozen
locator, validate as SEC content, be hashed and retained, and then pass field
adjudication. The source custody directory exists but contains no source
package or downloaded document.

Alpha Vantage Listing Status, OpenFIGI, issuer pages, and exchange notices keep
narrow corroboration roles. They cannot replace transaction terms or a private
unit value. FINRA remains relevant only where an OTC state is actually in
question. No adapter is built unless it can change a named gate.

## Gate result and authority

Research Admission V2 remains `blocked` solely on
`finite_terminal_reference_intervals`. After binding this partial bounds report,
its decision fingerprint is
`a3d7d94cffb8564208217f06fe035ac0c6c9f2fbcec7382a9c4cfebd916d720d`.

No return label, outcome, performance metric, parameter selection, validation,
holdout access, Candidate activation, network acquisition, credential access,
canonical write, `/data` mutation, publication, deployment, or scheduler
change occurred.
