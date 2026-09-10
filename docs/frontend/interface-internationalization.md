# Frontend Interface Internationalization

## Status and scope

The React Dashboard and the static Session login surface support the same three
interface locales in local and production bundles:

- `en` renders HTML language `en` and is the authoritative default;
- `zh` renders HTML language `zh-CN` and provides professional Simplified
  Chinese copy; and
- `es` renders HTML language `es` and provides neutral professional Spanish
  copy.

This is presentation-only. Locale never enters analytics requests, source
payloads, calculation parameters, fingerprints, numeric formatting, dates,
session handling, authorization, or data freshness. The Market Dashboard and
Market Regime & Opportunities workspaces expose the same rows, fields, precision,
warnings, and interactions in all three languages. The user-facing workspace name
is `Market Regime & Opportunities` / `市场风向与机会` / `Régimen y oportunidades`;
the formal API and contract identifiers remain unchanged.

## Locale state contract

The deterministic resolution order is:

1. a legal URL value, `lang=en`, `lang=zh`, or `lang=es`;
2. the user's prior explicit choice in localStorage key
   `whalpha.interface.locale`;
3. English.

Browser language is deliberately ignored, so a first visit is English even
when `navigator.language` is Chinese. An illegal `lang` is treated as an
explicit invalid request, safely resolves to English, and is canonicalized to
`lang=en`. A missing `lang` is canonicalized to the resolved locale.

The global language selector uses text rather than flags, exposes pressed
state and a localized ARIA label, and writes both URL history and localStorage
only after an explicit user selection. It edits only `lang`; `view`,
`universe`, relationship window, filters, pair deep links, and any other query
parameters remain intact. `popstate`, refresh, and direct links reconstruct
the same language and page state.

The static entry page implements the same policy before Session checking. Its
safe Dashboard `next` value carries the selected locale for both credential and
guest entry. The guest path uses the same language choices and reaches the same
Dashboard payload; identity never selects a catalog or analytics response.

## Typed catalog architecture

The React catalog is centralized in `apps/web/src/i18n/catalog.ts`:

- the English object is the compile-time source of `MessageKey`;
- the Chinese and Spanish objects must satisfy `Record<MessageKey, string>`;
- tests compare all runtime key sets and reject empty values;
- `I18nProvider` owns URL/storage resolution and supplies the typed `t`
  function;
- `domain.ts` maps stable analytics identifiers, reason codes, states,
  dimensions, pair IDs, funnel stages, warnings, and other domain values to
  human-readable keys without altering the source identifiers.

The login asset is intentionally independent of the React bundle, but its
small English, Chinese, and Spanish dictionaries also have identical tested key
sets.
Neither surface uses machine translation, an external service, a CDN, or a
downloaded font. System-font fallbacks include `Noto Sans SC`, `PingFang SC`,
and `Microsoft YaHei`.

Raw tickers, pair IDs, universe IDs, schema/calculation versions,
fingerprints, reason codes, URL keys/values, formulas, exact audit Decimals,
and formal data content are never translated. The primary interface renders a
localized fixed-rule explanation; the audit expansion retains the raw reason
code beside it. Unknown values remain visible and fail conservatively rather
than being invented or hidden.

## Terminology baseline

| English | Simplified Chinese | Spanish |
|---|---|---|
| Market Structure & Activity | 市场结构与活跃度 | Estructura y actividad del mercado |
| Market Regime & Opportunities | 市场风向与机会 | Régimen y oportunidades |
| Risk-on / Balanced / Defensive / Stress | 风险偏好 / 均衡 / 防御 / 压力 | Risk-on / Equilibrado / Defensivo / Tensión |
| Candidate / Confirmed | 候选状态 / 确认状态 | Candidato / Confirmado |
| Composite | 综合评分 | Compuesto |
| Trend | 趋势 | Tendencia |
| Market Breadth | 市场广度 | Amplitud del mercado |
| Volatility | 波动环境 | Volatilidad |
| Liquidity / Participation | 流动性 / 参与度 | Liquidez / Participación |
| Leadership / Dispersion | 领涨结构 / 离散度 | Liderazgo / Dispersión |
| Support / Neutral / Drag | 支持 / 中性 / 拖累 | Apoyo / Neutral / Lastre |
| Relative Strength / Relative Spread | 相对强弱 / 相对收益差 | Fortaleza relativa / Diferencial relativo |
| Correlation / Correlation Change | 相关系数 / 相关性变化 | Correlación / Cambio de correlación |
| Supporting Evidence / Counterevidence | 支持证据 / 反面证据 | Evidencia favorable / Evidencia contraria |
| Reliability | 可靠度 | Fiabilidad |
| Common Shares | 普通股 | Acciones ordinarias |
| Common Shares + ADRs | 普通股 + 美国存托凭证 | Acciones ordinarias + ADR |

Safety language remains equally prominent in all three languages: research context
is not a trade recommendation, statistical relationships are not causation,
price relationships are not fund flow, and reliability is not forecast
probability.

## Adding another locale

1. Add the locale and HTML-language mapping without changing existing URL
   values.
2. Supply every existing `MessageKey`; do not fall back silently to English.
3. Extend stable domain mappings only when a new language requires copy, never
   by changing analytics identifiers.
4. Add login copy with the identical login key set.
5. Extend precedence, history, deep-link, key-parity, reason-code, data-
   invariance, authentication, layout, and screenshot tests.
6. Review terminology and full sentences with an investment-research lens.

Guest access reuses this exact locale state and catalog. Credential and guest
Sessions must not change analytics content, fields, precision, timeliness,
functionality, or language availability.

## Publication boundary

The trilingual implementation uses one language-neutral Market Intelligence
payload for all three locales, and locale remains excluded from analytics identity.
Guest and credential Sessions consume that same payload. No role-dependent
content is authorized.
