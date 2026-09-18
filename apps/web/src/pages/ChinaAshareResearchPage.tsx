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
    currentValue: 'Official warning-document adjudication',
    currentNote: 'The 109-partition conservative reconstruction replays exactly. All 492 warning-search units are complete, but search locators are not event facts; official document bytes and effective intervals are the next gate.',
    architectureTitle: 'The A-share path is similar in governance—not in market mechanics',
    architectureNote: 'U.S. data, calendars, rules, Universes, results, and activation authority are never reused implicitly.',
    architecture: [
      ['01', 'Market isolation', 'QUALIFIED', 'A separate namespace, calendar, rule book, fee schedule, evidence custody, and admission path.'],
      ['02', 'Pilot calendar & mechanics', 'QUALIFIED', 'Official SSE/SZSE dates, effective-dated rules, theoretical limits, statutory fees, and one account-cost scenario.'],
      ['03', 'Full-population diagnostic', 'REPLAYED', '5,409 governed targets and 5,997,301 daily states were rebuilt independently with identical bytes and hashes.'],
      ['04', 'Evidence-family admission', 'IN PROGRESS', 'Resolve listing, suspension, risk-warning, actions, price-limit rules, and one point-in-time eligibility decision per security/session.'],
      ['05', 'Factor → model → strategy', 'LOCKED', 'Only a passing 13-family admission can open finite outcome-blind factor discovery and later stock selection.'],
    ],
    candidateGateTitle: 'The A-share stock-pool destination is visible—but empty by design',
    candidateStats: [
      ['Admitted Universe', '0', 'No historical daily stock pool has passed admission'],
      ['Active rankings', '0', 'No U.S. candidate row is reused'],
      ['Validated models', '0', 'Factor discovery has not opened'],
      ['Governed targets', '5,409', '5,296 resolved identities · 113 quarantined'],
    ],
    candidateBoundary: 'The page will eventually consume only an explicitly activated A-share strategy expression. Until then it is a transparent readiness surface, not a demonstration ranking.',
    evidenceTitle: 'What is real today',
    evidenceStats: [
      ['Research interval', '5 YEARS', '1,211 governed trading sessions'],
      ['Daily evidence', '5,987,288 BARS', 'Unadjusted execution-price observations'],
      ['Trading state', '5,997,301 STATES', '109 bounded source/normalized partitions'],
      ['Identity scope', '5,409 TARGETS', '5,296 resolved · 113 quarantined'],
      ['Provisional states', '5,059,363', '157,377 excluded · 780,561 quarantined'],
      ['Warning search', '492 / 492', '4,399 locators · 2,454 publication clocks · 0 adjudicated events'],
      ['Factor research', '0 CAMPAIGNS', 'Outcome access remains closed'],
    ],
    evidenceDetails: 'Inspect the evidence boundary',
    evidenceItems: [
      ['Market scope', 'The frozen SSE/SZSE acquisition population contains 5,409 governed targets across 109 partitions. It is not a complete-China-market claim; BSE remains outside the qualified route.'],
      ['Deterministic replay', 'The diagnostic was rebuilt from the exact readers rather than copied. Plan, partition aggregates, streaming aggregate, and manifest are byte- and hash-identical.'],
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
    passedItems: ['SSE/SZSE calendar', 'Effective-dated pilot rules', '109-partition exact reconstruction', 'Conservative Universe replay', '492 / 492 warning searches'],
    blocked: 'STILL BLOCKED',
    blockedItems: ['Return-authorized adjustment semantics', 'Corporate-action economics', 'Dynamic listed-security lifecycle', 'Daily point-in-time Universe', 'Warning and price-limit evidence', 'Complete 13-family admission'],
    next: 'Next sequence',
    nextBody: 'Fetch and hash the official warning documents, then adjudicate event type, subtype, stable-security binding, and effective intervals. Lifecycle, listing-stage, actions, returns, and the first factor batch remain behind later gates.',
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
    currentValue: '官方风险警示文件裁决',
    currentNote: '109分区保守重建已精确重放，492 / 492个风险警示检索单元全部完成；但检索线索不等于事件事实，下一道门是官方文件原文与生效区间裁决。',
    architectureTitle: '治理标准相同，市场机制不能照搬',
    architectureNote: '美股的数据、日历、规则、股票池、研究结果和激活权限都不会被隐式复用。',
    architecture: [
      ['01', '市场隔离', '已通过', '独立命名空间、交易日历、交易规则、费用表、证据保管和准入路径。'],
      ['02', '试点日历与交易机制', '已通过', '沪深官方交易日、按生效日期管理的规则、理论涨跌停、法定费用及一个账户成本场景。'],
      ['03', '全量诊断', '重放通过', '5,409个治理目标与5,997,301个逐日状态已独立重建，字节和物理哈希完全一致。'],
      ['04', '证据家族准入', '进行中', '收敛上市、停复牌、风险警示、公司行动、涨跌停规则与逐日点时适格决策。'],
      ['05', '因子 → 模型 → 策略', '未开放', '只有完整 13 类数据准入通过后，才开放有限、结果盲的因子发现和后续个股筛选。'],
    ],
    candidateGateTitle: 'A 股股票池入口已经可见，但目前有意保持为空',
    candidateStats: [
      ['已准入股票池', '0', '尚无历史逐日股票池通过正式准入'],
      ['有效排名', '0', '不会复用任何美股候选记录'],
      ['已验证模型', '0', 'A 股因子发现尚未开放'],
      ['治理目标', '5,409', '5,296个身份已解析 · 113个仍隔离'],
    ],
    candidateBoundary: '未来这里只接收经过明确激活的 A 股策略表达。在此之前，它是透明的准备状态页面，不会用示例分数伪装成真实排名。',
    evidenceTitle: '目前真正已经完成的部分',
    evidenceStats: [
      ['研究区间', '5 年', '1,211个受治理交易日'],
      ['日频证据', '5,987,288 条', '未复权、用于真实成交语义的价格观察'],
      ['交易状态', '5,997,301 条', '109个有界原始与标准化分区'],
      ['身份范围', '5,409 个', '5,296个已解析 · 113个隔离'],
      ['重建候选状态', '5,059,363 条', '排除157,377条 · 隔离780,561条'],
      ['风险警示检索', '492 / 492', '4,399条定位线索 · 2,454个发布时间 · 0项已裁决事件'],
      ['因子研究', '0 批次', '结果读取仍然关闭'],
    ],
    evidenceDetails: '查看证据边界',
    evidenceItems: [
      ['市场范围', '冻结的沪深采集总体包含109个分区、5,409个治理目标；这不等于完整中国市场，北交所仍不在合格路径内。'],
      ['确定性重放', '诊断包由全部精确 reader 独立重建而非复制；计划、分区汇总、流式汇总与清单的字节和哈希全部一致。'],
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
    passedItems: ['沪深交易日历', '试点按生效日期管理的规则', '109分区精确重建', '保守股票池重放', '492 / 492风险警示检索'],
    blocked: '仍未通过',
    blockedItems: ['可用于收益的复权语义', '公司行动经济处理', '动态上市证券生命周期', '逐日点时股票池', '风险警示与涨跌停证据', '完整 13 类数据准入'],
    next: '下一步顺序',
    nextBody: '先获取并哈希风险警示官方文件，再裁决事件类型、子类型、稳定证券绑定和生效区间。生命周期、上市阶段、公司行动、收益以及首批因子研究继续位于后续门禁之后。',
    boundary: '这是研究准备状态页面，不发布 A 股逐行数据，也不授予回测、模型、候选排名、产品或交易权限。',
  },
  es: {
    eyebrow: 'Acciones A de China · mercado de investigación separado',
    title: 'Base de investigación de acciones A',
    candidateTitle: 'Selección de acciones A basada en modelos',
    subtitle: 'Una base diaria de cinco años diseñada para reglas de acciones A, evidencia point-in-time y rentabilidad ejecutable, no solo teórica.',
    candidateSubtitle: 'El destino está reservado, pero no puede mostrar rankings hasta que existan un Universo admitido y un modelo validado.',
    status: 'Estado de admisión', statusValue: 'BASE · NO ADMITIDA', statusNote: 'No hay backtest, Alpha, modelo, ranking ni estrategia activa.',
    current: 'Puerta de ingeniería actual', currentValue: 'Adjudicación documental de alertas', currentNote: 'La reconstrucción conservadora de 109 particiones se reprodujo exactamente y las 492 búsquedas terminaron. Los localizadores no son hechos: faltan documentos oficiales e intervalos efectivos.',
    architectureTitle: 'Mismo gobierno; mecánica de mercado distinta', architectureNote: 'Datos, calendarios, reglas, Universos, resultados y autoridad de EE. UU. nunca se reutilizan implícitamente.',
    architecture: [
      ['01', 'Aislamiento de mercado', 'APROBADO', 'Espacio, calendario, reglas, costes, custodia y admisión independientes.'],
      ['02', 'Calendario y mecánica piloto', 'APROBADO', 'Fechas SSE/SZSE, reglas temporales, límites teóricos, tasas y un escenario de cuenta.'],
      ['03', 'Diagnóstico completo', 'REPRODUCIDO', '5.409 objetivos y 5.997.301 estados diarios fueron reconstruidos con bytes y hashes idénticos.'],
      ['04', 'Admisión por familia', 'EN CURSO', 'Resolver cotización, suspensión, alertas, acciones, límites y elegibilidad point-in-time.'],
      ['05', 'Factor → modelo → estrategia', 'BLOQUEADO', 'Solo la admisión de 13 familias puede abrir investigación factorial y selección.'],
    ],
    candidateGateTitle: 'El destino del Universo A es visible, pero permanece vacío por diseño',
    candidateStats: [['Universo admitido', '0', 'Ningún Universo histórico aprobado'], ['Rankings activos', '0', 'No se reutilizan candidatos de EE. UU.'], ['Modelos validados', '0', 'Descubrimiento factorial cerrado'], ['Objetivos gobernados', '5.409', '5.296 resueltos · 113 en cuarentena']],
    candidateBoundary: 'En el futuro solo consumirá una expresión de estrategia A activada explícitamente. Hoy es una vista de preparación, no un ranking de demostración.',
    evidenceTitle: 'Lo que existe hoy',
    evidenceStats: [['Intervalo', '5 AÑOS', '1.211 sesiones gobernadas'], ['Evidencia diaria', '5.987.288 BARRAS', 'Precios sin ajustar'], ['Estado', '5.997.301 FILAS', '109 particiones acotadas'], ['Identidad', '5.409 OBJETIVOS', '5.296 resueltos · 113 aislados'], ['Estados provisionales', '5.059.363', '157.377 excluidos · 780.561 aislados'], ['Búsqueda de alertas', '492 / 492', '4.399 localizadores · 2.454 horas de publicación · 0 eventos adjudicados'], ['Factores', '0 CAMPAÑAS', 'Resultados cerrados']],
    evidenceDetails: 'Examinar el límite de evidencia',
    evidenceItems: [['Ámbito', 'La población congelada SSE/SZSE contiene 5.409 objetivos en 109 particiones; no constituye todo el mercado chino y BSE queda fuera.'], ['Reproducción', 'El diagnóstico se reconstruyó desde lectores exactos, no por copia; plan, agregados, resumen y manifiesto coinciden en bytes y hashes.'], ['Evidencia oficial', 'Calendario y reglas son inmutables, de acceso restringido, ligados a hashes y releídos exactamente.'], ['Cuenta', 'Ping An vía Tonghuashun: 0,01% por lado comunicado por el usuario, mínimo conservador CNY 5 y 5 pb de deslizamiento por lado; falta confirmación documental.']],
    mechanicsTitle: 'Capa de ejecución específica de acciones A', mechanicsNote: 'Una señal correcta puede no ser negociable; ejecución y puntuación permanecen separadas.',
    mechanics: [['Inventario T+1', 'Entrada no antes de la siguiente sesión apta; una compra no puede venderse el mismo día. Retorno bruto y ejecutable serán etiquetas separadas.'], ['Límites de precio', 'Segmento, riesgo, IPO y cambios de regla se versionan por fecha; el piloto prueba límites teóricos, no prioridad ni ejecución.'], ['Bloqueo de límite', 'Entradas bloqueadas al alza y salidas bloqueadas a la baja fallan o se retrasan; la barra diaria no prueba una cola.'], ['Suspensión y antigüedad', 'Una barra ausente no prueba suspensión. Reanudación, edad, riesgo y exclusión requieren evidencia independiente.'], ['Cuenta y lotes', 'Permisos, lotes, fracciones, comisión mínima y tiempos de efectivo/inventario entran en el libro de ejecución.'], ['Realidad long-only', 'El long-short sirve para diagnóstico, pero el producto no presume préstamo universal; usa largo, efectivo o cobertura separada.']],
    researchTitle: 'Mecanismos de investigación adaptados',
    research: [['Estado de mercado primero', 'Amplitud, límites, fallos de límite, rotación, dispersión, tamaño y sectores definen aplicabilidad; volumen no se llama flujo.'], ['Universo point-in-time', 'Riesgo, edad, suspensión, segmento, liquidez y elegibilidad se evalúan por sesión.'], ['Tres capas de retorno', 'Precio bruto para ejecución, ajustado para comparabilidad y retorno total para distribuciones; no son intercambiables.'], ['Normalización A-share', 'Se conservan valores brutos y rangos robustos y se controlan segmento, tamaño, liquidez, industria, edad y beta.'], ['Horizontes separados', '2–5, 5–20 y 20–60 sesiones registran etiquetas, costes y estabilidad distintos.'], ['Tiempo de publicación', 'Resultados preliminares, desbloqueos, participaciones, prendas, consultas, reestructuraciones y reanudaciones entran solo cuando eran conocibles.']],
    gateTitle: 'Libro de admisión', passed: 'EVIDENCIA VERIFICADA', passedItems: ['Calendario SSE/SZSE', 'Reglas piloto con vigencia temporal', 'Reconstrucción exacta de 109 particiones', 'Reproducción del Universo conservador', '492 / 492 búsquedas de alertas'], blocked: 'AÚN BLOQUEADO', blockedItems: ['Ajustes aptos para retorno', 'Economía de acciones corporativas', 'Ciclo de vida dinámico', 'Universo diario', 'Alertas y límites de precio', 'Admisión de 13 familias'], next: 'Secuencia siguiente', nextBody: 'Obtener y verificar los documentos oficiales de alerta y adjudicar tipo, subtipo, vínculo estable e intervalos efectivos. Ciclo de vida, cotización, acciones, retornos y la primera campaña factorial siguen tras puertas posteriores.', boundary: 'Vista de preparación: no publica filas A-share ni concede backtest, modelo, ranking, Producto o negociación.',
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
