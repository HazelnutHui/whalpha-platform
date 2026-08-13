# Data Boundaries

## Confirmed Boundary

Analysis code should consume normalized internal interfaces rather than vendor response schemas.

The Market Data Provider boundary should cover:

- reference data
- bars/aggregates
- snapshots
- corporate actions
- options data
- portfolio/account data

Raw, normalized, and derived data must remain conceptually distinct.

## Proposed Providers

- Massive: proposed primary stock/ETF/market-structure backbone.
- IBKR: portfolio, positions, selected instruments, and selected options.
- Options provider: may be selected separately later.

Provider choice must remain replaceable.

## Data Authorization Boundary

The prototype is for personal use. Public accessibility does not automatically grant redistribution rights. Delayed/EOD or derived displays should be used until entitlements are confirmed.

Licensing must be reviewed before broader distribution or commercial use.

## Prohibited in Repository

Do not record API keys, subscription secrets, account credentials, or provider tokens in Git.
