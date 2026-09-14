# Strong-Leader Pullback Terminal Boundary Correction Audit — 2026-09-14

## Finding and authority

The first terminal-gap census reused `canonical_last_observed_date` from
Instrument Master history as if it were the final canonical EOD presence.
That field is an identity/provider-state observation date. ADR 0221 correctly
retains it as a source-priority diagnostic, but it cannot define a price-path
boundary.

ADRs 0253 and 0254 preserve the old artifacts for lineage and establish a
corrected, stable-ID EOD-boundary successor. This correction changes research
planning statistics only. It creates no legal last-trading date, execution
price, terminal outcome, strategy label, return, or admission authority.

## Formal evidence

The terminal-boundary report binds implementation revision
`d4119cf8f0ed9db8df8e419b7517400cf103600a` and formally validates all 287
Membership partitions plus 292 registered EOD sessions before materializing
requested stable-ID presence.

- Canonical report:
  `/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-boundary-census/census=20260914-v1/terminal-boundary-census.json`
- Report SHA-256:
  `a1fddf42680e65ad90250df2cb94b87058f02e0e157240c375551529606f9013`
- Logical fingerprint:
  `cb2aba6d936906d5e4a21f14fea2c9a6ff5337aee7ee3505c2c3977df909f0a7`

The V2 terminal-gap report binds implementation revision
`8ed286b8fc0aab6e0fa4d7d58299c3a386afdddb` and formally cross-reads the
boundary correction, immutable V1 report, original sample, lifecycle anchors,
payoff terms, and all existing reference layers.

- Canonical report:
  `/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2/census=20260914-v2/terminal-gap-census-v2.json`
- Report SHA-256:
  `1d920f4c44eb20bf312b667eb82a8944a9b63bfe0d3d7081a66e71c6f23e6cff`
- Logical fingerprint:
  `1cb6984652842e8898cebbb484f0796bfdd7b6e4e7bee167d88bf47734e06d5f`

Both reports formally reread successfully. Each canonical JSON has mode
`0400` beneath owner-owned mode-`0700` directories, with no symlink, partial,
or staging residue.

## Corrected result

Among 89 lifecycle rows, 75 have EOD presence ending before the final Identity
observation, 14 match it, and none end later. Fifty-five securities change at
least one registered horizon count.

| Boundary | 1-session paths / securities | 3-session paths / securities | 5-session paths / securities |
| --- | ---: | ---: | ---: |
| Historical Identity proxy | 10 / 10 | 135 / 63 | 252 / 64 |
| Corrected EOD presence | 63 / 63 | 186 / 64 | 302 / 65 |

The corrected five-session terminal worklist is:

| Evidence state | Securities | Documented paths | Remaining paths |
| --- | ---: | ---: | ---: |
| Existing reference evidence | 42 | 196 | 0 |
| Newly in-scope primary-source review | 1 | 0 | 1 |
| All other unresolved states | 22 | 0 | 105 |
| **Total** | **65** | **196** | **106** |

The addition is stable ID `ff8ae3f6-a3ae-5127-983b-0f94386f0055`, retained
with the `SCS` ticker locator, CIK `0001050825`, exchange `XNYS`, and share-
class FIGI `BBG001S89FD2`. Its strategy-window EOD presence ends on 2025-12-09,
the provider delisting candidate is 2025-12-11, and its single five-session
path is now explicitly in scope. These locators do not adjudicate its event or
terminal outcome.

The bounded next order is:

1. establish the new SCS primary-source chain;
2. adjudicate nine cessation-timing cases and three legacy exceptional cases;
3. address six CVRs, three holder-election/proration cases, and one unlisted-
   unit/election case under separate policies;
4. resolve missing-event neutrality and version the outcome-blind coverage
   census before any new admission decision.

## Verification and safety

Focused and linked correction suites passed before formal execution. The
complete API regression then passed 2,750 tests in 272.35 seconds. Its two
warnings are unchanged dependency deprecations in the authentication and
TestClient paths.

The correction used zero network requests and performed no `/data` write,
canonical lifecycle mutation, terminal-outcome calculation, Historical
Coverage admission, Candidate change, publication, deployment, or scheduler
mutation.
