import { useI18n } from '../i18n/I18nProvider';

type ChinaAshareView = 'research' | 'candidates';

const COPY = {
  en: {
    eyebrow: 'China A-shares · separately governed research market',
    title: 'A-share research foundation',
    candidateTitle: 'A-share model-driven selection',
    subtitle: 'A five-year daily-research foundation designed around A-share rules, point-in-time evidence, and executable—not merely theoretical—returns.',
    candidateSubtitle: 'The destination is reserved, but no ranking is allowed until an admitted A-share Universe and a validated model both exist.',
    status: 'Current admission state',
    statusValue: 'FOUNDATION · NOT ADMITTED',
    statusNote: 'No A-share backtest, Alpha, model, ranking, or strategy is active.',
    current: 'Current engineering gate',
    currentValue: 'Adjustment factors ↔ corporate actions',
    currentNote: 'Return semantics must pass before lifecycle, daily Universe, and the first outcome-blind factor campaign.',
    architectureTitle: 'The A-share path is similar in governance—not in market mechanics',
    architectureNote: 'U.S. data, calendars, rules, Universes, results, and activation authority are never reused implicitly.',
    architecture: [
      ['01', 'Market isolation', 'QUALIFIED', 'A separate namespace, calendar, rule book, fee schedule, evidence custody, and admission path.'],
      ['02', 'Pilot calendar & mechanics', 'QUALIFIED', 'Official SSE/SZSE dates, effective-dated rules, theoretical limits, statutory fees, and one account-cost scenario.'],
      ['03', 'Return semantics', 'IN PROGRESS', 'Reconcile provider adjustment factors against corporate actions; keep raw execution price, split-adjusted price, and total return separate.'],
      ['04', 'Lifecycle & daily Universe', 'LOCKED', 'Resolve listing, suspension, risk-warning, delisting, and one point-in-time eligibility decision per security/session.'],
      ['05', 'Factor → model → strategy', 'LOCKED', 'Only a passing 13-family admission can open finite outcome-blind factor discovery and later stock selection.'],
    ],
    candidateGateTitle: 'The A-share stock-pool destination is visible—but empty by design',
    candidateStats: [
      ['Admitted Universe', '0', 'No historical daily stock pool has passed admission'],
      ['Active rankings', '0', 'No U.S. candidate row is reused'],
      ['Validated models', '0', 'Factor discovery has not opened'],
      ['Pilot anchors', '6', 'Evidence coverage—not a tradable stock pool'],
    ],
    candidateBoundary: 'The page will eventually consume only an explicitly activated A-share strategy expression. Until then it is a transparent readiness surface, not a demonstration ranking.',
    evidenceTitle: 'What is real today',
    evidenceStats: [
      ['Pilot interval', '5 YEARS', '16 Sep 2021 → 16 Sep 2026'],
      ['Daily evidence', '7,255 BARS', 'Unadjusted execution-price observations'],
      ['Trading state', '7,266 DAYS', 'Includes 11 suspended sessions'],
      ['Official calendar', '1,211 SESSIONS', '12 annual notices · zero date differences'],
      ['Market mechanics', '7,266 DECISIONS', 'Zero observed-bar violations · zero unresolved rules'],
      ['Factor research', '0 CAMPAIGNS', 'Outcome access remains closed'],
    ],
    evidenceDetails: 'Inspect the evidence boundary',
    evidenceItems: [
      ['Market scope', 'Six pilot-only SSE/SZSE common-share bindings cover main board, STAR, ChiNext, suspension, risk-warning, and corporate-action scenarios. BSE remains quarantined.'],
      ['Adjustment observations', 'Twenty-eight provider factor changes are retained with all three source fields. Their direction, action coverage, revision behavior, and total-return meaning remain unproven.'],
      ['Official evidence', 'Calendar and market-mechanics source bytes are immutable, owner-only, hash-bound, and exactly reread. Internal paths and identifiers stay off the public interface.'],
      ['Account scenario', 'Ping An Securities via Tonghuashun uses a user-reported 0.01% commission per side, conservative CNY 5 minimum, and 5 bps slippage per side; statement confirmation remains pending.'],
    ],
    mechanicsTitle: 'A-share-specific execution layer',
    mechanicsNote: 'A signal can be statistically correct and still be untradeable. The execution layer therefore remains separate from factor and model scores.',
    mechanics: [
      ['T+1 inventory', 'A close-based signal can enter no earlier than the next eligible session; shares bought today cannot be assumed sellable the same day. Raw forward return and executable return will be separate labels.'],
      ['Price-limit state', 'Main-board, STAR, ChiNext, risk-warning, IPO no-limit, and future rule changes are effective-dated. The current pilot proves theoretical bounds, not queue priority or an exact fill.'],
      ['Locked-limit fills', 'One-price limit-up entries and limit-down exits must fail closed or move to a delayed-fill scenario. Daily bars cannot claim a queue position.'],
      ['Suspension and listing age', 'A missing bar is never automatically a suspension. Suspension, resumption, listing day, seasoning, risk-warning, and delisting state require independent evidence.'],
      ['Account and lot eligibility', 'Board permissions, minimum order size, odd-lot treatment, commission minimum, and cash/inventory timing belong to an account-aware execution ledger.'],
      ['Long-only reality', 'Short-leg spreads may diagnose a factor, but a user-facing strategy cannot assume universal stock borrow. The default expression is long, cash, or a separately governed hedge.'],
    ],
    researchTitle: 'Research mechanisms tailored to A-shares',
    research: [
      ['Market-state first', 'Breadth, limit-up/down climate, failed-limit frequency, turnover, dispersion, board/size leadership, and sector participation define applicability; volume is not relabeled as capital flow.'],
      ['Point-in-time stock pool', 'ST status, listing age, suspension, board, liquidity, and historical eligibility are evaluated on each session. Today’s survivors and classifications are never backfilled.'],
      ['Three return layers', 'Unadjusted prices simulate fills; split-adjusted series support comparability; cash distributions and actions create total return. The three layers cannot substitute for one another.'],
      ['A-share normalization', 'Raw and robust-ranked factors are retained; board, size, liquidity, industry, listing age, and market beta are controlled explicitly before claiming independent information.'],
      ['Horizon-specific tests', '2–5, 5–20, and 20–60-session hypotheses use separate labels, costs, embargoes, and stability tests rather than one universal holding period.'],
      ['Publication-time discipline', 'Earnings previews, express reports, lockup expiry, holdings changes, pledges, inquiries, restructurings, and resumptions enter only when their publication time was knowable.'],
    ],
    gateTitle: 'Admission ledger',
    passed: 'QUALIFIED FOR THE PILOT',
    passedItems: ['SSE/SZSE calendar', 'Effective-dated trading rules', 'Theoretical price-limit reconciliation', 'Statutory fee schedule', 'Cost-scenario registration'],
    blocked: 'STILL BLOCKED',
    blockedItems: ['Return-authorized adjustment semantics', 'Corporate-action economics', 'Listed-security lifecycle', 'Daily point-in-time Universe', 'Full-market and BSE route', 'Complete 13-family admission'],
    next: 'Next sequence',
    nextBody: 'Reconcile adjustments against corporate actions, close lifecycle evidence, generate one daily Universe decision per security/session, expand in bounded partitions, and publish the 13-family admission. Only a passing report may open the first A-share factor batch.',
    boundary: 'This is a research-readiness surface. It does not publish row-level A-share data and grants no backtest, model, candidate, Product, or trading authority.',
  },
  zh: {
    eyebrow: '中国 A 股 · 独立治理的研究市场',
    title: 'A 股量化研究基础',
    candidateTitle: 'A 股模型驱动筛选',
    subtitle: '围绕 A 股制度、点时证据和真实可成交收益建立的五年日频研究基础，而不是把美股模型换一个市场标签。',
    candidateSubtitle: '入口已经保留，但只有历史逐日股票池通过准入、且模型完成验证后，才允许出现正式排名。',
    status: '当前准入状态',
    statusValue: '基础建设中 · 尚未准入',
    statusNote: '当前没有 A 股回测、Alpha、模型、排名或策略。',
    current: '当前工程关口',
    currentValue: '复权因子 ↔ 公司行动',
    currentNote: '先证明收益语义，再处理生命周期、逐日股票池和首批结果盲因子研究。',
    architectureTitle: '治理标准相同，市场机制不能照搬',
    architectureNote: '美股的数据、日历、规则、股票池、研究结果和激活权限都不会被隐式复用。',
    architecture: [
      ['01', '市场隔离', '已通过', '独立命名空间、交易日历、交易规则、费用表、证据保管和准入路径。'],
      ['02', '试点日历与交易机制', '已通过', '沪深官方交易日、按生效日期管理的规则、理论涨跌停、法定费用及一个账户成本场景。'],
      ['03', '收益语义', '进行中', '用公司行动核对提供方复权因子；原始成交价、拆股复权价和总收益必须保持分离。'],
      ['04', '生命周期与逐日股票池', '未开放', '补齐上市、停复牌、风险警示、退市，并为每只证券每个交易日形成唯一点时适格决策。'],
      ['05', '因子 → 模型 → 策略', '未开放', '只有完整 13 类数据准入通过后，才开放有限、结果盲的因子发现和后续个股筛选。'],
    ],
    candidateGateTitle: 'A 股股票池入口已经可见，但目前有意保持为空',
    candidateStats: [
      ['已准入股票池', '0', '尚无历史逐日股票池通过正式准入'],
      ['有效排名', '0', '不会复用任何美股候选记录'],
      ['已验证模型', '0', 'A 股因子发现尚未开放'],
      ['试点证券', '6', '用于验证证据覆盖，不是可交易股票池'],
    ],
    candidateBoundary: '未来这里只接收经过明确激活的 A 股策略表达。在此之前，它是透明的准备状态页面，不会用示例分数伪装成真实排名。',
    evidenceTitle: '目前真正已经完成的部分',
    evidenceStats: [
      ['试点区间', '5 年', '2021-09-16 → 2026-09-16'],
      ['日频证据', '7,255 条', '未复权、用于真实成交语义的价格观察'],
      ['交易状态', '7,266 日', '明确包含 11 个停牌交易日'],
      ['官方交易日历', '1,211 日', '12 份年度公告 · 日期差异为零'],
      ['交易机制判定', '7,266 条', '观察价格违规为零 · 未解析规则为零'],
      ['因子研究', '0 批次', '结果读取仍然关闭'],
    ],
    evidenceDetails: '查看证据边界',
    evidenceItems: [
      ['市场范围', '六只沪深试点普通股覆盖主板、科创板、创业板、停牌、风险警示和公司行动场景；北交所仍处于隔离状态。'],
      ['复权观察', '保留 28 次提供方因子变化及三个原始字段，但方向、公司行动覆盖、修订行为和总收益含义尚未得到证明。'],
      ['官方证据', '日历和交易机制官方原文均不可变、仅所有者可读、绑定哈希并完成精确重读；内部路径和标识不在网站展示。'],
      ['账户成本', '平安证券经同花顺：用户提供双边各万分之一佣金，保守采用每笔最低 5 元并加入单边 5 bps 滑点；仍待交割单确认。'],
    ],
    mechanicsTitle: 'A 股特有的可成交性层',
    mechanicsNote: '统计信号正确并不等于可以买到或卖得掉，因此可成交性必须独立于因子分数和模型分数。',
    mechanics: [
      ['T+1 持仓约束', '收盘信号最早只能在下一可交易时点进入；当天买入不能假设当天卖出。原始远期收益与可实现收益将使用不同标签。'],
      ['涨跌停状态', '主板、科创板、创业板、风险警示、上市初期无涨跌幅和未来规则变化都按生效日期管理。目前只证明理论边界，不能证明排队顺序或成交。'],
      ['封板成交', '一字涨停买入和一字跌停退出必须关闭成交或进入延迟成交情景；仅凭日线不能声称拥有队列位置。'],
      ['停复牌与上市年龄', '缺少价格记录不自动等于停牌。停牌、复牌、上市日、成熟期、风险警示和退市必须有独立证据。'],
      ['账户权限与申报数量', '板块权限、最低申报数量、零股处理、最低佣金以及资金和持仓时序都进入账户级执行台账。'],
      ['多头现实约束', '多空组合可以用于诊断因子，但面向使用者的策略不能假设个股普遍可融券；默认表达是多头、现金或单独治理的对冲。'],
    ],
    researchTitle: '更适合 A 股的研究机制',
    research: [
      ['市场状态优先', '市场广度、涨跌停环境、炸板比例、换手、离散度、板块/规模强弱和行业参与度决定策略适用性；成交量不会被改名成资金流。'],
      ['点时股票池', 'ST 状态、上市年龄、停牌、板块、流动性和历史适格性逐日判断；不会把今天仍存续的股票和今天的分类倒推到过去。'],
      ['三层收益序列', '未复权价格用于模拟成交，拆股复权序列用于可比计算，现金分红和公司行动形成总收益；三者不能相互冒充。'],
      ['A 股横截面标准化', '同时保留原始值和稳健排名，并明确控制板块、规模、流动性、行业、上市年龄和市场 Beta 后再判断独立信息。'],
      ['按周期分别研究', '2–5、5–20、20–60 个交易日的假设分别注册标签、成本、隔离期和稳定性测试，不共用一个万能持有周期。'],
      ['公告时间纪律', '业绩预告、快报、限售解禁、股东变动、质押、问询、重组和复牌，只能从当时可知的公告时间进入研究。'],
    ],
    gateTitle: '准入台账',
    passed: '本试点已通过',
    passedItems: ['沪深交易日历', '按生效日期管理的交易规则', '理论涨跌停核对', '法定费用表', '账户成本场景登记'],
    blocked: '仍未通过',
    blockedItems: ['可用于收益的复权语义', '公司行动经济处理', '上市证券生命周期', '逐日点时股票池', '全市场扩展与北交所路径', '完整 13 类数据准入'],
    next: '下一步顺序',
    nextBody: '先用公司行动核对复权，再补齐上市证券生命周期，为每只证券每个交易日生成唯一股票池决策，分区扩展全市场，最后发布 13 类准入报告。只有正式通过后，才开放首批 A 股因子研究。',
    boundary: '这是研究准备状态页面，不发布 A 股逐行数据，也不授予回测、模型、候选排名、产品或交易权限。',
  },
  es: {
    eyebrow: 'Acciones A de China · mercado de investigación separado',
    title: 'Base de investigación de acciones A',
    candidateTitle: 'Selección de acciones A basada en modelos',
    subtitle: 'Una base diaria de cinco años diseñada para reglas de acciones A, evidencia point-in-time y rentabilidad ejecutable, no solo teórica.',
    candidateSubtitle: 'El destino está reservado, pero no puede mostrar rankings hasta que existan un Universo admitido y un modelo validado.',
    status: 'Estado de admisión', statusValue: 'BASE · NO ADMITIDA', statusNote: 'No hay backtest, Alpha, modelo, ranking ni estrategia activa.',
    current: 'Puerta de ingeniería actual', currentValue: 'Factores de ajuste ↔ acciones corporativas', currentNote: 'La semántica de rentabilidad debe aprobarse antes del ciclo de vida, Universo diario y primera campaña factorial.',
    architectureTitle: 'Mismo gobierno; mecánica de mercado distinta', architectureNote: 'Datos, calendarios, reglas, Universos, resultados y autoridad de EE. UU. nunca se reutilizan implícitamente.',
    architecture: [
      ['01', 'Aislamiento de mercado', 'APROBADO', 'Espacio, calendario, reglas, costes, custodia y admisión independientes.'],
      ['02', 'Calendario y mecánica piloto', 'APROBADO', 'Fechas SSE/SZSE, reglas temporales, límites teóricos, tasas y un escenario de cuenta.'],
      ['03', 'Semántica de rentabilidad', 'EN CURSO', 'Conciliar ajustes y acciones corporativas; separar precio bruto, precio ajustado y retorno total.'],
      ['04', 'Ciclo de vida y Universo diario', 'BLOQUEADO', 'Resolver cotización, suspensión, riesgo, exclusión y elegibilidad point-in-time.'],
      ['05', 'Factor → modelo → estrategia', 'BLOQUEADO', 'Solo la admisión de 13 familias puede abrir investigación factorial y selección.'],
    ],
    candidateGateTitle: 'El destino del Universo A es visible, pero permanece vacío por diseño',
    candidateStats: [['Universo admitido', '0', 'Ningún Universo histórico aprobado'], ['Rankings activos', '0', 'No se reutilizan candidatos de EE. UU.'], ['Modelos validados', '0', 'Descubrimiento factorial cerrado'], ['Anclas piloto', '6', 'Evidencia, no Universo negociable']],
    candidateBoundary: 'En el futuro solo consumirá una expresión de estrategia A activada explícitamente. Hoy es una vista de preparación, no un ranking de demostración.',
    evidenceTitle: 'Lo que existe hoy',
    evidenceStats: [['Intervalo', '5 AÑOS', '16 sep 2021 → 16 sep 2026'], ['Evidencia diaria', '7.255 BARRAS', 'Precios sin ajustar'], ['Estado', '7.266 DÍAS', 'Incluye 11 suspensiones'], ['Calendario', '1.211 SESIONES', '12 avisos · cero diferencias'], ['Mecánica', '7.266 DECISIONES', 'Cero infracciones · cero reglas pendientes'], ['Factores', '0 CAMPAÑAS', 'Resultados cerrados']],
    evidenceDetails: 'Examinar el límite de evidencia',
    evidenceItems: [['Ámbito', 'Seis valores piloto SSE/SZSE cubren mercados principal, STAR y ChiNext y escenarios de suspensión, riesgo y acciones corporativas; BSE sigue en cuarentena.'], ['Ajustes', 'Se conservan 28 cambios y tres campos del proveedor, pero aún no prueban dirección, cobertura, revisiones ni retorno total.'], ['Evidencia oficial', 'Calendario y reglas son inmutables, de acceso restringido, ligados a hashes y releídos exactamente.'], ['Cuenta', 'Ping An vía Tonghuashun: 0,01% por lado comunicado por el usuario, mínimo conservador CNY 5 y 5 pb de deslizamiento por lado; falta confirmación documental.']],
    mechanicsTitle: 'Capa de ejecución específica de acciones A', mechanicsNote: 'Una señal correcta puede no ser negociable; ejecución y puntuación permanecen separadas.',
    mechanics: [['Inventario T+1', 'Entrada no antes de la siguiente sesión apta; una compra no puede venderse el mismo día. Retorno bruto y ejecutable serán etiquetas separadas.'], ['Límites de precio', 'Segmento, riesgo, IPO y cambios de regla se versionan por fecha; el piloto prueba límites teóricos, no prioridad ni ejecución.'], ['Bloqueo de límite', 'Entradas bloqueadas al alza y salidas bloqueadas a la baja fallan o se retrasan; la barra diaria no prueba una cola.'], ['Suspensión y antigüedad', 'Una barra ausente no prueba suspensión. Reanudación, edad, riesgo y exclusión requieren evidencia independiente.'], ['Cuenta y lotes', 'Permisos, lotes, fracciones, comisión mínima y tiempos de efectivo/inventario entran en el libro de ejecución.'], ['Realidad long-only', 'El long-short sirve para diagnóstico, pero el producto no presume préstamo universal; usa largo, efectivo o cobertura separada.']],
    researchTitle: 'Mecanismos de investigación adaptados',
    research: [['Estado de mercado primero', 'Amplitud, límites, fallos de límite, rotación, dispersión, tamaño y sectores definen aplicabilidad; volumen no se llama flujo.'], ['Universo point-in-time', 'Riesgo, edad, suspensión, segmento, liquidez y elegibilidad se evalúan por sesión.'], ['Tres capas de retorno', 'Precio bruto para ejecución, ajustado para comparabilidad y retorno total para distribuciones; no son intercambiables.'], ['Normalización A-share', 'Se conservan valores brutos y rangos robustos y se controlan segmento, tamaño, liquidez, industria, edad y beta.'], ['Horizontes separados', '2–5, 5–20 y 20–60 sesiones registran etiquetas, costes y estabilidad distintos.'], ['Tiempo de publicación', 'Resultados preliminares, desbloqueos, participaciones, prendas, consultas, reestructuraciones y reanudaciones entran solo cuando eran conocibles.']],
    gateTitle: 'Libro de admisión', passed: 'APROBADO PARA EL PILOTO', passedItems: ['Calendario SSE/SZSE', 'Reglas temporales', 'Límites teóricos', 'Tasas legales', 'Escenario de costes'], blocked: 'AÚN BLOQUEADO', blockedItems: ['Ajustes aptos para retorno', 'Economía de acciones corporativas', 'Ciclo de vida', 'Universo diario', 'Mercado completo y BSE', 'Admisión de 13 familias'], next: 'Secuencia siguiente', nextBody: 'Conciliar ajustes y acciones, cerrar ciclo de vida, generar el Universo diario, ampliar por particiones y publicar la admisión. Solo entonces comienza la primera campaña factorial.', boundary: 'Vista de preparación: no publica filas A-share ni concede backtest, modelo, ranking, Producto o negociación.',
  },
} as const;

export function ChinaAshareResearchPage({ view }: { view: ChinaAshareView }): JSX.Element {
  const { locale } = useI18n();
  const c = COPY[locale];
  const candidateView = view === 'candidates';

  return <main className="research-page">
    <section className="research-hero">
      <div className="research-hero-copy"><span className="eyebrow">{c.eyebrow}</span><h1>{candidateView ? c.candidateTitle : c.title}</h1><p>{candidateView ? c.candidateSubtitle : c.subtitle}</p></div>
      <div className="research-status"><span>{c.status}</span><strong>{c.statusValue}</strong><p>{c.statusNote}</p></div>
      <div className="research-progress-copy"><strong>{c.current}</strong><span>{c.currentValue}</span><small>{c.currentNote}</small></div>
    </section>

    <section className="research-card research-architecture" aria-labelledby="ashare-architecture-title">
      <header><span>CN</span><div><p>{c.eyebrow}</p><h2 id="ashare-architecture-title">{c.architectureTitle}</h2><small>{c.architectureNote}</small></div></header>
      <div className="research-architecture-grid">
        {c.architecture.map(([index, title, state, body], itemIndex) => <article className={itemIndex < 2 ? 'active' : 'locked'} key={title}><div><span>{index}</span><b>{state}</b></div><h3>{title}</h3><p>{body}</p></article>)}
      </div>
    </section>

    {candidateView ? <section className="research-card research-factor-screening" aria-labelledby="ashare-candidate-gate-title">
      <header><span>0</span><div><h2 id="ashare-candidate-gate-title">{c.candidateGateTitle}</h2><p>{c.candidateBoundary}</p></div><b>{c.statusValue}</b></header>
      <div className="research-factor-stats">{c.candidateStats.map(([label, value, body]) => <article key={label}><span>{label}</span><strong>{value}</strong><small>{body}</small></article>)}</div>
      <p className="research-foundation-boundary">{c.candidateBoundary}</p>
    </section> : null}

    <section className="research-card research-foundation" aria-labelledby="ashare-evidence-title">
      <header><span>01</span><div><h2 id="ashare-evidence-title">{c.evidenceTitle}</h2><p>{c.statusNote}</p></div><b>{c.statusValue}</b></header>
      <div className="research-factor-stats">{c.evidenceStats.map(([label, value, body]) => <article key={label}><span>{label}</span><strong>{value}</strong><small>{body}</small></article>)}</div>
      <details className="research-factor-details" open><summary>{c.evidenceDetails}</summary><dl className="research-record-ledger">{c.evidenceItems.map(([label, body]) => <div key={label}><dt>{label}</dt><dd>{body}</dd></div>)}</dl></details>
    </section>

    <section className="research-card research-engineering-evidence" aria-labelledby="ashare-mechanics-title">
      <header><span>02</span><div><h2 id="ashare-mechanics-title">{c.mechanicsTitle}</h2><p>{c.mechanicsNote}</p></div><b>{c.architecture[2][2]}</b></header>
      <div className="research-screen-protocol">{c.mechanics.map(([title, body]) => <article key={title}><strong>{title}</strong><p>{body}</p></article>)}</div>
    </section>

    <section className="research-card research-engineering-evidence" aria-labelledby="ashare-research-title">
      <header><span>03</span><div><h2 id="ashare-research-title">{c.researchTitle}</h2><p>{c.architectureNote}</p></div><b>{c.architecture[4][2]}</b></header>
      <div className="research-screen-protocol">{c.research.map(([title, body]) => <article key={title}><strong>{title}</strong><p>{body}</p></article>)}</div>
    </section>

    <section className="research-card research-foundation" aria-labelledby="ashare-admission-title">
      <header><span>04</span><div><h2 id="ashare-admission-title">{c.gateTitle}</h2><p>{c.nextBody}</p></div><b>{c.statusValue}</b></header>
      <div className="research-screen-verdict">
        <article className="retained"><strong>{c.passed}</strong><ul>{c.passedItems.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article className="blocked"><strong>{c.blocked}</strong><ul>{c.blockedItems.map((item) => <li key={item}>{item}</li>)}</ul></article>
      </div>
      <div className="research-factor-limit"><strong>{c.next}</strong><p>{c.nextBody}</p></div>
      <p className="research-foundation-boundary">{c.boundary}</p>
    </section>
  </main>;
}
