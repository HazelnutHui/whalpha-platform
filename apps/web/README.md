# Trading Intelligence Web

The React application is no longer presented as five equal numbered modules.
Its persistent left rail has one `Research system` group led by Quant Research
Lab (`量化研究实验室`) as the default workspace, followed by Model-Driven
Equity Selection as its downstream consumer. A separate `Free market tools`
group contains Market Regime & Opportunities (`市场风向与机会`), Sector
Rotation, and Market Structure & Activity. Universe, language, and private
Session controls share an opaque sticky utility header. The Universe selector exposes only `Common
Shares` and `Common Shares + ADRs`, with CS-only as default. A validated stable
ID is persisted in the URL; Legacy remains an internal rollback boundary.

The public entry is research-first rather than a catalog of equally weighted
features. It presents Quant Research Lab as model/evidence authority,
model-driven Candidate ranking as a downstream activation, governed research
automation as a planned extension of traditional quantitative discipline, and
the three established market-context workspaces as free supporting tools. Its
current Strong-Leader Pullback record explicitly shows data construction,
unpublished out-of-sample evidence, and inactive Candidate authority before
any performance claim. The first viewport keeps account/password sign-in as
the primary entry, places equal-capability guest access immediately below it,
and uses a persistent continuation cue to expose the research narrative below.

Inside the Lab, a trilingual research-foundation snapshot shows the verified
five-year price/identity depth, reconstructed Membership, action assignments,
lifecycle references, and point-in-time fundamental pilot without combining
them into a misleading readiness score. An evidence ladder then separates the
frozen method, deterministic implementation, replayed reconstructed-population
diagnostics, formal performance-data admission, and result/Candidate
authority. The displayed 95.38% is explicitly method-computability coverage,
not a hit rate, prediction accuracy, or return.

The active Dashboard uses Activation V2 Primary/Secondary Universes. Provider
security form remains provisional and does not establish issuer structure or
domicile.

React/TypeScript/Vite frontend for Trading Intelligence Platform.

## Purpose

The frontend implements the five product workspaces and shared multilingual shell
for local/private development and versioned static publication. Quant Research
Lab is the model/evidence view; a future AI Quant Research Factory is its
backend capability and does not create another navigation item.

The authenticated and guest application uses a restrained institutional
research-workspace layer that is intentionally separate from the public
entry's marketing treatment. Navigation, utility controls, analytical panels,
tables, model records, drawers, and responsive states share flat surfaces,
compact geometry, restrained status color, and data-first typography. The
design avoids decorative imagery, glow-heavy cards, and motion as substitutes
for information hierarchy.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is the production static-dashboard target. It reads `/private-data/v1/manifest.json`, `market-summary.json`, `movers.json`, and `liquidity-map.json` from the authenticated static release. It does not call FastAPI and does not fall back to demo data. The deployed OCI release uses `/` as the public WH Alpha login entry, keeps `/login/` as a compatibility redirect, and protects Dashboard/private JSON with server-side session cookies; the frontend never stores usernames or passwords.


- `VITE_MARKET_DATA_MODE=api` is the default. It calls relative `/api/...` URLs through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo` is development-only, lazily loads clearly
  synthetic `TEST*` fixtures, and displays a persistent `DEMO DATA` badge.

API and Snapshot modes do not fall back to demo data on failure. Production
builds reject known synthetic fixture markers.

English remains the default interface language. Simplified Chinese is bundled
with the shared shell, while the complete neutral-Spanish catalog is loaded
only after an explicit Spanish selection or Spanish deep link. All three
locales preserve the same route, Universe, Session, data, and capability.

All five workspaces are route-level lazy chunks. The Quant Research Lab default
path no longer downloads the Candidate and ECharts-heavy Market Structure code
before it is needed. Hover/focus preloading reduces the first intentional
workspace switch, and production builds enforce raw-size ceilings of 350 KiB
for the entry JavaScript, 550 KiB for any asynchronous JavaScript chunk, and
130 KiB for the stylesheet.

Snapshot 1.11 / Dashboard 2.8 serves bounded Candidate summary/detail shards,
Entry Geometry, Strategy Channels, Candidate Visual Context, and Sector ETF
Rotation without browser-side score or rank recomputation. Exact active
sessions and release identity belong in
[current context](../../docs/project/current-context.md), not this application
guide.

## Implemented Views

- Research-first grouped workspace navigation and shared utility controls
- Factual first-screen market summary and Universe/comparable explanation
- Market Pulse
- Market Breadth
- Up/Down Volume
- Market Benchmark Strip for SPY, QQQ, IWM, DIA, and equal-weight universe return
- Sector Benchmark ETF 1D relative performance versus SPY
- Trading Activity Map treemap, default top 50
- Top Gainers and Top Losers
- Categorized Data Details
- Market Regime five-dimension evidence and six highlighted ETF relationships
- Complete 16-pair relationship table and detail drawer
- Language-neutral, risk-mode-specific Stock Candidate ranking, entry-location
  review, strategy channels, cross-channel decision desk, price-path/level
  context, contribution ledgers, and evidence drawer
- Trilingual Quant Research Lab foundation, readiness, and preregistered-method
  workspace;
  price depth has passed the length floor while the page keeps point-in-time
  membership, lifecycle, actions/adjustment, costs, and evaluation gates
  separately blocked and all real result areas locked
- Logout in snapshot mode
- loading, error, empty, and retry states

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

For local provider-backed verification, run the backend with private routes explicitly enabled:

```bash
TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true scripts/dev/run-api.sh
scripts/dev/run-web.sh
```

The private route enable flag is a development switch only, not authentication or deployment approval. The OCI static dashboard uses `snapshot` mode behind server-side session authentication.

## Tests

```bash
npm test
npm run build
```

## Current Non-Goals

- No real data on the public data-free landing page; guest and credential
  Sessions intentionally receive identical protected product capability
- No frontend access to credentials or password hashes
- No formal multi-user authentication or authorization
- No market-cap heatmap
- No sector/industry grouping
- No theme rotation
- No intraday or real-time data
- No real Quant Research Lab performance or research-stage activation
- No browser-side agent orchestration, model selection, or holdout access

The deployed Candidate score and technical Strategy Channels are frozen,
unvalidated Baseline V1. Future Stock Candidate rankings will come only from
separately validated and activated Quant Research Lab models; this frontend
guide does not authorize direct baseline tuning.

## Dashboard V1.1

The dashboard consumes the versioned overview payload. API mode calls `/api/v1/private/market/overview/latest`; snapshot mode reads `/private-data/v1/market-overview.json`; demo mode remains synthetic. The default universe is `Tradable U.S. Equities`, with ETFs shown separately as market and Sector Benchmark ETFs. Freshness compares the actual latest completed dataset session with the offline XNYS expected latest completed session and displays `Fresh`, an explicit session lag, or calendar unavailability separately from file validation.
