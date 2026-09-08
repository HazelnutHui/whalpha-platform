# Strategy Decision Integrity Deployment — 2026-09-08

## Outcome

The Strategy Channels decision-integrity presentation was implemented,
validated, published, and deployed. Published strategy status, score, rank,
parameters, thresholds, and analytics contracts were unchanged.

The browser now separates channel-local research priority from Candidate
trade-review readiness; exposes all-risk-mode rejection, gap/realized-
volatility review, no bounded setup, elevated extension, and explicit event
manual-check state; and counts displayed overlap only by stable
`instrument_id`. It does not infer sector membership, fund flow, channel
independence, expected return, option return, or a trade instruction.

## Validation

- Frontend: 117 tests passed; ordinary and isolated Snapshot-mode Production
  builds passed.
- API: 2,209 tests passed with the two existing dependency deprecation
  warnings.
- Candidate detail still fails closed on a missing or mismatched stable ID.
- English and Chinese assertions cover research/readiness separation, risk
  rejection, and stable-ID overlap semantics.

## Publication and deployment evidence

| Field | Verified value |
| --- | --- |
| Source commit | `ca2d34d506922f75699c376391dd6a9191ef0ae9` |
| Snapshot / OCI release | `2026-09-08T171914Z-ca2d34d50692` |
| Snapshot contracts | 1.11 / Dashboard 2.8 |
| Analysis session | 2026-09-04; ordinary fresh; lag zero |
| Market Intelligence | `2026-09-04T112916Z-717cb82c5369` |
| Snapshot plan SHA-256 | `d1d8373bdf050b5a71fac4ab569bbb98a3afb3631800b80f33d21996eb6cb68a` |
| Snapshot pointer fingerprint | `c1469a1dbde97fc5212b57d039e60b585be5ba0488ae4626c2e0d393fe387ea5` |
| Bundle logical fingerprint | `1bf4843b5988a43e125ac5cb48d68c779f0782070c869a7298345ca13396f8fe` |
| Bundle manifest SHA-256 | `d97ef555c19d1f3ec4c90ee7177be1935487c0f1519d02be61d625f97c40048f` |
| Bundle checksums SHA-256 | `837c5924572b9ac2206c7eab742d5542e28f5850cc1ec9238cb43709049f4d06` |
| Remote-state fingerprint | `98ba9f7126f019957e5502fabe591bc0781c0b2b9bd02b6ab90f2e230b5ae837` |

Remote preflight and independent postflight verified Nginx, the localhost-only
Auth Service, protected routes, a temporary guest Session, and identical guest
and credential route policy. There were zero staging releases, failed releases,
unexpected private listeners, or failed system units. Password-based login and
final human visual review remain manual checks.

The first source-bound Snapshot `2026-09-08T171250Z-8c3dc878d6ab` was not
bundled or deployed after the isolated build exposed an over-narrow test-fixture
type. The fixture type was corrected, retested, committed, and a new exact-
commit Snapshot was created. Both are immutable; the later release is active.

The final network-prohibited active-source report found 4,186 `/data` files /
2,143,226,489 bytes, inventory fingerprint
`3f4a5780a69a8d60688ce34b64f8df06fc0dd12070801f265b46f3f7a1f6ac49`,
zero symlinks, and zero publication residue. Research readiness remains
`data_blocked`; this deployment makes no performance claim.
