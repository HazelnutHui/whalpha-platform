# China A-share Corporate-action Reconciliation — 2026-09-17

## Scope

This audit closes only the corporate-action/adjustment-economic gate for the
six-security SSE/SZSE daily pilot covering 2021-09-16 through 2026-09-16. It
does not create canonical identities, a historical Universe, a full-market
database, research admission, Product data, or deployment authority.

## Evidence and method

- retained 12 exact CNINFO distribution and rights-query responses, including
  six valid empty rights responses;
- normalized 27 implemented distribution events with stable pilot bindings;
- retained 123 BaoStock adjustment observations from 1990 through the pilot
  end so every in-window event has predecessor-factor evidence;
- independently matched all 27 dates, record dates, and economic terms through
  Tonghuashun observations exposed by AKShare;
- computed the exchange action reference formula from the previous actual
  close and effective cash/share terms, while retaining exchange pre-close
  rounding separately; and
- compared the expected close/reference-price step with both cumulative
  BaoStock factor directions under a fixed 0.000005 relative tolerance.

## Result

| Decision | Count |
| --- | ---: |
| Matched implemented action | 27 |
| Provider correction/no-op | 1 |
| Left-boundary action | 0 |
| Action without adjustment | 0 |
| Adjustment without action | 0 |
| Factor conflict | 0 |

The sole non-action row is `sh.600519` on 2023-07-03. Its cumulative fore/back
factors are unchanged from the preceding observation; it is retained as a
provider-field correction rather than fabricated as a second economic event.

## Custody and verification

- package logical fingerprint:
  `6ec16837c7ec8e96f69ae7979143e0bbe6040ab33f89ec9eaa95c0fc66c38693`;
- report logical fingerprint:
  `5567b7ea20174b5f9779a022b21bf256fcf5712e2a04ae2883d24e8b9ea9e586`;
- manifest physical SHA-256:
  `80a6f658d9f5318f43103b913b33972a4fa23a1306fbc58fe857cca862122694`;
- 17 files, 164,389 bytes, owner-only modes, zero symlinks, closed file set;
- independent exact reread passed; and
- 59 focused A-share regression tests and all 3,139 backend tests passed.

The package is temporary owner-only evidence below `/tmp`. Every canonical,
research, Product, and deployment authority flag remains false. The next gate
is stable listed-security identity and lifecycle evidence.
