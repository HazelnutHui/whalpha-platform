import modelRecord from '../modelRecords/quant-research-lab-model-record-v1.json';
import factorQualification from '../modelRecords/quant-research-factor-qualification-v2.json';
import factorScreeningV2 from '../modelRecords/quant-research-factor-screening-v2.json';
import factorScreening from '../modelRecords/quant-research-factor-screening-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const ARCHITECTURE_COPY = {
  en: {
    eyebrow: 'Current research architecture · ADR 0274',
    title: 'From measurement to a decision—without collapsing the evidence.',
    note: 'The research universe can expand over time. Every batch that reads outcomes remains finite, registered, and fully counted.',
    layers: [
      ['01', 'Factor Discovery', 'CURRENT · V2 SCREEN IMPLEMENTATION', 'Catalog V2 passed outcome-blind qualification. Six Development trials are now frozen and the cumulative ledger counts all 14 trials; no V2 outcome has been read. The next boundary is exact implementation, one report, and one replay.'],
      ['02', 'Model Construction', 'LOCKED', 'Combine a small admitted factor set into an explainable rank, probability, distribution, or risk state. No model is preselected.'],
      ['03', 'Strategy Expression', 'LOCKED', 'Translate a locked model into entry, exit, holding, sizing, cost, capacity, and risk rules. Stock and option expressions remain separate.'],
    ],
    boundary: 'A factor is not a model. A model is not a strategy. A backtest is not Product authority.',
    prior: 'First-program outcome',
    priorBody: 'Strong-Leader Pullback is closed: V1 was inconclusive and its only registered replacement was rejected on endpoint instability. No parameter was locked; Validation and Holdout were not opened.',
  },
  zh: {
    eyebrow: '当前研究架构 · ADR 0274',
    title: '从测量到决策，每一层证据都保持独立。',
    note: '长期研究方向可以持续扩展；但每一批读取结果的实验都必须有限、预先登记并计入真实试验次数。',
    layers: [
      ['01', '因子发现层', '当前阶段 · V2 筛选实现', '因子目录 V2 已通过不读取结果的资格诊断。6项开发期试验已经冻结，累计账本完整记录14项试验；V2 尚未读取任何结果。下一道边界是精确实现、一次报告和一次重放。'],
      ['02', '模型构建层', '保持锁定', '用少量合格且非冗余的因子构建可解释排名、概率、分布或风险状态。目前没有预先指定模型。'],
      ['03', '策略表达层', '保持锁定', '把锁定模型转为入场、退出、持有、仓位、成本、容量与风险规则；股票和期权表达分开验证。'],
    ],
    boundary: '因子不是模型，模型不是策略，回测也不等于产品权限。',
    prior: '首个研究项目结论',
    priorBody: '强势股回撤已关闭：V1 证据不足，唯一一次登记替代因终端估值情景下的优选参数不稳定而被拒绝。没有锁定参数，也没有打开验证集或留出集。',
  },
  es: {
    eyebrow: 'Arquitectura de investigación actual · ADR 0274',
    title: 'De la medición a la decisión, sin mezclar las capas de evidencia.',
    note: 'El universo de investigación puede ampliarse con el tiempo. Cada campaña que consulta resultados sigue siendo finita, registrada y contabilizada.',
    layers: [
      ['01', 'Descubrimiento de factores', 'FASE ACTUAL · IMPLEMENTACIÓN DEL FILTRO V2', 'El Catálogo V2 superó la calificación sin resultados. Ya están congeladas seis pruebas de Desarrollo y el registro acumulativo contabiliza las 14 pruebas; no se ha consultado ningún resultado V2. El siguiente límite es la implementación exacta, un informe y una reproducción.'],
      ['02', 'Construcción del modelo', 'BLOQUEADA', 'Combina un pequeño conjunto de factores admitidos en un rango, probabilidad, distribución o estado de riesgo explicable. No hay un modelo preseleccionado.'],
      ['03', 'Expresión de estrategia', 'BLOQUEADA', 'Convierte un modelo bloqueado en reglas de entrada, salida, tenencia, tamaño, costes, capacidad y riesgo. Acciones y opciones se validan por separado.'],
    ],
    boundary: 'Un factor no es un modelo. Un modelo no es una estrategia. Un backtest no concede autoridad al producto.',
    prior: 'Resultado del primer programa',
    priorBody: 'Strong-Leader Pullback está cerrado: V1 fue inconcluso y su única alternativa registrada fue rechazada por inestabilidad entre escenarios terminales. No se bloqueó ningún parámetro ni se abrieron Validación o Holdout.',
  },
} as const;

const FACTOR_NAMES: Record<string, Record<string, string>> = {
  en: {
    relative_return_spy_20s: '20-session relative return versus SPY',
    relative_return_acceleration_5_vs_prior15: 'Five-session relative acceleration versus prior 15',
    signed_path_efficiency_10s: '10-session signed path efficiency',
    positive_session_share_10s: '10-session positive-close share',
    largest_absolute_return_share_10s: 'Largest absolute-return share over 10 sessions',
    prior_atr_ratio_5_to_14: 'Prior ATR5 to ATR14 ratio',
    prior_close_range_10s_atr14: 'Prior 10-session close range over ATR14',
    close_vs_prior_high_20s_atr14: 'Close distance from prior 20-session high over ATR14',
    dollar_volume_surprise_1_to_20: 'One-session dollar-volume surprise versus prior 20',
    close_location_value_1s: 'One-session close-location value',
    absolute_overnight_gap_atr14: 'Absolute overnight gap over prior ATR14',
    rolling_maximum_drawdown_10s: '10-session rolling maximum drawdown',
    medium_term_relative_momentum_126s_skip5: '126-session relative momentum, skipping the latest five',
    short_term_relative_reversal_5s: 'Five-session market-relative reversal',
    intraday_relative_pressure_reversal_5s: 'Five-session intraday relative-pressure reversal',
    overnight_relative_persistence_5s: 'Five-session overnight relative persistence',
    down_market_relative_resilience_60s: '60-session down-market relative resilience',
    amihud_illiquidity_20s: '20-session Amihud illiquidity proxy',
    single_index_residual_volatility_60s: '60-session single-index residual volatility',
    relative_downside_semideviation_60s: '60-session relative downside semideviation',
  },
  zh: {
    relative_return_spy_20s: '20日相对 SPY 收益',
    relative_return_acceleration_5_vs_prior15: '5日相对强度加速度（对比此前15日）',
    signed_path_efficiency_10s: '10日带方向路径效率',
    positive_session_share_10s: '10日上涨交易日占比',
    largest_absolute_return_share_10s: '10日单日绝对收益集中度',
    prior_atr_ratio_5_to_14: '前一日 ATR5 / ATR14',
    prior_close_range_10s_atr14: '前10日收盘区间 / ATR14',
    close_vs_prior_high_20s_atr14: '收盘距前20日高点 / ATR14',
    dollar_volume_surprise_1_to_20: '单日成交额相对20日中位数异常',
    close_location_value_1s: '单日收盘位置',
    absolute_overnight_gap_atr14: '隔夜缺口绝对值 / ATR14',
    rolling_maximum_drawdown_10s: '10日滚动最大回撤',
    medium_term_relative_momentum_126s_skip5: '126日相对动量（跳过最近5日）',
    short_term_relative_reversal_5s: '5日市场相对反转',
    intraday_relative_pressure_reversal_5s: '5日日内相对压力反转',
    overnight_relative_persistence_5s: '5日隔夜相对延续',
    down_market_relative_resilience_60s: '60日下跌市场相对韧性',
    amihud_illiquidity_20s: '20日 Amihud 非流动性代理',
    single_index_residual_volatility_60s: '60日单指数残差波动率',
    relative_downside_semideviation_60s: '60日相对下行半偏差',
  },
  es: {
    relative_return_spy_20s: 'Rentabilidad relativa a SPY en 20 sesiones',
    relative_return_acceleration_5_vs_prior15: 'Aceleración relativa de cinco sesiones frente a las 15 anteriores',
    signed_path_efficiency_10s: 'Eficiencia direccional de la trayectoria en 10 sesiones',
    positive_session_share_10s: 'Proporción de cierres positivos en 10 sesiones',
    largest_absolute_return_share_10s: 'Concentración del mayor retorno absoluto en 10 sesiones',
    prior_atr_ratio_5_to_14: 'Cociente ATR5 / ATR14 previo',
    prior_close_range_10s_atr14: 'Rango previo de cierres de 10 sesiones sobre ATR14',
    close_vs_prior_high_20s_atr14: 'Distancia del cierre al máximo previo de 20 sesiones sobre ATR14',
    dollar_volume_surprise_1_to_20: 'Sorpresa de volumen monetario frente a la mediana previa de 20 sesiones',
    close_location_value_1s: 'Posición del cierre en una sesión',
    absolute_overnight_gap_atr14: 'Gap nocturno absoluto sobre ATR14 previo',
    rolling_maximum_drawdown_10s: 'Máxima caída móvil de 10 sesiones',
    medium_term_relative_momentum_126s_skip5: 'Momentum relativo de 126 sesiones, excluyendo las cinco más recientes',
    short_term_relative_reversal_5s: 'Reversión relativa al mercado en cinco sesiones',
    intraday_relative_pressure_reversal_5s: 'Reversión de presión relativa intradía en cinco sesiones',
    overnight_relative_persistence_5s: 'Persistencia relativa nocturna en cinco sesiones',
    down_market_relative_resilience_60s: 'Resiliencia relativa en mercados bajistas durante 60 sesiones',
    amihud_illiquidity_20s: 'Proxy de iliquidez de Amihud en 20 sesiones',
    single_index_residual_volatility_60s: 'Volatilidad residual de índice único en 60 sesiones',
    relative_downside_semideviation_60s: 'Semidesviación bajista relativa en 60 sesiones',
  },
};

const FACTOR_TAXONOMY: Record<string, Record<string, string>> = {
  en: { relative_leadership: 'Relative leadership', trend_path: 'Trend path', volatility_structure: 'Volatility structure', participation_execution: 'Participation & execution', downside_fragility: 'Downside fragility', medium_horizon_continuation: 'Medium-horizon continuation', short_horizon_reversal: 'Short-horizon reversal', return_timing: 'Return timing', market_state: 'Market state', liquidity_capacity: 'Liquidity & capacity', downside_risk: 'Downside risk', candidate_alpha: 'Candidate Alpha', setup_conditioner: 'Setup conditioner', applicability_input: 'Applicability input', risk_guard: 'Risk guard', positive_monotonic: 'Positive monotonic', negative_monotonic: 'Negative monotonic', no_standalone_alpha_claim: 'No standalone Alpha claim' },
  zh: { relative_leadership: '相对领导力', trend_path: '趋势路径', volatility_structure: '波动结构', participation_execution: '参与度与执行', downside_fragility: '下行脆弱性', medium_horizon_continuation: '中期延续', short_horizon_reversal: '短期反转', return_timing: '收益时段分解', market_state: '市场状态', liquidity_capacity: '流动性与容量', downside_risk: '下行风险', candidate_alpha: '候选 Alpha', setup_conditioner: '形态条件因子', applicability_input: '适用性输入', risk_guard: '风险护栏', positive_monotonic: '正向单调假设', negative_monotonic: '负向单调假设', no_standalone_alpha_claim: '不主张独立 Alpha' },
  es: { relative_leadership: 'Liderazgo relativo', trend_path: 'Trayectoria de tendencia', volatility_structure: 'Estructura de volatilidad', participation_execution: 'Participación y ejecución', downside_fragility: 'Fragilidad bajista', medium_horizon_continuation: 'Continuación a medio plazo', short_horizon_reversal: 'Reversión a corto plazo', return_timing: 'Descomposición temporal del retorno', market_state: 'Estado del mercado', liquidity_capacity: 'Liquidez y capacidad', downside_risk: 'Riesgo bajista', candidate_alpha: 'Candidato de Alpha', setup_conditioner: 'Condicionante de configuración', applicability_input: 'Variable de aplicabilidad', risk_guard: 'Salvaguarda de riesgo', positive_monotonic: 'Hipótesis monótona positiva', negative_monotonic: 'Hipótesis monótona negativa', no_standalone_alpha_claim: 'Sin afirmación de Alpha independiente' },
};

const COPY = {
  en: {
    eyebrow: 'Factor, model, and strategy research · governed registry',
    title: 'Quant Research Lab',
    subtitle: 'The authoritative record of what is measured, what is modeled, how it becomes a strategy, and where the evidence fails.',
    status: 'FACTOR DISCOVERY V2', statusValue: 'SCREEN REGISTERED · OUTCOMES UNREAD',
    statusNote: 'Five-year split evidence produced a byte-identical 98.59% qualification pass. Six finite Development trials are now frozen and appended to the cumulative ledger before outcome access. No factor is predictive or admitted yet.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    readiness: 'Evidence ladder', readinessItems: [
      ['Three-layer architecture', 'ACCEPTED', 'Factor Discovery, Model Construction, and Strategy Expression now have separate version and evidence boundaries.', 'met'],
      ['Cumulative research ledger', 'REGISTERED · 14 TRIALS', 'All eight consumed V1 trials remain intact; four V2 Alpha and two V2 risk trials are appended with outcomes unread.', 'met'],
      ['Factor Catalog V2', 'REGISTERED', 'Eight exact definitions cover continuation, reversal, return timing, defensive state, liquidity applicability, and downside risk.', 'met'],
      ['V2 data qualification', 'PASSED', 'The report and replay are byte-identical: 98.59% complete vectors, 267 eligible sessions, and all eight definitions clear the frozen gates.', 'met'],
      ['Development screen', 'REGISTERED', 'Six trials, labels, unchanged gates, block inference, Holm families, costs, promotion caps, and one-report/one-replay stopping are frozen.', 'met'],
      ['Screen implementation', 'CURRENT', 'Implement the frozen protocol exactly, retain every exclusion, then create one immutable Development report and one exact replay.', 'active'],
      ['Model, strategy & Product', 'LOCKED', 'Qualification is not Alpha. No predictive model, strategy expression, Candidate authority, or option-performance claim exists.', 'locked'],
    ],
    foundation: 'Research foundation snapshot', foundationNote: 'Verified, versioned evidence already built on Dell. Each item states both its useful scope and its limit.', foundationBadge: 'EVIDENCE REVIEWED · 15 SEP 2026',
    foundationItems: [
      ['Five-year market base', 'DEPTH COMPLETE', 'Contiguous EOD price and stable-identity depth are complete.', 'verified'],
      ['Historical membership', 'RECONSTRUCTED', '1,250 sessions are reconstructed and three are prospective; reconstructed history is not as operated.', 'qualified'],
      ['Corporate actions', 'PARTIAL EVIDENCE', '4,623 of 4,643 first-strategy exposures have exact event-date assignments; absence neutrality is not proven.', 'qualified'],
      ['Lifecycle & terminal', 'BOUNDED REFERENCES', 'All 302 five-session paths have either exact or finite-interval references; references are not strategy outcomes.', 'qualified'],
      ['Point-in-time fundamentals', 'ENGINEERING PILOT', 'Four registered SEC query paths and four strict as-operated projection sessions exist; this is engineering evidence only.', 'qualified'],
    ],
    foundationControls: 'Evaluation controls already frozen', controlLabels: ['Registered specifications', 'Chronological split', 'Purge + embargo', 'Cost scenarios per side', 'Sealed holdout use'],
    foundationBoundary: 'These facts are not blended into one readiness percentage. A weak mandatory evidence family keeps performance research locked.',
    factorQualification: 'Factor qualification V2', factorQualificationNote: 'The eight-factor catalog was calculated twice over the same frozen Dell population. The byte-identical replay measures source and implementation fitness only; it never reads future returns.', factorQualificationBadge: 'PASSED · EXACT REPLAY',
    factorStats: ['Registered factors', 'Complete vectors', 'Coverage', 'Pair checks', 'Near-duplicate groups'],
    factorCoverageMeaning: '431,249 of 437,402 declared paths produced complete eight-factor vectors. The 6,153 incomplete paths remain explicit; none was zero-filled. Availability reached 98.59% across 267 eligible sessions, split 123 / 144 across the frozen chronological halves.',
    factorRedundancy: 'Strongest same-session relationship', factorRedundancyBody: 'The largest absolute weighted Spearman relationship was 0.8942 between the two risk guards. No pair met the full near-duplicate rule. This passes a data-qualification test; it says nothing about predictive value.',
    factorRoles: 'Catalog roles', factorRoleValues: ['4 candidate Alpha measurements', '1 setup conditioner', '1 applicability input', '2 risk guards'],
    factorInspect: 'Inspect all eight registered definitions and exact formulas',
    factorRole: 'Role', factorFormula: 'Exact formula', factorWindow: 'Point-in-time source window', factorExpectation: 'Registered relationship',
    factorCutoffValue: 'completed session close → next session open', factorMissingValue: 'explicit unavailable · never zero-fill',
    factorVerdict: 'What V2 earned', factorVerdictValue: '8 / 8 eligible for protocol review', factorVerdictBody: 'Four candidate Alpha measurements, one setup conditioner, one applicability input, and two risk guards cleared coverage, chronology, variation, tie, and redundancy gates. They are measurements awaiting a registered outcome test—not admitted factors.',
    factorNext: 'Next bounded action', factorNextValue: 'IMPLEMENT EXACT SCREEN · THEN REPLAY', factorNextBody: 'The finite protocol is registered. Implement its six trials without revising formulas or gates, then retain one Development report and one exact replay. Validation, Holdout, model construction, and Candidate ranking stay closed.',
    factorLimits: 'Qualification limits', factorLimitsBody: 'Membership is reconstructed rather than as operated; historical classifications and broad Regime diversity remain unproven; daily bars do not observe spreads or signed order flow; and split-neutral absence remains a disclosed source limitation despite the qualified reconstruction.',
    screeningV2: 'Registered Development Screen · Factor Catalog V2', screeningV2Note: 'The outcome-reading question is now finite and machine-bound. Registration authorizes exact implementation of the screen—not a model or a strategy.', screeningV2Badge: 'REGISTERED · OUTCOMES UNREAD',
    screeningV2Stats: ['Formal trials', 'Cumulative trials', 'Development sessions', 'Declared paths', 'Primary / decay'],
    screeningV2State: 'Current evidence state', screeningV2StateValue: '0 outcomes read', screeningV2StateBody: 'Four Alpha and two risk-guard trials are registered. The conditioner and Amihud applicability input consume no standalone outcome trials.',
    screeningV2Selection: 'Promotion boundary', screeningV2SelectionValue: '≤2 Alpha + ≤1 risk guard', screeningV2SelectionBody: 'Every survivor must pass standalone and incremental evidence, chronology, concentration, monotonicity, decay, and Holm gates. At least one Alpha survivor is required before Model Construction.',
    screeningV2Inspect: 'Inspect the frozen six-trial protocol and cumulative ledger', screeningV2Protocol: 'Frozen evaluation', screeningV2ProtocolBody: '3-session primary stock outcome · 1/5-session decay · same-session ranks · 10,000 circular five-session block-bootstrap replications · unchanged V1 gates · Holm within 4-Alpha and 2-risk families · 0/10/25/50 bps-per-side diagnostics.', screeningV2Limits: 'What remains closed', screeningV2LimitsBody: 'Historical sector neutralization and broad Regime diversity are unavailable. The screen is reconstructed Development selection evidence only; Validation, Holdout, model, strategy, Candidate, options, and trading remain locked.',
    factorScreen: 'Historical Development Screen · Factor Catalog V1', factorScreenNote: 'Retained failed research, not the current campaign. Its finite protocol was committed before outcome access and executed twice against the same Development cohort; no candidate Alpha passed.', factorScreenBadge: 'RETAINED FAILURE · EXACT REPLAY',
    factorScreenStats: ['Formal hypotheses', 'Signal sessions', 'Observations', 'Forward labels', 'Selected Alpha / risk'],
    factorScreenOutcome: 'The honest result', factorScreenOutcomeBody: 'Zero candidate-Alpha factors passed the frozen gates. Factor Catalog V1 therefore closes without a predictive model and cannot change Stock Candidates.',
    factorScreenSelected: 'Evidence retained', factorScreenSelectedBody: '10-session rolling maximum drawdown passed as a downside-risk guard: robust rank effect 0.2540, 90% lower bound 0.2322, Holm-adjusted p 0.0003. It may constrain a later model; it is not Alpha by itself.',
    factorScreenDecisions: 'All eight registered decisions', factorScreenDecisionLabels: ['Robust effect', '90% lower bound', 'Holm p', 'Failed gates'], factorScreenPassed: 'Risk guard retained', factorScreenRejected: 'Rejected',
    factorScreenInspect: 'Inspect protocol, custody, limits, and exact report identity',
    factorScreenProtocol: 'Frozen evaluation', factorScreenProtocolBody: 'Primary horizon: 3 sessions · decay diagnostics: 1 and 5 · 10,000 circular five-session block-bootstrap replications · 90% intervals · Holm family-wise control · 0/10/25/50 bps per-side cost diagnostics.',
    factorScreenLimits: 'Interpretation boundary', factorScreenLimitsBody: 'Development only; reconstructed membership; 106 signal sessions; historical classification and broad Regime diversity not proven; fixed costs are scenarios, not execution calibration. Validation and Holdout were never opened.',
    engineering: 'Historical method-engineering evidence', engineeringNote: 'The first Pullback method was run twice over the reconstructed Dell population with identical fingerprints. These retained facts answer whether that method could be computed—not whether it worked.', engineeringBadge: 'HISTORICAL · OUTCOME BLIND',
    engineeringStages: ['Method frozen', 'Implementation tested', 'Population replayed', 'Performance admission'], verified: 'Verified', blockedState: 'Blocked',
    declaredSessions: 'Declared sessions', completeSessions: 'Feature-complete sessions', declaredPaths: 'Declared paths', computablePaths: 'Computable paths', excludedPaths: 'Explicit exclusions',
    coverageMeaning: '95.38% is method-computability coverage—not win rate, prediction accuracy, or return.',
    proxyBoundary: 'What remains provisional', proxyBody: 'Membership is reconstructed rather than as operated; split adjustment has unproven neutral rows; Regime is recomputed; and no Stress-state path appears in this interval.',
    owner: 'Research ownership', ownerValue: 'WH Alpha personal quantitative research',
    boundary: 'Authority boundary', boundaryBody: 'The Lab owns factor, model, expression, and evaluation evidence. Stock Candidates may later consume only the small reviewed set of explicitly activated expressions; there is no permanent model-count limit.',
    registry: 'Historical first program', featured: 'Retained rejected method record',
    methodOnly: 'Method only', noCandidate: 'Not Candidate-eligible', notAssessed: 'Market fit not assessed',
    version: 'Version', lifecycleState: 'Lifecycle', evidence: 'Evidence', applicability: 'Applicability',
    oos: 'Out-of-sample observations', nextDecision: 'Next decision', strength: 'Primary strength', weakness: 'Primary weakness',
    inspect: 'Inspect complete logic, formulas, parameters, evaluation, and fingerprints',
    logic: '1 · Logic and decision', features: '2 · Inputs and features', parameters: '3 · Parameters and search budget',
    evaluation: '4 · Evaluation design', gates: '5 · Advancement gates', failure: '6 · Failure, invalidation, and blockers', reproduction: '7 · Reproduction',
    decisionUse: 'Decision use', hypothesis: 'Hypothesis', rationale: 'Economic rationale', signal: 'Signal rule', ranking: 'Ranking rule',
    source: 'Source', cutoff: 'Availability cutoff', lookback: 'Lookback', transform: 'Transform', expected: 'Expected direction', missing: 'Missingness',
    candidates: 'Candidate values', selection: 'Selection',
    split: 'Chronology', outcome: 'Primary outcome', secondary: 'Secondary outcomes', benchmark: 'Benchmark', control: 'Control', inference: 'Inference', multiplicity: 'Multiplicity', costs: 'Cost scenarios', holdout: 'Holdout custody', portfolio: 'Portfolio construction',
    counter: 'Required counterevidence review', invalidation: 'Invalidation conditions', blockers: 'Current blockers', risks: 'Risk disclosures',
    none: 'None', undefined: 'Not defined', sessions: 'sessions', falseValue: 'Not defined',
    lifecycle: 'Three-layer promotion path', stages: ['Factor discovery', 'Model construction', 'Strategy expression', 'Validation', 'Sealed holdout', 'Shadow', 'Activation'],
    current: 'Current', locked: 'Locked', blocked: 'Blocked by evidence',
    results: 'Current research ledger', resultsNote: 'Failures remain visible; no synthetic substitute and no implied active performance',
    resultCards: [['Factor Catalog V2', 'Screen registered · outcomes unread'], ['Factor Screen V1', 'Closed · no candidate Alpha'], ['Pullback program', 'Closed · no stable selection'], ['Active models', 'None']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '因子、模型与策略研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '权威记录测量什么、如何建模、怎样形成策略，以及证据在哪一层失败，而不是只陈列漂亮回测。',
    status: '因子发现 V2', statusValue: '筛选已登记 · 尚未读取结果',
    statusNote: '五年拆股证据带来了逐字节一致、覆盖率98.59%的资格通过。6项有限开发期试验已经在读取结果前冻结并写入累计账本；目前没有因子被证明有效或获准进入模型。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    readiness: '证据阶梯', readinessItems: [
      ['三层研究架构', '已生效', '因子发现、模型构建与策略表达现在拥有相互独立的版本和证据边界。', 'met'],
      ['累计研究账本', '已登记 · 共14项试验', 'V1 已消耗的8项试验原样保留；V2 新增4项 Alpha 与2项风险试验，且结果尚未读取。', 'met'],
      ['因子目录 V2', '已登记', '8项精确定义覆盖延续、反转、收益时段、防御状态、流动性适用性与下行风险。', 'met'],
      ['V2 数据资格诊断', '已通过', '报告与重放逐字节一致：完整向量覆盖率98.59%，267个合格交易日，8项定义全部通过冻结门槛；6,491条五年拆股来源与旧正式证据重叠冲突为零。', 'met'],
      ['开发期筛选', '已登记', '6项试验、标签、原有门槛、区块推断、Holm家族、成本、晋级上限与一次报告/一次重放规则均已冻结。', 'met'],
      ['筛选实现', '当前工作', '严格实现冻结协议，保留每一条排除原因，然后只生成一份不可变开发期报告与一次精确重放。', 'active'],
      ['模型、策略与产品', '锁定', '资格通过不等于 Alpha；目前仍没有预测模型、策略表达、个股候选权限或期权绩效主张。', 'locked'],
    ],
    foundation: '研究基础快照', foundationNote: '以下是已经在戴尔完成核验并版本化的工程证据；每一项同时标明可用范围与证据边界。', foundationBadge: '证据核对 · 2026-09-15',
    foundationItems: [
      ['五年行情基础', '深度已完成', '连续日线行情与稳定证券身份的五年深度已经完成。', 'verified'],
      ['历史成员资格', '事后重建', '其中1,250个交易日为事后重建、3个为前瞻记录；重建历史不等于当时实录。', 'qualified'],
      ['公司行动', '部分证据', '第一策略4,643条暴露中4,623条已有精确事件日匹配；尚未证明其余空白均为中性。', 'qualified'],
      ['生命周期与终端', '参考边界已覆盖', '302条五日路径均已有精确或有限区间参考；参考证据仍不等于策略收益。', 'qualified'],
      ['点时基本面', '工程试点', '已登记4条SEC查询路径，并取得4个严格按当时可用信息投影的交易日；目前仅属工程证据。', 'qualified'],
    ],
    foundationControls: '已经冻结的评估约束', controlLabels: ['已登记规格', '时间顺序切分', '清洗期 + 隔离期', '单边成本情景', '封存样本外使用次数'],
    foundationBoundary: '不会把不同证据强行合成为一个“总完成度”。任何必需证据族不合格，绩效研究仍保持锁定。',
    factorQualification: '因子资格诊断 V2', factorQualificationNote: '8项因子已在戴尔同一冻结总体上完整计算两次。逐字节一致的精确重放只检验来源与实现是否合格，全程不读取未来收益。', factorQualificationBadge: '已通过 · 精确重放',
    factorStats: ['登记因子', '完整向量', '覆盖率', '成对核验', '近重复组'],
    factorCoverageMeaning: '437,402条声明路径中，431,249条形成完整的8因子向量；6,153条不完整路径继续明确保留，没有静默补零。覆盖率达到98.59%，267个合格交易日在冻结的前后时间段中分布为123 / 144。',
    factorRedundancy: '最强同日关系', factorRedundancyBody: '两个风险护栏之间的绝对加权 Spearman 关系最高，为0.8942；没有因子对满足完整的近重复规则。这只代表数据资格通过，并不代表存在预测价值。',
    factorRoles: '目录角色', factorRoleValues: ['4项候选 Alpha 测量', '1项形态条件因子', '1项适用性输入', '2项风险护栏'],
    factorInspect: '展开审阅8项登记定义与精确公式',
    factorRole: '角色', factorFormula: '精确公式', factorWindow: '点时数据窗口', factorExpectation: '登记关系',
    factorCutoffValue: '当日收盘数据完成 → 最早下一交易日开盘执行', factorMissingValue: '明确标为不可用 · 禁止静默补零',
    factorVerdict: 'V2 获得了什么资格', factorVerdictValue: '8 / 8 项可进入协议审查', factorVerdictBody: '4项候选 Alpha 测量、1项形态条件、1项适用性输入和2项风险护栏均通过覆盖、时间分布、取值、并列与冗余门槛。它们只是等待登记结果检验的测量，并非已获准因子。',
    factorNext: '下一项有限动作', factorNextValue: '精确实现筛选 · 然后重放', factorNextBody: '有限协议已经登记。不得修改公式或门槛，只实现其中6项试验，再保留一份开发期报告和一次精确重放。验证集、留出集、模型构建和个股候选排名继续关闭。',
    factorLimits: '资格诊断边界', factorLimitsBody: '成员资格为事后重建而非当时实录；历史行业分类和充分的市场状态多样性尚未证明；日线不能观察点差或带方向订单流；即使重建数据通过资格，拆股空白是否中性仍作为来源限制公开保留。',
    screeningV2: '已登记开发期筛选 · 因子目录 V2', screeningV2Note: '读取结果的问题现在已经有限且可机器核验。登记只授权精确实现筛选，不代表模型或策略成立。', screeningV2Badge: '已登记 · 结果未读取',
    screeningV2Stats: ['正式试验', '累计试验', '开发期交易日', '声明路径', '主要 / 衰减周期'],
    screeningV2State: '当前证据状态', screeningV2StateValue: '结果读取次数 0', screeningV2StateBody: '已登记4项 Alpha 与2项风险护栏试验；条件因子与 Amihud 适用性输入不消耗任何独立结果试验。',
    screeningV2Selection: '晋级边界', screeningV2SelectionValue: '最多2项 Alpha + 1项风险护栏', screeningV2SelectionBody: '每个晋级项都必须通过独立与增量证据、时间稳定性、集中度、单调性、衰减和 Holm 门槛；至少1项 Alpha 存活，才可提出模型构建。',
    screeningV2Inspect: '展开审阅冻结的6项试验协议与累计账本', screeningV2Protocol: '冻结评估规则', screeningV2ProtocolBody: '主要股票结果3个交易日 · 1/5日衰减 · 同日秩 · 10,000次五日循环区块自助法 · V1门槛保持不变 · 4项Alpha与2项风险分别做Holm校正 · 单边0/10/25/50 bps成本诊断。', screeningV2Limits: '仍保持关闭的部分', screeningV2LimitsBody: '历史行业中性化和充分的市场状态多样性仍不可用。筛选仅属于事后重建开发期选择证据；验证集、留出集、模型、策略、个股候选、期权与交易继续锁定。',
    factorScreen: '历史开发期筛选 · 因子目录 V1', factorScreenNote: '这是保留的失败研究，不是当前项目。有限协议在读取结果前已经提交，并在同一开发样本上完整执行两次；没有候选 Alpha 通过。', factorScreenBadge: '失败留档 · 精确重放',
    factorScreenStats: ['正式假设', '信号交易日', '观察数', '前瞻标签', '入选 Alpha / 风险'],
    factorScreenOutcome: '真实结论', factorScreenOutcomeBody: '没有候选 Alpha 通过冻结门槛。因此因子目录 V1 在没有预测模型的状态下关闭，也不得改变个股候选排名。',
    factorScreenSelected: '保留的证据', factorScreenSelectedBody: '10日滚动最大回撤作为下行风险护栏通过：稳健秩效应0.2540，90%下界0.2322，Holm校正 p 值0.0003。它可以约束未来模型，但自身不是 Alpha。',
    factorScreenDecisions: '8项登记决策', factorScreenDecisionLabels: ['稳健效应', '90%下界', 'Holm p 值', '失败门槛'], factorScreenPassed: '保留风险护栏', factorScreenRejected: '未通过',
    factorScreenInspect: '展开审阅协议、保管、限制与报告身份',
    factorScreenProtocol: '冻结评估规则', factorScreenProtocolBody: '主要周期3个交易日；1日与5日用于衰减诊断；10,000次五日循环区块自助法；90%区间；Holm家族错误控制；单边0/10/25/50 bps成本情景。',
    factorScreenLimits: '解释边界', factorScreenLimitsBody: '仅限开发期；成员资格为事后重建；仅106个信号日；历史分类和充分的市场状态多样性未获证明；固定成本只是情景而非执行校准。验证集和留出集从未打开。',
    engineering: '历史方法工程证据', engineeringNote: '首个回撤方法已在戴尔重建样本上完整运行两次，结果指纹完全一致。以下保留事实只回答“该方法能否计算”，不回答“策略是否有效”。', engineeringBadge: '历史记录 · 不含结果',
    engineeringStages: ['方法已冻结', '实现测试通过', '总体重放完成', '绩效数据准入'], verified: '已核验', blockedState: '仍阻塞',
    declaredSessions: '声明交易日', completeSessions: '特征完整交易日', declaredPaths: '声明路径', computablePaths: '可计算路径', excludedPaths: '明确排除',
    coverageMeaning: '95.38% 是方法可计算路径覆盖率，不是胜率、预测准确率或收益率。',
    proxyBoundary: '仍属临时证据的部分', proxyBody: '成员资格是事后重建而非当时实录；拆股复权仍有未证明的中性空白；Regime 为重新计算；该区间没有 Stress 状态路径。',
    owner: '研究归属', ownerValue: 'WH Alpha 个人量化研究',
    boundary: '权限边界', boundaryBody: '实验室负责因子、模型、表达与评估证据；个股候选未来只消费少量经过独立审查并明确激活的表达，不设永久模型数量上限。',
    registry: '首个历史研究项目', featured: '保留的被拒绝方法档案',
    methodOnly: '仅有方法', noCandidate: '不可进入个股候选', notAssessed: '尚未评估市场适配',
    version: '版本', lifecycleState: '生命周期', evidence: '证据类型', applicability: '当前适配',
    oos: '样本外观察数', nextDecision: '下一项决策', strength: '主要优点', weakness: '主要弱点',
    inspect: '展开审阅完整逻辑、公式、参数、评估设计与指纹',
    logic: '1 · 逻辑与决策用途', features: '2 · 输入与特征', parameters: '3 · 参数与搜索预算',
    evaluation: '4 · 评估设计', gates: '5 · 晋级门槛', failure: '6 · 反面证据、失效条件与阻塞项', reproduction: '7 · 复现信息',
    decisionUse: '决策用途', hypothesis: '研究假设', rationale: '经济逻辑', signal: '触发公式', ranking: '排名规则',
    source: '来源', cutoff: '可用时间界限', lookback: '回看窗口', transform: '变换', expected: '预期方向', missing: '缺失处理',
    candidates: '候选取值', selection: '选择范围',
    split: '时间划分', outcome: '主要结果', secondary: '次要结果', benchmark: '基准', control: '对照组', inference: '推断方法', multiplicity: '多重检验', costs: '成本情景', holdout: '样本外保管', portfolio: '组合构建',
    counter: '必须检查的反面证据', invalidation: '失效条件', blockers: '当前阻塞项', risks: '风险声明',
    none: '无', undefined: '未定义', sessions: '个交易日', falseValue: '尚未定义',
    lifecycle: '三层晋级路径', stages: ['因子发现', '模型构建', '策略表达', '验证', '封存留出集', '影子运行', '正式激活'],
    current: '当前', locked: '锁定', blocked: '受证据阻塞',
    results: '当前研究账本', resultsNote: '失败结果继续保留；不使用合成替代，也不暗示存在有效绩效',
    resultCards: [['因子目录 V2', '筛选已登记 · 结果未读取'], ['因子筛选 V1', '已关闭 · 无候选 Alpha'], ['回撤研究项目', '已关闭 · 无稳定选择'], ['已激活模型', '无']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
  es: {
    eyebrow: 'Investigación de factores, modelos y estrategias · registro gobernado',
    title: 'Laboratorio de investigación cuantitativa',
    subtitle: 'El registro autoritativo de qué se mide, qué se modela, cómo se expresa una estrategia y en qué capa falla la evidencia.',
    status: 'DESCUBRIMIENTO DE FACTORES V2', statusValue: 'FILTRO REGISTRADO · RESULTADOS SIN CONSULTAR',
    statusNote: 'La evidencia de splits produjo una calificación del 98,59 % reproducida byte a byte. Seis pruebas finitas de Desarrollo ya están congeladas y añadidas al registro acumulativo antes de consultar resultados. Ningún factor es aún predictivo ni está admitido.',
    coverage: 'Estado de la evidencia', coverageNote: 'La integridad del método y la eficacia del modelo son cuestiones distintas.',
    coverageBoundary: 'Publicar un método no convierte la estrategia en validada, adecuada para el mercado actual ni predictiva de rentabilidades de opciones.',
    readiness: 'Escalera de evidencia', readinessItems: [
      ['Arquitectura de tres capas', 'ACEPTADA', 'Descubrimiento de factores, Construcción del modelo y Expresión de estrategia tienen límites de versión y evidencia separados.', 'met'],
      ['Registro acumulativo de investigación', 'REGISTRADO · 14 PRUEBAS', 'Las ocho pruebas consumidas de V1 permanecen intactas; se añaden cuatro pruebas Alpha y dos de riesgo V2 sin consultar resultados.', 'met'],
      ['Catálogo de factores V2', 'REGISTRADO', 'Ocho definiciones exactas cubren continuación, reversión, momento del retorno, defensa, aplicabilidad de liquidez y riesgo bajista.', 'met'],
      ['Calificación de datos V2', 'SUPERADA', 'El informe y la reproducción son idénticos byte a byte: 98,59 % de vectores completos, 267 sesiones aptas y los ocho factores superan los filtros congelados; no hubo conflictos con la evidencia canónica previa.', 'met'],
      ['Selección en Desarrollo', 'REGISTRADA', 'Se congelaron seis pruebas, etiquetas, filtros sin cambios, inferencia por bloques, familias de Holm, costes, límites de promoción y una regla de un informe y una reproducción.', 'met'],
      ['Implementación del filtro', 'ACTUAL', 'Implementar exactamente el protocolo congelado, conservar cada exclusión y producir un único informe inmutable de Desarrollo y una reproducción exacta.', 'active'],
      ['Modelo, estrategia y Producto', 'BLOQUEADOS', 'Superar la calificación no demuestra Alpha. Aún no existe modelo predictivo, expresión de estrategia, autoridad sobre Candidatos ni afirmación sobre opciones.', 'locked'],
    ],
    foundation: 'Resumen de la base de investigación', foundationNote: 'Evidencia verificada y versionada que ya existe en Dell. Cada punto indica tanto su utilidad como su límite.', foundationBadge: 'EVIDENCIA REVISADA · 15 SEP 2026',
    foundationItems: [
      ['Base de mercado a cinco años', 'PROFUNDIDAD COMPLETA', 'La profundidad continua de precios diarios e identidad estable está completa.', 'verified'],
      ['Composición histórica', 'RECONSTRUIDA', '1.250 sesiones son reconstruidas y tres son prospectivas; la reconstrucción no equivale a un registro operativo de la fecha.', 'qualified'],
      ['Acciones corporativas', 'EVIDENCIA PARCIAL', '4.623 de 4.643 exposiciones del primer estudio tienen fecha de evento exacta; no se ha demostrado la neutralidad de las ausencias.', 'qualified'],
      ['Ciclo de vida y terminal', 'REFERENCIAS ACOTADAS', 'Las 302 trayectorias disponen de una referencia exacta o de intervalo finito; una referencia no es un resultado de estrategia.', 'qualified'],
      ['Fundamentales a fecha de conocimiento', 'PILOTO DE INGENIERÍA', 'Existen cuatro consultas SEC registradas y cuatro sesiones con proyección estricta según la información disponible entonces; sigue siendo evidencia de ingeniería.', 'qualified'],
    ],
    foundationControls: 'Controles de evaluación ya congelados', controlLabels: ['Especificaciones registradas', 'División cronológica', 'Purga + embargo', 'Escenarios de costes por lado', 'Uso del holdout sellado'],
    foundationBoundary: 'Estos hechos no se combinan en un único porcentaje de avance. Una familia de evidencia obligatoria insuficiente mantiene bloqueada la investigación de rendimiento.',
    factorQualification: 'Calificación de factores V2', factorQualificationNote: 'El catálogo de ocho factores se calculó dos veces sobre la misma población congelada en Dell. La reproducción idéntica byte a byte evalúa solo la aptitud de las fuentes y de la implementación; nunca consulta rendimientos futuros.', factorQualificationBadge: 'SUPERADA · REPRODUCCIÓN EXACTA',
    factorStats: ['Factores registrados', 'Vectores completos', 'Cobertura', 'Pares revisados', 'Grupos casi duplicados'],
    factorCoverageMeaning: 'De 437.402 trayectorias declaradas, 431.249 produjeron vectores completos de ocho factores. Las 6.153 incompletas siguen explícitas, sin rellenarlas con cero. La disponibilidad alcanzó el 98,59 % en 267 sesiones aptas, repartidas 123 / 144 entre las dos mitades cronológicas congeladas.',
    factorRedundancy: 'Relación contemporánea más intensa', factorRedundancyBody: 'La mayor relación de Spearman ponderada en valor absoluto fue 0,8942 entre las dos salvaguardas de riesgo. Ningún par cumplió la regla completa de casi duplicado. Esto supera una prueba de datos, pero no demuestra capacidad predictiva.',
    factorRoles: 'Funciones del catálogo', factorRoleValues: ['4 medidas candidatas de Alpha', '1 condicionante de configuración', '1 variable de aplicabilidad', '2 salvaguardas de riesgo'],
    factorInspect: 'Examinar las ocho definiciones registradas y sus fórmulas exactas',
    factorRole: 'Función', factorFormula: 'Fórmula exacta', factorWindow: 'Ventana point-in-time', factorExpectation: 'Relación registrada',
    factorCutoffValue: 'cierre completo de la sesión → primera ejecución en la apertura siguiente', factorMissingValue: 'ausencia explícita · nunca se rellena con cero',
    factorVerdict: 'Qué habilitó V2', factorVerdictValue: '8 / 8 aptos para revisar el protocolo', factorVerdictBody: 'Las cuatro medidas candidatas de Alpha, un condicionante, una variable de aplicabilidad y dos salvaguardas superaron cobertura, cronología, variación, empates y redundancia. Son mediciones pendientes de una prueba registrada, no factores admitidos.',
    factorNext: 'Siguiente acción acotada', factorNextValue: 'IMPLEMENTAR EL FILTRO EXACTO · DESPUÉS REPRODUCIR', factorNextBody: 'El protocolo finito ya está registrado. Se implementarán sus seis pruebas sin modificar fórmulas ni filtros, seguidas de un informe de Desarrollo y una reproducción exacta. Validación, Holdout, modelo y Candidatos siguen cerrados.',
    factorLimits: 'Límites de la calificación', factorLimitsBody: 'La composición está reconstruida y no registrada tal como se operó; la clasificación histórica y una diversidad amplia de regímenes no están demostradas; las barras diarias no observan diferenciales ni flujo firmado; la neutralidad de ausencias de splits sigue declarada como limitación incluso tras la calificación.',
    screeningV2: 'Selección registrada en Desarrollo · Catálogo V2', screeningV2Note: 'La pregunta que consultará resultados ya es finita y verificable por máquina. El registro autoriza implementar exactamente la selección, no un modelo ni una estrategia.', screeningV2Badge: 'REGISTRADA · RESULTADOS SIN CONSULTAR',
    screeningV2Stats: ['Pruebas formales', 'Pruebas acumuladas', 'Sesiones de Desarrollo', 'Trayectorias declaradas', 'Horizonte principal / decaimiento'],
    screeningV2State: 'Estado actual de la evidencia', screeningV2StateValue: '0 resultados consultados', screeningV2StateBody: 'Hay cuatro pruebas Alpha y dos salvaguardas de riesgo registradas. El condicionante y la variable Amihud de aplicabilidad no consumen pruebas independientes.',
    screeningV2Selection: 'Límite de promoción', screeningV2SelectionValue: '≤2 Alpha + ≤1 salvaguarda', screeningV2SelectionBody: 'Cada superviviente debe superar evidencia independiente e incremental, cronología, concentración, monotonicidad, decaimiento y Holm. Se exige al menos un Alpha antes de proponer Construcción del modelo.',
    screeningV2Inspect: 'Examinar el protocolo congelado de seis pruebas y el registro acumulativo', screeningV2Protocol: 'Evaluación congelada', screeningV2ProtocolBody: 'Resultado principal a 3 sesiones · decaimiento a 1/5 · rangos por sesión · 10.000 réplicas bootstrap con bloques circulares de cinco sesiones · filtros V1 sin cambios · Holm en familias de 4 Alpha y 2 riesgos · diagnósticos de 0/10/25/50 pb por lado.', screeningV2Limits: 'Qué permanece cerrado', screeningV2LimitsBody: 'No se dispone de neutralización sectorial histórica ni de diversidad amplia de regímenes. La selección solo aporta evidencia de Desarrollo reconstruida; Validación, Holdout, modelo, estrategia, Candidatos, opciones y negociación siguen bloqueados.',
    factorScreen: 'Selección histórica en Desarrollo · Catálogo V1', factorScreenNote: 'Investigación fallida conservada, no la campaña actual. El protocolo finito se confirmó antes de consultar resultados y se ejecutó dos veces sobre la misma cohorte; ningún candidato de Alpha superó los filtros.', factorScreenBadge: 'FALLO CONSERVADO · REPRODUCCIÓN EXACTA',
    factorScreenStats: ['Hipótesis formales', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras', 'Alpha / riesgo seleccionados'],
    factorScreenOutcome: 'Resultado sin adornos', factorScreenOutcomeBody: 'Ningún candidato de Alpha superó los filtros congelados. El Catálogo V1 se cierra sin modelo predictivo y no puede modificar la clasificación de acciones.',
    factorScreenSelected: 'Evidencia conservada', factorScreenSelectedBody: 'La máxima caída móvil de 10 sesiones superó los filtros como salvaguarda bajista: efecto robusto de rango 0,2540, límite inferior del 90 % de 0,2322 y p de Holm 0,0003. Puede limitar un modelo futuro; por sí sola no es Alpha.',
    factorScreenDecisions: 'Las ocho decisiones registradas', factorScreenDecisionLabels: ['Efecto robusto', 'Límite inferior 90 %', 'p de Holm', 'Filtros fallidos'], factorScreenPassed: 'Salvaguarda conservada', factorScreenRejected: 'Rechazado',
    factorScreenInspect: 'Examinar protocolo, custodia, límites e identidad exacta',
    factorScreenProtocol: 'Evaluación congelada', factorScreenProtocolBody: 'Horizonte principal: 3 sesiones; diagnósticos de decaimiento: 1 y 5; 10.000 réplicas bootstrap con bloques circulares de cinco sesiones; intervalos del 90 %; control familiar de Holm; costes de 0/10/25/50 pb por lado.',
    factorScreenLimits: 'Límite de interpretación', factorScreenLimitsBody: 'Solo Desarrollo; composición reconstruida; 106 sesiones de señal; clasificación histórica y diversidad amplia de regímenes no demostradas; los costes fijos son escenarios, no calibración de ejecución. Validación y Holdout nunca se abrieron.',
    engineering: 'Evidencia histórica de ingeniería', engineeringNote: 'El primer método Pullback se ejecutó dos veces sobre la población reconstruida en Dell y produjo huellas idénticas. Estos datos conservados indican si aquel método podía calcularse, no si funcionaba.', engineeringBadge: 'HISTÓRICA · SIN RESULTADOS',
    engineeringStages: ['Método congelado', 'Implementación probada', 'Población reproducida', 'Admisión de rendimiento'], verified: 'Verificado', blockedState: 'Bloqueada',
    declaredSessions: 'Sesiones declaradas', completeSessions: 'Sesiones con características completas', declaredPaths: 'Trayectorias declaradas', computablePaths: 'Trayectorias computables', excludedPaths: 'Exclusiones explícitas',
    coverageMeaning: 'El 95,38 % mide cobertura de cálculo del método; no es tasa de acierto, precisión predictiva ni rentabilidad.',
    proxyBoundary: 'Qué sigue siendo provisional', proxyBody: 'La composición está reconstruida y no registrada tal como se operó; hay filas neutrales de ajustes sin demostrar; el régimen se recalculó; y el intervalo no contiene trayectorias en estado Stress.',
    owner: 'Titularidad de la investigación', ownerValue: 'Investigación cuantitativa propia de WH Alpha',
    boundary: 'Límite de autoridad', boundaryBody: 'El Laboratorio custodia la evidencia de factores, modelos, expresiones y evaluación. Candidatos solo podrá consumir un conjunto pequeño y revisado de expresiones activadas, sin un límite numérico permanente.',
    registry: 'Primer programa histórico', featured: 'Método rechazado conservado',
    methodOnly: 'Solo método', noCandidate: 'No apto para Candidatos', notAssessed: 'Adecuación al mercado no evaluada',
    version: 'Versión', lifecycleState: 'Ciclo de vida', evidence: 'Evidencia', applicability: 'Aplicabilidad',
    oos: 'Observaciones fuera de muestra', nextDecision: 'Próxima decisión', strength: 'Fortaleza principal', weakness: 'Debilidad principal',
    inspect: 'Examinar la lógica completa, las fórmulas, los parámetros, la evaluación y las huellas',
    logic: '1 · Lógica y decisión', features: '2 · Entradas y características', parameters: '3 · Parámetros y presupuesto de búsqueda',
    evaluation: '4 · Diseño de evaluación', gates: '5 · Criterios de avance', failure: '6 · Fallos, invalidación y bloqueos', reproduction: '7 · Reproducción',
    decisionUse: 'Uso en la decisión', hypothesis: 'Hipótesis', rationale: 'Fundamento económico', signal: 'Regla de señal', ranking: 'Regla de clasificación',
    source: 'Fuente', cutoff: 'Corte de disponibilidad', lookback: 'Ventana retrospectiva', transform: 'Transformación', expected: 'Dirección esperada', missing: 'Tratamiento de ausencias',
    candidates: 'Valores candidatos', selection: 'Selección',
    split: 'Cronología', outcome: 'Resultado principal', secondary: 'Resultados secundarios', benchmark: 'Referencia', control: 'Control', inference: 'Inferencia', multiplicity: 'Multiplicidad', costs: 'Escenarios de costes', holdout: 'Custodia del holdout', portfolio: 'Construcción de cartera',
    counter: 'Revisión obligatoria de evidencia contraria', invalidation: 'Condiciones de invalidación', blockers: 'Bloqueos actuales', risks: 'Divulgaciones de riesgo',
    none: 'Ninguno', undefined: 'No definido', sessions: 'sesiones', falseValue: 'No definido',
    lifecycle: 'Ruta de promoción de tres capas', stages: ['Descubrimiento de factores', 'Construcción del modelo', 'Expresión de estrategia', 'Validación', 'Holdout sellado', 'Sombra', 'Activación'],
    current: 'Actual', locked: 'Bloqueado', blocked: 'Bloqueado por la evidencia',
    results: 'Registro de investigación actual', resultsNote: 'Los fallos siguen visibles; sin sustitutos sintéticos ni rendimiento activo implícito',
    resultCards: [['Catálogo de factores V2', 'Filtro registrado · resultados sin consultar'], ['Selección de factores V1', 'Cerrada · sin candidato de Alpha'], ['Programa Pullback', 'Cerrado · sin selección estable'], ['Modelos activos', 'Ninguno']],
    interpret: 'Cómo se presentará la evidencia futura', interpretBody: 'La investigación de señales mostrará expectativa neta, incertidumbre, costes, cobertura de muestra, tasa de aciertos/payoff/PF, MFE/MAE, sensibilidad, concentración y evidencia contraria. No se reducirá a una sola puntuación.',
    optionBoundary: 'La evidencia de una acción no es rendimiento de opciones', optionBoundaryBody: 'Las opciones requieren una capa de expresión independiente con cotizaciones contemporáneas, IV, griegas, diferenciales, interés abierto, vencimiento y riesgo de eventos.',
  },
} as const;

function humanize(value: string): string {
  return value.split('_').join(' ');
}

function RecordList({ items }: { items: readonly string[] }): JSX.Element {
  return <ul className="research-record-list">{items.map((item) => <li key={item}>{humanize(item)}</li>)}</ul>;
}

export function QuantResearchLabPage(): JSX.Element {
  const { locale } = useI18n();
  const c = COPY[locale];
  const architecture = ARCHITECTURE_COPY[locale];
  const modelName = locale === 'zh' ? modelRecord.display_name_zh : modelRecord.display_name;
  const evaluation = modelRecord.evaluation_design;
  const engineering = modelRecord.method_engineering_evidence;
  const numberFormat = new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US');
  const decimalFormat = new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const correlationFormat = new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  const screeningMetricFormat = new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  const factorStats = [
    numberFormat.format(factorQualification.factor_count),
    numberFormat.format(factorQualification.complete_factor_vector_count),
    `${decimalFormat.format(factorQualification.coverage_percent)}%`,
    numberFormat.format(factorQualification.pairwise_correlation_count),
    numberFormat.format(factorQualification.near_duplicate_group_count),
  ];
  const factorScreeningV2Stats = [
    numberFormat.format(factorScreeningV2.formal_trial_count),
    numberFormat.format(factorScreeningV2.cumulative_trial_count),
    numberFormat.format(factorScreeningV2.development_session_count),
    numberFormat.format(factorScreeningV2.development_declared_path_count),
    `${factorScreeningV2.primary_horizon_sessions} / ${factorScreeningV2.decay_horizon_sessions.join('·')}`,
  ];
  const factorScreenStats = [
    numberFormat.format(factorScreening.formal_hypothesis_count),
    numberFormat.format(factorScreening.signal_session_count),
    numberFormat.format(factorScreening.observation_count),
    numberFormat.format(factorScreening.label_count),
    `${factorScreening.selected_alpha_count} / ${factorScreening.selected_risk_guard_count}`,
  ];
  const foundationValues = [
    numberFormat.format(1_255),
    `${numberFormat.format(1_253)} / ${numberFormat.format(1_255)}`,
    `${numberFormat.format(4_623)} / ${numberFormat.format(4_643)}`,
    `${numberFormat.format(219)} + ${numberFormat.format(83)}`,
    '4',
  ];
  const evaluationControls = [
    [numberFormat.format(evaluation.search_budget), c.controlLabels[0]],
    ['50 / 25 / 25', c.controlLabels[1]],
    [`${evaluation.purge_sessions} + ${evaluation.embargo_sessions}`, c.controlLabels[2]],
    [`${evaluation.cost_scenarios_bps_per_side.join(' / ')} bps`, c.controlLabels[3]],
    ['1×', c.controlLabels[4]],
  ];

  return <main className="research-page">
    <section className="research-hero">
      <div className="research-hero-copy"><span className="eyebrow">{c.eyebrow}</span><h1>{c.title}</h1><p>{c.subtitle}</p></div>
      <div className="research-status"><span>{c.status}</span><strong>{c.statusValue}</strong><p>{c.statusNote}</p></div>
      <div className="research-progress-copy"><strong>{c.coverage}</strong><span>{c.coverageNote}</span><small>{c.coverageBoundary}</small></div>
    </section>

    <section className="research-card research-architecture" aria-labelledby="research-architecture-title">
      <header><span>00</span><div><p>{architecture.eyebrow}</p><h2 id="research-architecture-title">{architecture.title}</h2><small>{architecture.note}</small></div></header>
      <div className="research-architecture-grid">
        {architecture.layers.map(([index, title, state, body], layerIndex) => <article className={layerIndex === 0 ? 'active' : 'locked'} key={title}><div><span>{index}</span><b>{state}</b></div><h3>{title}</h3><p>{body}</p></article>)}
      </div>
      <strong className="research-architecture-boundary">{architecture.boundary}</strong>
    </section>

    <section className="research-readiness" aria-labelledby="research-readiness-title"><header><span>01</span><h2 id="research-readiness-title">{c.readiness}</h2></header><div>{c.readinessItems.map(([name, state, body, tone]) => <article className={`research-readiness-${tone}`} key={name}><span>{state}</span><strong>{name}</strong><p>{body}</p></article>)}</div></section>

    <section className="research-card research-foundation" aria-labelledby="research-foundation-title">
      <header><span>02</span><div><h2 id="research-foundation-title">{c.foundation}</h2><p>{c.foundationNote}</p></div><b>{c.foundationBadge}</b></header>
      <div className="research-foundation-grid">
        {c.foundationItems.map(([name, state, body, tone], index) => <article className={`research-foundation-${tone}`} key={name}><div><strong>{foundationValues[index]}</strong><b>{state}</b></div><h3>{name}</h3><p>{body}</p></article>)}
      </div>
      <div className="research-foundation-controls"><strong>{c.foundationControls}</strong><div>{evaluationControls.map(([value, label]) => <span key={label}><b>{value}</b><small>{label}</small></span>)}</div></div>
      <p className="research-foundation-boundary">{c.foundationBoundary}</p>
    </section>

    <section className="research-card research-factor-qualification" aria-labelledby="research-factor-qualification-title">
      <header><span>03</span><div><h2 id="research-factor-qualification-title">{c.factorQualification}</h2><p>{c.factorQualificationNote}</p></div><b>{c.factorQualificationBadge}</b></header>
      <div className="research-factor-stats">
        {c.factorStats.map((label, index) => <article key={label}><span>{label}</span><strong>{factorStats[index]}</strong></article>)}
      </div>
      <p className="research-factor-coverage">{c.factorCoverageMeaning}</p>
      <div className="research-screen-verdict research-qualification-verdict">
        <article className={factorQualification.status === 'ready_for_screening_protocol_review' ? 'retained' : 'rejected'}><span>{c.factorVerdict}</span><strong>{c.factorVerdictValue}</strong><p>{c.factorVerdictBody}</p></article>
        <article className="retained"><span>{c.factorNext}</span><strong>{c.factorNextValue}</strong><p>{c.factorNextBody}</p></article>
      </div>
      <div className="research-factor-findings">
        <article><span>{c.factorRedundancy}</span><strong>{correlationFormat.format(Math.abs(factorQualification.maximum_absolute_weighted_same_session_spearman))}</strong><p>{c.factorRedundancyBody}</p></article>
        <article><span>{c.factorRoles}</span><div>{c.factorRoleValues.map((value) => <b key={value}>{value}</b>)}</div></article>
      </div>
      <details className="research-factor-details">
        <summary>{c.factorInspect}</summary>
        <div className="research-factor-definition-grid">{factorQualification.definitions.map((factor) => <article key={factor.factor_id}>
          <header><span>{FACTOR_TAXONOMY[locale][factor.family]}</span><strong>{FACTOR_NAMES[locale][factor.factor_id]}</strong><code>{factor.factor_id}</code></header>
          <dl>
            <div><dt>{c.factorRole}</dt><dd>{FACTOR_TAXONOMY[locale][factor.role]}</dd></div>
            <div><dt>{c.factorExpectation}</dt><dd>{FACTOR_TAXONOMY[locale][factor.expected_relationship]}</dd></div>
            <div><dt>{c.factorFormula}</dt><dd><code>{factor.exact_formula}</code></dd></div>
            <div><dt>{c.source}</dt><dd>{factor.source_fields.join(' · ')}</dd></div>
            <div><dt>{c.factorWindow}</dt><dd>{humanize(factor.source_window)}</dd></div>
            <div><dt>{c.cutoff}</dt><dd>{c.factorCutoffValue}</dd></div>
            <div><dt>{c.missing}</dt><dd>{c.factorMissingValue}</dd></div>
          </dl>
        </article>)}</div>
        <dl className="research-factor-reproduction">
          <div><dt>{c.factorWindow}</dt><dd>{factorQualification.first_session} → {factorQualification.last_session}</dd></div>
          <div><dt>catalog fingerprint</dt><dd><code>{factorQualification.catalog_fingerprint}</code></dd></div>
          <div><dt>protocol fingerprint</dt><dd><code>{factorQualification.protocol_fingerprint}</code></dd></div>
          <div><dt>report fingerprint</dt><dd><code>{factorQualification.report_logical_fingerprint}</code></dd></div>
          <div><dt>report SHA-256</dt><dd><code>{factorQualification.report_sha256}</code></dd></div>
        </dl>
      </details>
      <div className="research-factor-limit"><strong>{c.factorLimits}</strong><p>{c.factorLimitsBody}</p></div>
    </section>

    <section className="research-card research-factor-qualification" aria-labelledby="research-factor-screening-v2-title">
      <header><span>04</span><div><h2 id="research-factor-screening-v2-title">{c.screeningV2}</h2><p>{c.screeningV2Note}</p></div><b>{c.screeningV2Badge}</b></header>
      <div className="research-factor-stats research-screen-stats">
        {c.screeningV2Stats.map((label, index) => <article key={label}><span>{label}</span><strong>{factorScreeningV2Stats[index]}</strong></article>)}
      </div>
      <div className="research-screen-verdict">
        <article className="retained"><span>{c.screeningV2State}</span><strong>{c.screeningV2StateValue}</strong><p>{c.screeningV2StateBody}</p></article>
        <article className="retained"><span>{c.screeningV2Selection}</span><strong>{c.screeningV2SelectionValue}</strong><p>{c.screeningV2SelectionBody}</p></article>
      </div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.screeningV2Inspect}</summary>
        <div className="research-screen-protocol">
          <article><strong>{FACTOR_TAXONOMY[locale].candidate_alpha}</strong><ul className="research-record-list">{factorScreeningV2.alpha_factor_ids.map((factorId) => <li key={factorId}>{FACTOR_NAMES[locale][factorId]}</li>)}</ul></article>
          <article><strong>{FACTOR_TAXONOMY[locale].risk_guard}</strong><ul className="research-record-list">{factorScreeningV2.risk_guard_factor_ids.map((factorId) => <li key={factorId}>{FACTOR_NAMES[locale][factorId]}</li>)}</ul></article>
        </div>
        <div className="research-screen-protocol"><article><strong>{c.screeningV2Protocol}</strong><p>{c.screeningV2ProtocolBody}</p></article><article><strong>{c.screeningV2Limits}</strong><p>{c.screeningV2LimitsBody}</p></article></div>
        <dl className="research-factor-reproduction">
          <div><dt>Development window</dt><dd>{factorScreeningV2.first_development_signal_session} → {factorScreeningV2.last_development_signal_session}</dd></div>
          <div><dt>incremental control</dt><dd><code>{factorScreeningV2.incremental_baseline_factor_id}</code></dd></div>
          <div><dt>protocol fingerprint</dt><dd><code>{factorScreeningV2.protocol_fingerprint}</code></dd></div>
          <div><dt>prior ledger</dt><dd><code>{factorScreeningV2.prior_ledger_fingerprint}</code></dd></div>
          <div><dt>registered ledger</dt><dd><code>{factorScreeningV2.registered_ledger_fingerprint}</code></dd></div>
        </dl>
      </details>
    </section>

    <section className="research-card research-factor-screening" aria-labelledby="research-factor-screening-title">
      <header><span>05</span><div><h2 id="research-factor-screening-title">{c.factorScreen}</h2><p>{c.factorScreenNote}</p></div><b>{c.factorScreenBadge}</b></header>
      <div className="research-factor-stats research-screen-stats">
        {c.factorScreenStats.map((label, index) => <article key={label}><span>{label}</span><strong>{factorScreenStats[index]}</strong></article>)}
      </div>
      <div className="research-screen-verdict">
        <article className="rejected"><span>{c.factorScreenOutcome}</span><strong>0 / 5 Alpha</strong><p>{c.factorScreenOutcomeBody}</p></article>
        <article className="retained"><span>{c.factorScreenSelected}</span><strong>{FACTOR_NAMES[locale].rolling_maximum_drawdown_10s}</strong><p>{c.factorScreenSelectedBody}</p></article>
      </div>
      <h3 className="research-screen-decision-title">{c.factorScreenDecisions}</h3>
      <div className="research-screen-decisions">
        {factorScreening.decisions.map((decision) => <article className={decision.status === 'selected_model_candidate' ? 'retained' : 'rejected'} key={decision.factor_id}>
          <header><div><span>{FACTOR_TAXONOMY[locale][decision.role]}</span><strong>{FACTOR_NAMES[locale][decision.factor_id]}</strong></div><b>{decision.status === 'selected_model_candidate' ? c.factorScreenPassed : c.factorScreenRejected}</b></header>
          <dl>
            <div><dt>{c.factorScreenDecisionLabels[0]}</dt><dd>{screeningMetricFormat.format(decision.robust_effect)}</dd></div>
            <div><dt>{c.factorScreenDecisionLabels[1]}</dt><dd>{screeningMetricFormat.format(decision.robust_lower_bound)}</dd></div>
            <div><dt>{c.factorScreenDecisionLabels[2]}</dt><dd>{screeningMetricFormat.format(decision.holm_adjusted_p_value)}</dd></div>
            <div><dt>{c.factorScreenDecisionLabels[3]}</dt><dd>{numberFormat.format(decision.failed_gate_count)}</dd></div>
          </dl>
        </article>)}
      </div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.factorScreenInspect}</summary>
        <div className="research-screen-protocol"><article><strong>{c.factorScreenProtocol}</strong><p>{c.factorScreenProtocolBody}</p></article><article><strong>{c.factorScreenLimits}</strong><p>{c.factorScreenLimitsBody}</p></article></div>
        <dl className="research-factor-reproduction">
          <div><dt>Development window</dt><dd>{factorScreening.first_signal_session} → {factorScreening.last_signal_session}</dd></div>
          <div><dt>protocol fingerprint</dt><dd><code>{factorScreening.protocol_fingerprint}</code></dd></div>
          <div><dt>report fingerprint</dt><dd><code>{factorScreening.report_logical_fingerprint}</code></dd></div>
          <div><dt>report SHA-256</dt><dd><code>{factorScreening.report_sha256}</code></dd></div>
          <div><dt>implementation revision</dt><dd><code>{factorScreening.implementation_revision}</code></dd></div>
        </dl>
      </details>
    </section>

    <section className="research-card research-engineering-evidence" aria-labelledby="research-engineering-title">
      <header><span>06</span><div><h2 id="research-engineering-title">{c.engineering}</h2><p>{c.engineeringNote}</p></div><b>{c.engineeringBadge}</b></header>
      <ol className="research-engineering-rail">{c.engineeringStages.map((stage, index) => <li className={index < 3 ? 'done' : 'blocked'} key={stage}><i>{index < 3 ? '✓' : '!'}</i><strong>{stage}</strong><small>{index < 3 ? c.verified : c.blockedState}</small></li>)}</ol>
      <div className="research-engineering-stats">
        {[[c.declaredSessions, engineering.session_count], [c.completeSessions, engineering.complete_feature_session_count], [c.declaredPaths, engineering.expected_path_count], [c.computablePaths, engineering.complete_observation_count], [c.excludedPaths, engineering.excluded_path_count]].map(([label, value]) => <article key={label}><span>{label}</span><strong>{numberFormat.format(Number(value))}</strong></article>)}
      </div>
      <p className="research-engineering-meaning"><strong>{locale === 'es' ? '95,38 %' : '95.38%'}</strong>{c.coverageMeaning}</p>
      <div className="research-engineering-boundary"><strong>{c.proxyBoundary}</strong><p>{c.proxyBody}</p></div>
      <div className="research-program-outcome"><strong>{architecture.prior}</strong><p>{architecture.priorBody}</p></div>
    </section>

    <section className="research-boundary-grid"><article><span>{c.owner}</span><strong>{c.ownerValue}</strong></article><article><span>{c.boundary}</span><p>{c.boundaryBody}</p></article></section>

    <section className="research-card research-model-registry" aria-labelledby="research-model-title">
      <header><span>07</span><div><h2 id="research-model-title">{c.registry}</h2><p>{c.featured}</p></div></header>
      <article className="research-model-summary">
        <div className="research-model-heading"><div><span>{modelRecord.model_id}</span><h3>{modelName}</h3><p>{modelRecord.hypothesis}</p></div><div className="research-model-badges"><b>{c.methodOnly}</b><b>{c.noCandidate}</b><b>{c.notAssessed}</b></div></div>
        <dl className="research-model-facts">
          <div><dt>{c.version}</dt><dd>{modelRecord.model_version}</dd></div>
          <div><dt>{c.lifecycleState}</dt><dd>{humanize(modelRecord.lifecycle_state)}</dd></div>
          <div><dt>{c.evidence}</dt><dd>{humanize(modelRecord.evidence_scope)}</dd></div>
          <div><dt>{c.applicability}</dt><dd>{humanize(modelRecord.applicability_state)}</dd></div>
          <div><dt>{c.oos}</dt><dd>{modelRecord.out_of_sample_observation_count}</dd></div>
        </dl>
        <div className="research-model-balance"><p><strong>{c.strength}</strong>{modelRecord.primary_strength}</p><p><strong>{c.weakness}</strong>{modelRecord.primary_weakness}</p></div>
        <p className="research-next-decision"><strong>{c.nextDecision}</strong>{modelRecord.next_required_decision}</p>
      </article>

      <details className="research-model-details">
        <summary>{c.inspect}</summary>
        <div className="research-record-section"><h3>{c.logic}</h3><dl className="research-record-ledger">
          {[[c.decisionUse,modelRecord.decision_use],[c.hypothesis,modelRecord.hypothesis],[c.rationale,modelRecord.economic_rationale],[c.signal,modelRecord.signal_rule],[c.ranking,modelRecord.ranking_rule]].map(([term, value]) => <div key={term}><dt>{term}</dt><dd>{value}</dd></div>)}
        </dl></div>

        <div className="research-record-section"><h3>{c.features}</h3><div className="research-feature-grid">{modelRecord.feature_disclosures.map((feature) => <article key={feature.feature_id}><header><span>{humanize(feature.role)}</span><strong>{humanize(feature.feature_id)}</strong></header><code>{feature.exact_formula}</code><dl><div><dt>{c.source}</dt><dd>{feature.requirement_source_family} → {feature.raw_source_families.join(' + ')} · {feature.source_fields.join(', ')}</dd></div><div><dt>{c.cutoff}</dt><dd>{humanize(feature.availability_cutoff)}</dd></div><div><dt>{c.lookback}</dt><dd>{feature.lookback_sessions} {c.sessions}</dd></div><div><dt>{c.transform}</dt><dd>{humanize(feature.transform)}</dd></div><div><dt>{c.expected}</dt><dd>{humanize(feature.expected_direction)}</dd></div><div><dt>{c.missing}</dt><dd>{humanize(feature.missingness_rule)}</dd></div></dl></article>)}</div></div>

        <div className="research-record-section"><h3>{c.parameters}</h3><div className="research-parameter-records">{modelRecord.parameter_disclosures.map((parameter) => <article key={parameter.parameter_id}><strong>{humanize(parameter.parameter_id)}</strong><p>{parameter.rationale}</p><span>{c.candidates}</span><code>{parameter.candidate_values.join(' | ')}</code><small>{c.selection}: {humanize(parameter.selection_scope)}</small></article>)}</div></div>

        <div className="research-record-section"><h3>{c.evaluation}</h3><dl className="research-record-ledger">
          <div><dt>{c.split}</dt><dd>{humanize(evaluation.split_rule)} · warm-up {evaluation.warmup_sessions} · purge {evaluation.purge_sessions} · embargo {evaluation.embargo_sessions}</dd></div>
          <div><dt>{c.outcome}</dt><dd>{humanize(evaluation.primary_outcome)}</dd></div>
          <div><dt>{c.secondary}</dt><dd>{evaluation.secondary_outcomes.map(humanize).join(' · ')}</dd></div>
          <div><dt>{c.benchmark}</dt><dd>{humanize(evaluation.benchmark)}</dd></div>
          <div><dt>{c.control}</dt><dd>{humanize(evaluation.control)}</dd></div>
          <div><dt>{c.inference}</dt><dd>{humanize(evaluation.inference_method)}</dd></div>
          <div><dt>{c.multiplicity}</dt><dd>{humanize(evaluation.multiplicity_method)} · budget {evaluation.search_budget}</dd></div>
          <div><dt>{c.costs}</dt><dd>{evaluation.cost_scenarios_bps_per_side.join(' / ')} bps per side</dd></div>
          <div><dt>{c.holdout}</dt><dd>{humanize(evaluation.holdout_rule)}</dd></div>
          <div><dt>{c.portfolio}</dt><dd>{evaluation.portfolio_construction_defined ? c.undefined : c.falseValue}</dd></div>
        </dl></div>

        <div className="research-record-section"><h3>{c.gates}</h3><RecordList items={modelRecord.decision_gates} /></div>
        <div className="research-record-section research-record-risk"><h3>{c.failure}</h3><div><article><strong>{c.counter}</strong><RecordList items={modelRecord.counterevidence_requirements} /></article><article><strong>{c.invalidation}</strong><RecordList items={modelRecord.invalidation_conditions} /></article><article><strong>{c.blockers}</strong><RecordList items={modelRecord.blocker_codes} /></article><article><strong>{c.risks}</strong><RecordList items={modelRecord.risk_disclosure_codes} /></article></div></div>
        <div className="research-record-section"><h3>{c.reproduction}</h3><dl className="research-fingerprint-ledger">
          <div><dt>contract</dt><dd><code>{modelRecord.contract_version}</code></dd></div><div><dt>record</dt><dd><code>{modelRecord.logical_fingerprint}</code></dd></div><div><dt>method contract</dt><dd><code>{modelRecord.source_method_contract_version}</code></dd></div><div><dt>method</dt><dd><code>{modelRecord.source_method_fingerprint}</code></dd></div><div><dt>diagnostic contract</dt><dd><code>{engineering.report_contract_version}</code></dd></div><div><dt>diagnostic report</dt><dd><code>{engineering.report_logical_fingerprint}</code></dd></div><div><dt>experiment ID</dt><dd><code>{modelRecord.source_experiment_id}</code></dd></div><div><dt>experiment</dt><dd><code>{modelRecord.source_experiment_fingerprint}</code></dd></div><div><dt>features</dt><dd><code>{modelRecord.input_feature_fingerprint}</code></dd></div><div><dt>evaluation</dt><dd><code>{modelRecord.evaluation_policy_fingerprint}</code></dd></div><div><dt>implementation revision</dt><dd>{modelRecord.implementation_revision ?? modelRecord.implementation_revision_reason}</dd></div><div><dt>result publication</dt><dd>{modelRecord.result_publication_id ?? c.none}</dd></div>
        </dl></div>
      </details>
    </section>

    <section className="research-card research-lifecycle"><header><span>08</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>09</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
