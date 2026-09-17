import factorQualification from '../modelRecords/quant-research-factor-qualification-v2.json';
import discoveryCycle from '../modelRecords/quant-research-discovery-cycle-state-v2.json';
import multiAgentGovernance from '../modelRecords/quant-research-multi-agent-governance-v1.json';
import factorScreeningV2 from '../modelRecords/quant-research-factor-screening-v2.json';
import factorScreening from '../modelRecords/quant-research-factor-screening-v1.json';
import campaignThreeScreening from '../modelRecords/quant-research-campaign-three-screening-public-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const ARCHITECTURE_COPY = {
  en: {
    eyebrow: 'Current research architecture · three separate evidence layers',
    title: 'From measurement to a decision—without collapsing the evidence.',
    note: 'The research universe can expand over time. Every batch that reads outcomes remains finite, registered, and fully counted.',
    layers: [
      ['01', 'Factor Discovery', 'CURRENT · OUTCOME-BLIND INTAKE', 'Three finite campaigns are closed without candidate Alpha. All 17 trials remain counted; the next campaign must begin with a new deduplicated hypothesis set.'],
      ['02', 'Model Construction', 'LOCKED', 'Combine a small admitted factor set into an explainable rank, probability, distribution, or risk state. No model is preselected.'],
      ['03', 'Strategy Expression', 'LOCKED', 'Translate a locked model into entry, exit, holding, sizing, cost, capacity, and risk rules. Stock and option expressions remain separate.'],
    ],
    boundary: 'A factor is not a model. A model is not a strategy. A backtest is not Product authority.',
  },
  zh: {
    eyebrow: '当前研究架构 · 三层证据相互独立',
    title: '从测量到决策，每一层证据都保持独立。',
    note: '长期研究方向可以持续扩展；但每一批读取结果的实验都必须有限、预先登记并计入真实试验次数。',
    layers: [
      ['01', '因子发现层', '当前阶段 · 回到结果盲入口', '三批有限研究均在没有候选 Alpha 的状态下关闭。17项试验全部保留计数；下一批必须从新的去重假设开始。'],
      ['02', '模型构建层', '保持锁定', '用少量合格且非冗余的因子构建可解释排名、概率、分布或风险状态。目前没有预先指定模型。'],
      ['03', '策略表达层', '保持锁定', '把锁定模型转为入场、退出、持有、仓位、成本、容量与风险规则；股票和期权表达分开验证。'],
    ],
    boundary: '因子不是模型，模型不是策略，回测也不等于产品权限。',
  },
  es: {
    eyebrow: 'Arquitectura actual · tres capas de evidencia separadas',
    title: 'De la medición a la decisión, sin mezclar las capas de evidencia.',
    note: 'El universo de investigación puede ampliarse con el tiempo. Cada campaña que consulta resultados sigue siendo finita, registrada y contabilizada.',
    layers: [
      ['01', 'Descubrimiento de factores', 'FASE ACTUAL · NUEVA ENTRADA SIN RESULTADOS', 'Tres campañas finitas se cerraron sin Alpha candidato. Las 17 pruebas siguen contabilizadas; la siguiente campaña debe comenzar con hipótesis nuevas y deduplicadas.'],
      ['02', 'Construcción del modelo', 'BLOQUEADA', 'Combina un pequeño conjunto de factores admitidos en un rango, probabilidad, distribución o estado de riesgo explicable. No hay un modelo preseleccionado.'],
      ['03', 'Expresión de estrategia', 'BLOQUEADA', 'Convierte un modelo bloqueado en reglas de entrada, salida, tenencia, tamaño, costes, capacidad y riesgo. Acciones y opciones se validan por separado.'],
    ],
    boundary: 'Un factor no es un modelo. Un modelo no es una estrategia. Un backtest no concede autoridad al producto.',
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

const CAMPAIGN_THREE_DECISION_NAMES: Record<string, Record<string, string>> = {
  en: {
    breakout_breadth: 'Breakout position × market breadth',
    volume_participation: 'Volume surprise × market participation',
    residual_risk_volatility: 'Residual risk × broad volatility',
  },
  zh: {
    breakout_breadth: '突破位置 × 市场广度',
    volume_participation: '成交额异常 × 市场参与度',
    residual_risk_volatility: '残差风险 × 广泛市场波动',
  },
  es: {
    breakout_breadth: 'Posición de ruptura × amplitud del mercado',
    volume_participation: 'Sorpresa de volumen × participación del mercado',
    residual_risk_volatility: 'Riesgo residual × volatilidad amplia',
  },
};

const COPY = {
  en: {
    eyebrow: 'Factor, model, and strategy research · governed registry',
    title: 'Quant Research Lab',
    subtitle: 'The authoritative record of what is measured, what is modeled, how it becomes a strategy, and where the evidence fails.',
    status: 'FACTOR DISCOVERY · THREE CAMPAIGNS CLOSED', statusValue: 'NO CANDIDATE ALPHA · INTAKE REOPENED',
    statusNote: 'Campaign Three completed one frozen Development screen and a byte-identical replay. Both Alpha interactions and the risk guard failed; no model or strategy was opened.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    submission: 'Submit a falsifiable factor or strategy hypothesis for independent registration and testing under the same governed workflow. If an idea ultimately enters a usable model and future commercial use, WH Alpha will contact the contributor and report the outcome.',
    submissionContact: 'Contact',
    readiness: 'Evidence ladder', readinessItems: [
      ['Three-layer architecture', 'ACCEPTED', 'Factor Discovery, Model Construction, and Strategy Expression now have separate version and evidence boundaries.', 'met'],
      ['Cumulative research ledger', '17 TRIALS · ALL CLOSED', 'All trials from three campaigns remain permanently counted. Ledger edition 5 records outcomes and authority; it is not a model version.', 'met'],
      ['Second factor campaign', 'CLOSED', 'Its eight exact definitions covered continuation, reversal, return timing, defensive state, liquidity applicability, and downside risk. It produced no candidate Alpha.', 'met'],
      ['V2 data qualification', 'PASSED', 'The report and replay are byte-identical: 98.59% complete vectors, 267 eligible sessions, and all eight definitions clear the frozen gates.', 'met'],
      ['Development screen', 'COMPLETED', 'Four Alpha trials failed. Two risk guards passed, but the no-Alpha prerequisite prevents selection into Model Construction.', 'met'],
      ['Exact reproduction', 'VERIFIED', 'The independent replay returned the identical reviewed result with zero canonical, Production, or external writes.', 'met'],
      ['Reusable research inputs', '1 PANEL QUALIFIED', 'The exactly replayed Market-State panel is registered for outcome-blind reuse. Outcome-bearing panels and all new result access remain closed.', 'met'],
      ['Third factor campaign', 'CLOSED · NO ALPHA', 'The formal result and exact replay match. Both Alpha interactions and the risk guard failed the frozen screen; no model input was selected.', 'met'],
      ['Model, strategy & Product', 'LOCKED', 'No predictive model, strategy expression, Candidate authority, or option-performance claim exists.', 'locked'],
    ],
    cycle: 'Renewable factor-discovery loop', cycleNote: 'The research program may continue indefinitely. Every campaign inside it is finite, deduplicated, preregistered, replayed, and permanently counted.', cycleBadge: 'CONTINUOUS SYSTEM · BOUNDED CAMPAIGNS',
    cycleStats: ['Operating mode', 'Current stage', 'Completed campaigns', 'Formal trials recorded', 'Active campaign'], cycleStatValues: ['RENEWABLE', 'OUTCOME-BLIND INTAKE', '3', '17', 'NONE'],
    cycleStages: [
      ['01', 'Propose & deduplicate', 'COMPLETED', 'Five ideas were retained; four advanced and one near-duplicate stopped before any outcome access.'],
      ['02', 'Build without outcomes', 'COMPLETED', 'The exact 106-session report and independent replay matched. Three designs qualified; one Alpha design stopped before outcomes.'],
      ['03', 'Register the finite test', 'COMPLETED', 'Two Alpha trials and one risk trial, including outcomes, costs, multiplicity, gates, caps, and stopping rules, are frozen in the cumulative ledger.'],
      ['04', 'Authorize, evaluate & replay', 'COMPLETED', 'The one formal run and exact replay matched. All three trials failed; Validation and Holdout remained sealed.'],
      ['05', 'Close, count & return', 'CURRENT', 'Ledger edition 5 retains all 17 consumed trials and returns the program to a new outcome-blind hypothesis intake.'],
    ],
    cycleCurrent: 'Current position', cycleCurrentValue: 'INTAKE · NO ACTIVE CAMPAIGN', cycleCurrentBody: 'Campaign Three is closed. The next campaign must begin with a new falsifiable hypothesis set deduplicated against all 17 consumed trials.',
    cycleInfrastructure: 'Stopped before outcomes', cycleInfrastructureValue: '1 ALPHA DESIGN REJECTED', cycleInfrastructureBody: 'Defensive resilience lacked balanced natural-zero state support and was overly concentrated, including in the first half. Its threshold was not moved after inspection.',
    cycleContinuity: 'Next boundary', cycleContinuityValue: 'NEW FINITE CAMPAIGN', cycleContinuityBody: 'No further Campaign Three outcome access exists. A successor requires new intake, data admission, qualification, preregistration, and separate authorization.',
    cycleInspect: 'Inspect deduplication, budget, isolation, and pause rules',
    cycleGuardTitles: ['Duplicate identity', 'Finite trial budget', 'Stage isolation', 'Automatic pause'],
    cycleGuardBodies: [
      'Novelty is checked across mechanism, information set and cutoff, formula, Universe, horizon, parameter neighborhood, and related hypothesis family.',
      'Factor and interaction count, parameter variants, horizons, hypothesis families, multiplicity, selection cap, and stopping rule must all be frozen.',
      'Idea and qualification stages cannot read outcomes. Development access begins only for a newly registered campaign; Validation and Holdout remain separate.',
      'Lineage mismatch, stage leakage, trial-budget breach, replay failure, or sealed-partition breach stops the affected campaign without erasing prior work.',
    ],
    agentPilot: 'Stage-isolated research team', agentPilotNote: 'The supervised multi-Agent pilot completed qualification, preregistration, one formal Development screen, exact replay, adversarial review, and ledger close.', agentPilotBadge: 'CAMPAIGN CLOSED · REPLAY MATCHED',
    agentStats: ['Market-state qualification', 'Input replay', 'Frozen decisions', 'Validation / Holdout'], agentStatValues: ['PASSED · 267 / 287', 'MATCHED · 106 / 106', '3 · REJECTED', 'SEALED'],
    agentStages: [
      ['01', 'Independent reviews', 'COMPLETED', 'Governance, methodology, and implementation reviewers found and corrected real pre-run defects.'],
      ['02', 'Market-state qualification', 'COMPLETED', 'All 287 sessions were evaluated; reconstructed breadth was jointly available for 267 sessions and the independent canonical-byte replay matched.'],
      ['03', 'Hypotheses and input review', 'COMPLETED', 'Five cards were frozen; three designs passed exact outcome-blind qualification and one accepted Alpha design was rejected.'],
      ['04', 'Protocol and trial accounting', 'COMPLETED', 'The three qualified trials and every evaluation and stopping rule are fixed in cumulative ledger edition 4.'],
      ['05', 'Development evaluation', 'COMPLETED', 'The authorized formal screen rejected all three frozen trials without changing any gate.'],
      ['06', 'Replay, red team, and human route', 'COMPLETED', 'The exact replay matched, the ledger closed, and downstream model authority remained locked.'],
    ],
    agentRoles: 'Role and access map', agentRoleNames: ['Research controller', 'Data & evidence', 'Hypothesis review', 'Implementation', 'Evaluation', 'Red team', 'Approval & publication'],
    agentBoundary: 'What this does not mean', agentBoundaryBody: 'This is not an unattended Alpha miner. No new return trial, model, Validation, Holdout, Candidate authority, deployment, broker access, or trading authority is open.',
    agentInspect: 'Inspect role isolation, serial gates, and shared accounting',
    campaignThree: 'Completed Development Screen · Campaign Three', campaignThreeNote: 'The question, sample, interaction regressions, block inference, multiplicity, and stopping rule were frozen before outcomes. The independent replay produced the identical report.', campaignThreeBadge: 'CLOSED · EXACT REPLAY',
    campaignThreeStats: ['Formal trials', 'Cumulative trials', 'Signal sessions', 'Observations', 'Forward labels'],
    campaignThreeAlpha: 'Candidate Alpha decision', campaignThreeAlphaValue: '0 / 2 admitted', campaignThreeAlphaBody: 'Both interactions had negative primary slopes and negative second-half slopes. Neither passed bootstrap lower bounds or family-wise control.',
    campaignThreeRisk: 'Risk-guard decision', campaignThreeRiskValue: '0 / 1 qualified', campaignThreeRiskBody: 'The pooled slope was positive, but the second half turned negative and both registered lower bounds crossed zero. It was rejected rather than rescued.',
    campaignThreeDecisions: 'All three frozen decisions', campaignThreeDecisionLabels: ['Interaction beta', 'Second-half beta', 'Worst 90% lower bound', 'Holm p', 'Failed gates'], campaignThreeRejected: 'Rejected',
    campaignThreeBoundary: 'What the result authorizes', campaignThreeBoundaryBody: 'Nothing downstream. Model Construction, Validation, Holdout, Candidate activation, option claims, publication authority, and trading remain closed.',
    foundation: 'Research foundation snapshot', foundationNote: 'Verified, versioned evidence already built on the research workstation. Each item states both its useful scope and its limit.', foundationBadge: 'EVIDENCE REVIEWED · 15 SEP 2026',
    foundationItems: [
      ['Five-year market base', 'DEPTH COMPLETE', 'Contiguous EOD price and stable-identity depth are complete.', 'verified'],
      ['Historical membership', 'RECONSTRUCTED', '1,250 sessions are reconstructed and three are prospective; reconstructed history is not as operated.', 'qualified'],
      ['Corporate actions', 'PARTIAL EVIDENCE', '4,623 of 4,643 first-strategy exposures have exact event-date assignments; absence neutrality is not proven.', 'qualified'],
      ['Lifecycle & terminal', 'BOUNDED REFERENCES', 'All 302 five-session paths have either exact or finite-interval references; references are not strategy outcomes.', 'qualified'],
      ['Point-in-time fundamentals', 'ENGINEERING PILOT', 'Four registered SEC query paths and four strict as-operated projection sessions exist; this is engineering evidence only.', 'qualified'],
    ],
    foundationControls: 'Campaign Three controls already frozen', controlLabels: ['Registered trials', 'Chronological halves', 'Bootstrap block lengths', 'Cost scenarios per side', 'Formal run / exact replay'],
    foundationBoundary: 'These facts are not blended into one readiness percentage. A weak mandatory evidence family keeps performance research locked.',
    factorQualification: 'Factor qualification V2', factorQualificationNote: 'The eight-factor catalog was calculated twice over the same frozen workstation population. The exact replay measures source and implementation fitness only; it never reads future returns.', factorQualificationBadge: 'PASSED · EXACT REPLAY',
    factorStats: ['Registered factors', 'Complete vectors', 'Coverage', 'Pair checks', 'Near-duplicate groups'],
    factorCoverageMeaning: '431,249 of 437,402 declared paths produced complete eight-factor vectors. The 6,153 incomplete paths remain explicit; none was zero-filled. Availability reached 98.59% across 267 eligible sessions, split 123 / 144 across the frozen chronological halves.',
    factorRedundancy: 'Strongest same-session relationship', factorRedundancyBody: 'The largest absolute weighted Spearman relationship was 0.8942 between the two risk guards. No pair met the full near-duplicate rule. This passes a data-qualification test; it says nothing about predictive value.',
    factorRoles: 'Catalog roles', factorRoleValues: ['4 candidate Alpha measurements', '1 setup conditioner', '1 applicability input', '2 risk guards'],
    factorInspect: 'Inspect all eight registered definitions and exact formulas',
    factorRole: 'Role', factorFormula: 'Exact formula', factorWindow: 'Point-in-time source window', factorExpectation: 'Registered relationship', source: 'Source', cutoff: 'Availability cutoff', missing: 'Missingness',
    factorCutoffValue: 'completed session close → next session open', factorMissingValue: 'explicit unavailable · never zero-fill',
    factorVerdict: 'What V2 earned', factorVerdictValue: '8 / 8 eligible for protocol review', factorVerdictBody: 'Four candidate Alpha measurements, one setup conditioner, one applicability input, and two risk guards cleared coverage, chronology, variation, tie, and redundancy gates. They are measurements awaiting a registered outcome test—not admitted factors.',
    factorNext: 'Qualification outcome', factorNextValue: 'SCREEN COMPLETED · SEE DECISION BELOW', factorNextBody: 'All eight measurements were eligible to be tested, not presumed useful. The completed screen rejected every candidate Alpha and preserved the qualification record unchanged.',
    factorLimits: 'Qualification limits', factorLimitsBody: 'Membership is reconstructed rather than as operated; historical classifications and broad Regime diversity remain unproven; daily bars do not observe spreads or signed order flow; and split-neutral absence remains a disclosed source limitation despite the qualified reconstruction.',
    screeningV2: 'Completed Development Screen · Factor Catalog V2', screeningV2Note: 'This is the immutable result of the preregistered question, not a backtest selected for appearance. The exact replay matched every result and count.', screeningV2Badge: 'CLOSED · EXACT REPLAY',
    screeningV2Stats: ['Formal trials', 'Cumulative trials', 'Signal sessions', 'Observations', 'Forward labels'],
    screeningV2State: 'Candidate Alpha decision', screeningV2StateValue: '0 / 4 admitted', screeningV2StateBody: 'All four candidate-Alpha measurements failed at least one frozen gate. Their formulas and thresholds cannot be repaired after seeing these outcomes.',
    screeningV2Selection: 'Risk evidence', screeningV2SelectionValue: '2 qualified · 0 selected', screeningV2SelectionBody: 'Both downside-risk guards passed their registered gates. They remain useful evidence, but neither becomes a model input because no candidate Alpha survived.',
    screeningV2Decisions: 'All six registered decisions', screeningV2DecisionLabels: ['Robust effect', '90% lower bound', 'Holm p', 'Failed gates'], screeningV2Risk: 'Risk evidence · not selected', screeningV2Rejected: 'Rejected',
    screeningV2Next: 'Successor campaign result', screeningV2NextValue: '3 TRIALS · ALL REJECTED', screeningV2NextBody: 'Campaign Three completed its frozen screen and exact replay. It produced no candidate Alpha, no qualified risk guard, and no model input.',
    screeningV2Inspect: 'Inspect the frozen protocol, lineage, and report identity', screeningV2Protocol: 'Frozen evaluation', screeningV2ProtocolBody: '3-session primary stock outcome · 1/5-session decay · same-session ranks · 10,000 circular five-session block-bootstrap replications · unchanged V1 gates · Holm within 4-Alpha and 2-risk families · 0/10/25/50 bps-per-side diagnostics.', screeningV2Limits: 'What remains closed', screeningV2LimitsBody: 'Historical sector neutralization and broad Regime diversity remain unavailable. This is reconstructed Development evidence only; Validation, Holdout, model, strategy, Candidate, options, and trading remain locked.',
    factorScreen: 'Historical Development Screen · Factor Catalog V1', factorScreenNote: 'Retained failed research, not the current campaign. Its finite protocol was committed before outcome access and executed twice against the same Development cohort; no candidate Alpha passed.', factorScreenBadge: 'RETAINED FAILURE · EXACT REPLAY',
    factorScreenStats: ['Formal hypotheses', 'Signal sessions', 'Observations', 'Forward labels', 'Selected Alpha / risk'],
    factorScreenOutcome: 'The honest result', factorScreenOutcomeBody: 'Zero candidate-Alpha factors passed the frozen gates. Factor Catalog V1 therefore closes without a predictive model and cannot change Stock Candidates.',
    factorScreenSelected: 'Evidence retained', factorScreenSelectedBody: '10-session rolling maximum drawdown passed as a downside-risk guard: robust rank effect 0.2540, 90% lower bound 0.2322, Holm-adjusted p 0.0003. It may constrain a later model; it is not Alpha by itself.',
    factorScreenDecisions: 'All eight registered decisions', factorScreenDecisionLabels: ['Robust effect', '90% lower bound', 'Holm p', 'Failed gates'], factorScreenPassed: 'Risk guard retained', factorScreenRejected: 'Rejected',
    factorScreenInspect: 'Inspect protocol, custody, limits, and exact report identity',
    factorScreenProtocol: 'Frozen evaluation', factorScreenProtocolBody: 'Primary horizon: 3 sessions · decay diagnostics: 1 and 5 · 10,000 circular five-session block-bootstrap replications · 90% intervals · Holm family-wise control · 0/10/25/50 bps per-side cost diagnostics.',
    factorScreenLimits: 'Interpretation boundary', factorScreenLimitsBody: 'Development only; reconstructed membership; 106 signal sessions; historical classification and broad Regime diversity not proven; fixed costs are scenarios, not execution calibration. Validation and Holdout were never opened.',
    owner: 'Research ownership', ownerValue: 'WH Alpha personal quantitative research',
    boundary: 'Authority boundary', boundaryBody: 'The Lab owns factor, model, expression, and evaluation evidence. Stock Candidates may later consume only the small reviewed set of explicitly activated expressions; there is no permanent model-count limit.',
    lifecycle: 'Three-layer promotion path', stages: ['Factor discovery', 'Model construction', 'Strategy expression', 'Validation', 'Sealed holdout', 'Shadow', 'Activation'],
    current: 'Current', locked: 'Locked', blocked: 'Blocked by evidence',
    results: 'Current research ledger', resultsNote: 'Failures remain visible; no synthetic substitute and no implied active performance',
    resultCards: [['First factor campaign', 'Closed · no candidate Alpha'], ['Second factor campaign', 'Closed · no candidate Alpha'], ['Third factor campaign', 'Closed · no candidate Alpha'], ['Active models / strategies', 'None / none']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '因子、模型与策略研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '权威记录测量什么、如何建模、怎样形成策略，以及证据在哪一层失败，而不是只陈列漂亮回测。',
    status: '因子发现 · 三批研究均已关闭', statusValue: '无候选 Alpha · 回到结果盲入口',
    statusNote: '第三批已完成一次冻结的开发期筛选和逐字节一致的精确重放。2项 Alpha 交互与1项风险护栏全部失败，没有开放模型或策略。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    submission: '欢迎提交可证伪的因子或策略假设。WH Alpha 将按统一研究流程独立登记、测试并保留失败记录；若建议最终进入可用模型并产生未来商业用途，将联系贡献者并反馈结果。',
    submissionContact: '联系',
    readiness: '证据阶梯', readinessItems: [
      ['三层研究架构', '已生效', '因子发现、模型构建与策略表达现在拥有相互独立的版本和证据边界。', 'met'],
      ['累计研究账本', '共17项 · 全部关闭', '三批研究的全部试验永久计数。账本第5版记录结果和权限，不是第5个模型。', 'met'],
      ['第二批因子研究', '已关闭', '8项精确定义覆盖延续、反转、收益时段、防御状态、流动性适用性与下行风险；最终没有产生候选 Alpha。', 'met'],
      ['V2 数据资格诊断', '已通过', '报告与重放逐字节一致：完整向量覆盖率98.59%，267个合格交易日，8项定义全部通过冻结门槛；6,491条五年拆股来源与旧正式证据重叠冲突为零。', 'met'],
      ['开发期筛选', '已完成', '4项 Alpha 全部失败；2项风险护栏通过，但因缺少 Alpha 而不能进入模型构建。', 'met'],
      ['精确复现', '已验证', '独立重放得到完全相同且经过审阅的结果，并保持正式数据、生产和外部请求写入为零。', 'met'],
      ['可复用研究输入', '1个面板已合格', '精确重放的市场状态面板已登记为结果盲复用输入；结果型面板和新的结果访问仍全部关闭。', 'met'],
      ['第三批因子研究', '已关闭 · 无 Alpha', '正式结果与精确重放一致。2项 Alpha 交互和1项风险护栏均未通过冻结筛选，没有选择任何模型输入。', 'met'],
      ['模型、策略与产品', '锁定', '目前仍没有预测模型、策略表达、个股候选权限或期权绩效主张。', 'locked'],
    ],
    cycle: '可持续因子发现循环', cycleNote: '整个研究计划可以持续迭代，但其中每一批研究都必须有限、去重、预登记、精确复现并永久计入试验账本。', cycleBadge: '持续研究系统 · 单批次有边界',
    cycleStats: ['运行模式', '当前阶段', '已完成批次', '累计登记试验', '当前批次'], cycleStatValues: ['持续循环', '结果盲假设入口', '3', '17', '无'],
    cycleStages: [
      ['01', '提出假设并去重', '已完成', '共保留5个想法；4个进入下一步，1个近重复想法在任何结果访问前停止。'],
      ['02', '不读取结果地构建', '已完成', '106个交易日的正式报告与独立重放完全一致；3项设计通过，1项 Alpha 在读取结果前停止。'],
      ['03', '登记有限检验', '已完成', '2项 Alpha 和1项风险试验连同结果、成本、重复检验、门槛、入选上限与停止规则，均已写入累计试验账本。'],
      ['04', '授权、评估与重放', '已完成', '一次正式运行与一次精确重放完全一致；3项试验全部失败，验证集与留出集始终密封。'],
      ['05', '关闭、记账并返回', '当前阶段', '累计账本第5版保留17项已消费试验，研究系统回到新的结果盲假设入口。'],
    ],
    cycleCurrent: '当前位置', cycleCurrentValue: '假设入口 · 无活动批次', cycleCurrentBody: '第三批已经关闭。下一批必须提出新的可证伪假设，并与全部17项已消费试验完成去重。',
    cycleInfrastructure: '读取结果前停止', cycleInfrastructureValue: '1项 Alpha 设计被拒绝', cycleInfrastructureBody: '防御韧性的自然零点状态支持不平衡且过度集中，前半段尤其不足；审查后没有移动阈值进行补救。',
    cycleContinuity: '下一道边界', cycleContinuityValue: '新的有限研究批次', cycleContinuityBody: '第三批不再允许读取更多结果。后续批次需要重新经过假设、数据准入、资格审查、预登记与单独授权。',
    cycleInspect: '查看去重、预算、隔离与暂停规则',
    cycleGuardTitles: ['重复身份', '有限试验预算', '阶段隔离', '自动暂停'],
    cycleGuardBodies: [
      '从经济机制、信息集合与截止时点、公式、Universe、周期、参数邻域及相关假设家族七个维度判断是否重复。',
      '因子与交互数量、参数变体、周期、假设家族、重复检验方法、入选上限和停止规则必须全部冻结。',
      '提出想法和资格诊断阶段不能读取结果；只有新批次完成登记后才能打开开发期结果，验证集与留出集继续独立隔离。',
      '来源谱系不一致、阶段泄漏、超出试验预算、重放失败或密封分区泄漏会立即停止受影响批次，但不会抹去已有研究。',
    ],
    agentPilot: '阶段隔离的研究协作组', agentPilotNote: '人工监督的多 Agent 试点已完成资格审查、预登记、一次正式开发期筛选、精确重放、反证审查与账本关闭。', agentPilotBadge: '批次已关闭 · 重放完全一致',
    agentStats: ['市场状态资格', '输入精确重放', '冻结决策', 'Validation / Holdout'], agentStatValues: ['通过 · 267 / 287', '完全一致 · 106 / 106', '3项 · 全部拒绝', '保持密封'],
    agentStages: [
      ['01', '独立审查', '已完成', '治理、方法和实现审查在真实运行前发现并修正了实质问题。'],
      ['02', '市场状态资格审查', '已完成', '287个交易日全部完成；重建宽度联合可用267日，独立规范字节重放完全一致。'],
      ['03', '假设与输入审查', '已完成', '5张假设卡已经冻结；3项设计通过精确结果盲资格审查，1项已接受 Alpha 设计被拒绝。'],
      ['04', '协议与试验记账', '已完成', '3项合格试验及全部评估和停止规则已经写入累计试验账本第4版。'],
      ['05', '开发期评估', '已完成', '获授权的正式筛选在不改变任何门槛的前提下拒绝了全部3项试验。'],
      ['06', '重放、反证与人工裁决', '已完成', '精确重放一致、累计账本关闭，下游模型权限继续锁定。'],
    ],
    agentRoles: '角色与访问权限', agentRoleNames: ['研究主控', '数据与证据', '假设审查', '实现', '评估', '反证', '审批与发布'],
    agentBoundary: '这不代表什么', agentBoundaryBody: '这不是无人监管的 Alpha 挖掘器。新的收益试验、模型、Validation、Holdout、候选权限、部署、券商或交易权限均未开放。',
    agentInspect: '查看角色隔离、串行阶段门与共享账本',
    campaignThree: '已完成开发期筛选 · 第三批研究', campaignThreeNote: '研究问题、样本、交互回归、区块推断、重复检验与停止规则均在读取结果前冻结；独立重放生成了完全相同的报告。', campaignThreeBadge: '已关闭 · 精确重放',
    campaignThreeStats: ['正式试验', '累计试验', '信号交易日', '观察数', '前瞻标签'],
    campaignThreeAlpha: '候选 Alpha 结论', campaignThreeAlphaValue: '0 / 2 获准', campaignThreeAlphaBody: '两项交互的主要斜率与后半段斜率均为负，没有通过区块下界或家族错误控制。',
    campaignThreeRisk: '风险护栏结论', campaignThreeRiskValue: '0 / 1 合格', campaignThreeRiskBody: '全期斜率虽为正，但后半段转负，两个登记区块的下界均跨零；因此按规则拒绝，而不是事后补救。',
    campaignThreeDecisions: '3项冻结决策', campaignThreeDecisionLabels: ['交互斜率', '后半段斜率', '最差90%下界', 'Holm p 值', '失败门槛'], campaignThreeRejected: '未通过',
    campaignThreeBoundary: '结果开放了什么权限', campaignThreeBoundaryBody: '没有开放任何下游权限。模型构建、验证集、留出集、个股候选激活、期权主张、发布权限与交易全部继续锁定。',
    foundation: '研究基础快照', foundationNote: '以下是已经在研究工作站完成核验并版本化的工程证据；每一项同时标明可用范围与证据边界。', foundationBadge: '证据核对 · 2026-09-15',
    foundationItems: [
      ['五年行情基础', '深度已完成', '连续日线行情与稳定证券身份的五年深度已经完成。', 'verified'],
      ['历史成员资格', '事后重建', '其中1,250个交易日为事后重建、3个为前瞻记录；重建历史不等于当时实录。', 'qualified'],
      ['公司行动', '部分证据', '第一策略4,643条暴露中4,623条已有精确事件日匹配；尚未证明其余空白均为中性。', 'qualified'],
      ['生命周期与终端', '参考边界已覆盖', '302条五日路径均已有精确或有限区间参考；参考证据仍不等于策略收益。', 'qualified'],
      ['点时基本面', '工程试点', '已登记4条SEC查询路径，并取得4个严格按当时可用信息投影的交易日；目前仅属工程证据。', 'qualified'],
    ],
    foundationControls: '第三批已经冻结的评估约束', controlLabels: ['登记试验', '时间前后半段', '自助法区块长度', '单边成本情景', '正式运行 / 精确重放'],
    foundationBoundary: '不会把不同证据强行合成为一个“总完成度”。任何必需证据族不合格，绩效研究仍保持锁定。',
    factorQualification: '因子资格诊断 V2', factorQualificationNote: '8项因子已在工作站同一冻结总体上完整计算两次。精确重放只检验来源与实现是否合格，全程不读取未来收益。', factorQualificationBadge: '已通过 · 精确重放',
    factorStats: ['登记因子', '完整向量', '覆盖率', '成对核验', '近重复组'],
    factorCoverageMeaning: '437,402条声明路径中，431,249条形成完整的8因子向量；6,153条不完整路径继续明确保留，没有静默补零。覆盖率达到98.59%，267个合格交易日在冻结的前后时间段中分布为123 / 144。',
    factorRedundancy: '最强同日关系', factorRedundancyBody: '两个风险护栏之间的绝对加权 Spearman 关系最高，为0.8942；没有因子对满足完整的近重复规则。这只代表数据资格通过，并不代表存在预测价值。',
    factorRoles: '目录角色', factorRoleValues: ['4项候选 Alpha 测量', '1项形态条件因子', '1项适用性输入', '2项风险护栏'],
    factorInspect: '展开审阅8项登记定义与精确公式',
    factorRole: '角色', factorFormula: '精确公式', factorWindow: '点时数据窗口', factorExpectation: '登记关系', source: '来源', cutoff: '可用时间界限', missing: '缺失处理',
    factorCutoffValue: '当日收盘数据完成 → 最早下一交易日开盘执行', factorMissingValue: '明确标为不可用 · 禁止静默补零',
    factorVerdict: 'V2 获得了什么资格', factorVerdictValue: '8 / 8 项可进入协议审查', factorVerdictBody: '4项候选 Alpha 测量、1项形态条件、1项适用性输入和2项风险护栏均通过覆盖、时间分布、取值、并列与冗余门槛。它们只是等待登记结果检验的测量，并非已获准因子。',
    factorNext: '资格诊断之后', factorNextValue: '筛选已完成 · 结论见下方', factorNextBody: '8项测量获得的是接受检验的资格，不是预设有效。正式筛选拒绝了所有候选 Alpha，并保持原资格报告不变。',
    factorLimits: '资格诊断边界', factorLimitsBody: '成员资格为事后重建而非当时实录；历史行业分类和充分的市场状态多样性尚未证明；日线不能观察点差或带方向订单流；即使重建数据通过资格，拆股空白是否中性仍作为来源限制公开保留。',
    screeningV2: '已完成开发期筛选 · 因子目录 V2', screeningV2Note: '这是预登记问题的不可变结论，不是为了外观挑选出来的回测。精确重放复现了全部结果和计数。', screeningV2Badge: '已关闭 · 精确重放',
    screeningV2Stats: ['正式试验', '累计试验', '信号交易日', '观察数', '前瞻标签'],
    screeningV2State: '候选 Alpha 结论', screeningV2StateValue: '0 / 4 获准', screeningV2StateBody: '4项候选 Alpha 均至少失败一个冻结门槛；已经看到结果后，不得再修补它们的公式或阈值。',
    screeningV2Selection: '风险证据', screeningV2SelectionValue: '2项通过 · 0项入选', screeningV2SelectionBody: '两项下行风险护栏均通过登记门槛，可以作为风险认识保留；但没有候选 Alpha 存活，因此都不能成为模型输入。',
    screeningV2Decisions: '6项登记决策', screeningV2DecisionLabels: ['稳健效应', '90%下界', 'Holm p 值', '失败门槛'], screeningV2Risk: '风险证据 · 未入选', screeningV2Rejected: '未通过',
    screeningV2Next: '后续研究批次结论', screeningV2NextValue: '3项试验 · 全部拒绝', screeningV2NextBody: '第三批已完成冻结筛选与精确重放，没有产生候选 Alpha、合格风险护栏或模型输入。',
    screeningV2Inspect: '展开审阅冻结协议、来源链与报告身份', screeningV2Protocol: '冻结评估规则', screeningV2ProtocolBody: '主要股票结果3个交易日 · 1/5日衰减 · 同日秩 · 10,000次五日循环区块自助法 · V1门槛保持不变 · 4项Alpha与2项风险分别做Holm校正 · 单边0/10/25/50 bps成本诊断。', screeningV2Limits: '仍保持关闭的部分', screeningV2LimitsBody: '历史行业中性化和充分的市场状态多样性仍不可用。筛选仅属于事后重建开发期证据；验证集、留出集、模型、策略、个股候选、期权与交易继续锁定。',
    factorScreen: '历史开发期筛选 · 因子目录 V1', factorScreenNote: '这是保留的失败研究，不是当前项目。有限协议在读取结果前已经提交，并在同一开发样本上完整执行两次；没有候选 Alpha 通过。', factorScreenBadge: '失败留档 · 精确重放',
    factorScreenStats: ['正式假设', '信号交易日', '观察数', '前瞻标签', '入选 Alpha / 风险'],
    factorScreenOutcome: '真实结论', factorScreenOutcomeBody: '没有候选 Alpha 通过冻结门槛。因此因子目录 V1 在没有预测模型的状态下关闭，也不得改变个股候选排名。',
    factorScreenSelected: '保留的证据', factorScreenSelectedBody: '10日滚动最大回撤作为下行风险护栏通过：稳健秩效应0.2540，90%下界0.2322，Holm校正 p 值0.0003。它可以约束未来模型，但自身不是 Alpha。',
    factorScreenDecisions: '8项登记决策', factorScreenDecisionLabels: ['稳健效应', '90%下界', 'Holm p 值', '失败门槛'], factorScreenPassed: '保留风险护栏', factorScreenRejected: '未通过',
    factorScreenInspect: '展开审阅协议、保管、限制与报告身份',
    factorScreenProtocol: '冻结评估规则', factorScreenProtocolBody: '主要周期3个交易日；1日与5日用于衰减诊断；10,000次五日循环区块自助法；90%区间；Holm家族错误控制；单边0/10/25/50 bps成本情景。',
    factorScreenLimits: '解释边界', factorScreenLimitsBody: '仅限开发期；成员资格为事后重建；仅106个信号日；历史分类和充分的市场状态多样性未获证明；固定成本只是情景而非执行校准。验证集和留出集从未打开。',
    owner: '研究归属', ownerValue: 'WH Alpha 个人量化研究',
    boundary: '权限边界', boundaryBody: '实验室负责因子、模型、表达与评估证据；个股候选未来只消费少量经过独立审查并明确激活的表达，不设永久模型数量上限。',
    lifecycle: '三层晋级路径', stages: ['因子发现', '模型构建', '策略表达', '验证', '封存留出集', '影子运行', '正式激活'],
    current: '当前', locked: '锁定', blocked: '受证据阻塞',
    results: '当前研究账本', resultsNote: '失败结果继续保留；不使用合成替代，也不暗示存在有效绩效',
    resultCards: [['第一批因子研究', '已关闭 · 无候选 Alpha'], ['第二批因子研究', '已关闭 · 无候选 Alpha'], ['第三批因子研究', '已关闭 · 无候选 Alpha'], ['已激活模型 / 策略', '无 / 无']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
  es: {
    eyebrow: 'Investigación de factores, modelos y estrategias · registro gobernado',
    title: 'Laboratorio de investigación cuantitativa',
    subtitle: 'El registro autoritativo de qué se mide, qué se modela, cómo se expresa una estrategia y en qué capa falla la evidencia.',
    status: 'DESCUBRIMIENTO DE FACTORES · TRES CAMPAÑAS CERRADAS', statusValue: 'SIN ALPHA CANDIDATO · NUEVA ENTRADA',
    statusNote: 'La tercera campaña completó una selección de Desarrollo congelada y una reproducción idéntica byte a byte. Las dos interacciones Alpha y la salvaguarda de riesgo fallaron; no se abrió ningún modelo ni estrategia.',
    coverage: 'Estado de la evidencia', coverageNote: 'La integridad del método y la eficacia del modelo son cuestiones distintas.',
    coverageBoundary: 'Publicar un método no convierte la estrategia en validada, adecuada para el mercado actual ni predictiva de rentabilidades de opciones.',
    submission: 'Se aceptan hipótesis refutables de factores o estrategias para su registro y evaluación independiente bajo el mismo proceso gobernado. Si una propuesta llega a un modelo utilizable y a un futuro uso comercial, WH Alpha contactará a la persona colaboradora y comunicará el resultado.',
    submissionContact: 'Contacto',
    readiness: 'Escalera de evidencia', readinessItems: [
      ['Arquitectura de tres capas', 'ACEPTADA', 'Descubrimiento de factores, Construcción del modelo y Expresión de estrategia tienen límites de versión y evidencia separados.', 'met'],
      ['Registro acumulativo de investigación', '17 PRUEBAS · TODAS CERRADAS', 'Las pruebas de las tres campañas permanecen contabilizadas. La quinta edición del registro conserva resultados y autoridad; no es una versión de modelo.', 'met'],
      ['Segunda campaña de factores', 'CERRADA', 'Ocho definiciones exactas cubrieron continuación, reversión, momento del retorno, defensa, aplicabilidad de liquidez y riesgo bajista. No produjo ningún Alpha candidato.', 'met'],
      ['Calificación de datos V2', 'SUPERADA', 'El informe y la reproducción son idénticos byte a byte: 98,59 % de vectores completos, 267 sesiones aptas y los ocho factores superan los filtros congelados; no hubo conflictos con la evidencia canónica previa.', 'met'],
      ['Selección en Desarrollo', 'COMPLETADA', 'Fallaron las cuatro pruebas Alpha. Dos salvaguardas superaron los criterios, pero la ausencia de Alpha impide pasar a Construcción del modelo.', 'met'],
      ['Reproducción exacta', 'VERIFICADA', 'La repetición independiente obtuvo el mismo resultado revisado, sin escrituras canónicas, de Producción ni solicitudes externas.', 'met'],
      ['Entradas de investigación reutilizables', '1 PANEL CALIFICADO', 'El panel de estado de mercado, reproducido exactamente, queda registrado para reutilización sin resultados. Los paneles con resultados y todo acceso nuevo siguen cerrados.', 'met'],
      ['Tercera campaña de factores', 'CERRADA · SIN ALPHA', 'El resultado formal y la reproducción exacta coinciden. Las dos interacciones Alpha y la salvaguarda fallaron la selección congelada; no se eligió ninguna entrada de modelo.', 'met'],
      ['Modelo, estrategia y Producto', 'BLOQUEADOS', 'No existe modelo predictivo, expresión de estrategia, autoridad sobre Candidatos ni afirmación sobre opciones.', 'locked'],
    ],
    cycle: 'Ciclo renovable de descubrimiento de factores', cycleNote: 'El programa puede continuar de forma indefinida. Cada campaña es finita, deduplicada, prerregistrada, reproducida y contabilizada de forma permanente.', cycleBadge: 'SISTEMA CONTINUO · CAMPAÑAS ACOTADAS',
    cycleStats: ['Modo operativo', 'Fase actual', 'Campañas concluidas', 'Pruebas registradas', 'Campaña actual'], cycleStatValues: ['RENOVABLE', 'ENTRADA SIN RESULTADOS', '3', '17', 'NINGUNA'],
    cycleStages: [
      ['01', 'Proponer y deduplicar', 'COMPLETADA', 'Se conservaron cinco ideas: cuatro avanzaron y una casi duplicada se detuvo antes de consultar resultados.'],
      ['02', 'Construir sin resultados', 'COMPLETADA', 'El informe de 106 sesiones y la reproducción independiente coincidieron: tres diseños superaron los filtros y un Alpha se detuvo antes de consultar resultados.'],
      ['03', 'Registrar la prueba finita', 'COMPLETADA', 'Dos pruebas Alpha y una de riesgo, con resultados, costes, multiplicidad, criterios, límites y parada, están congeladas en el registro acumulativo.'],
      ['04', 'Autorizar, evaluar y reproducir', 'COMPLETADA', 'La ejecución formal autorizada y su reproducción exacta coincidieron. Las tres pruebas fallaron; Validación y Holdout permanecieron sellados.'],
      ['05', 'Cerrar, contabilizar y volver', 'FASE ACTUAL', 'La quinta edición del registro conserva las 17 pruebas consumidas y devuelve el programa a una nueva entrada de hipótesis sin resultados.'],
    ],
    cycleCurrent: 'Posición actual', cycleCurrentValue: 'ENTRADA · SIN CAMPAÑA ACTIVA', cycleCurrentBody: 'La tercera campaña está cerrada. La siguiente debe comenzar con un nuevo conjunto de hipótesis refutables y deduplicadas frente a las 17 pruebas consumidas.',
    cycleInfrastructure: 'Detenido antes de resultados', cycleInfrastructureValue: '1 DISEÑO ALPHA RECHAZADO', cycleInfrastructureBody: 'La resiliencia defensiva carecía de soporte equilibrado alrededor de cero y estaba demasiado concentrada, también en la primera mitad. No se movió el umbral tras inspeccionarla.',
    cycleContinuity: 'Siguiente frontera', cycleContinuityValue: 'NUEVA CAMPAÑA FINITA', cycleContinuityBody: 'No existe más acceso a resultados de la tercera campaña. Una sucesora exige nueva admisión, calificación, preinscripción y autorización independiente.',
    cycleInspect: 'Examinar deduplicación, presupuesto, aislamiento y pausas',
    cycleGuardTitles: ['Identidad de duplicados', 'Presupuesto finito', 'Aislamiento por etapas', 'Pausa automática'],
    cycleGuardBodies: [
      'La novedad se revisa por mecanismo, información y corte, fórmula, universo, horizonte, vecindad de parámetros y familia de hipótesis relacionada.',
      'Deben congelarse el número de factores e interacciones, variantes, horizontes, familias, multiplicidad, límite de selección y regla de parada.',
      'Las fases de ideas y calificación no pueden leer resultados. Desarrollo se abre solo para una campaña nueva registrada; Validación y Holdout siguen separados.',
      'Una discrepancia de linaje, fuga entre etapas, exceso de presupuesto, fallo de reproducción o ruptura de una partición sellada detiene la campaña afectada.',
    ],
    agentPilot: 'Equipo de investigación aislado por etapas', agentPilotNote: 'El piloto multiagente supervisado completó calificación, preinscripción, una selección formal de Desarrollo, reproducción exacta, revisión adversarial y cierre del registro.', agentPilotBadge: 'CAMPAÑA CERRADA · REPRODUCCIÓN COINCIDENTE',
    agentStats: ['Calificación de mercado', 'Reproducción de entradas', 'Decisiones congeladas', 'Validación / Holdout'], agentStatValues: ['SUPERADA · 267 / 287', 'COINCIDE · 106 / 106', '3 · RECHAZADAS', 'SELLADOS'],
    agentStages: [
      ['01', 'Revisiones independientes', 'COMPLETADO', 'Las revisiones de gobierno, método e implementación detectaron y corrigieron defectos reales antes de ejecutar datos.'],
      ['02', 'Calificación del estado de mercado', 'COMPLETADA', 'Se evaluaron las 287 sesiones; la amplitud reconstruida estuvo disponible conjuntamente en 267 y la reproducción independiente coincidió byte a byte.'],
      ['03', 'Hipótesis y revisión de entradas', 'COMPLETADA', 'Se congelaron cinco fichas; tres diseños superaron la calificación exacta sin resultados y un Alpha aceptado fue rechazado.'],
      ['04', 'Protocolo y contabilidad de pruebas', 'COMPLETADA', 'Las tres pruebas calificadas y todas las reglas de evaluación y parada están fijadas en la cuarta edición del registro acumulativo.'],
      ['05', 'Evaluación de Desarrollo', 'COMPLETADA', 'La selección formal autorizada rechazó las tres pruebas congeladas sin alterar ningún criterio.'],
      ['06', 'Reproducción, ataque y decisión humana', 'COMPLETADA', 'La reproducción exacta coincidió, el registro se cerró y la autoridad de modelo posterior permaneció bloqueada.'],
    ],
    agentRoles: 'Mapa de roles y acceso', agentRoleNames: ['Control de investigación', 'Datos y evidencia', 'Revisión de hipótesis', 'Implementación', 'Evaluación', 'Equipo adversarial', 'Aprobación y publicación'],
    agentBoundary: 'Lo que esto no significa', agentBoundaryBody: 'No es un minero de Alpha autónomo. No se ha abierto ninguna nueva prueba de retorno, modelo, Validación, Holdout, autoridad de Candidatos, despliegue, bróker ni negociación.',
    agentInspect: 'Examinar aislamiento, puertas seriales y contabilidad compartida',
    campaignThree: 'Selección de Desarrollo completada · Tercera campaña', campaignThreeNote: 'La pregunta, la muestra, las regresiones de interacción, la inferencia por bloques, la multiplicidad y la regla de parada se congelaron antes de consultar resultados. La reproducción independiente generó el mismo informe.', campaignThreeBadge: 'CERRADA · REPRODUCCIÓN EXACTA',
    campaignThreeStats: ['Pruebas formales', 'Pruebas acumuladas', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras'],
    campaignThreeAlpha: 'Decisión sobre Alpha', campaignThreeAlphaValue: '0 / 2 admitidos', campaignThreeAlphaBody: 'Ambas interacciones tuvieron pendientes principales y de segunda mitad negativas. Ninguna superó los límites bootstrap ni el control familiar.',
    campaignThreeRisk: 'Decisión de salvaguarda', campaignThreeRiskValue: '0 / 1 calificada', campaignThreeRiskBody: 'La pendiente conjunta fue positiva, pero la segunda mitad se volvió negativa y ambos límites inferiores registrados cruzaron cero. Se rechazó sin rescatarla a posteriori.',
    campaignThreeDecisions: 'Las tres decisiones congeladas', campaignThreeDecisionLabels: ['Beta de interacción', 'Beta de segunda mitad', 'Peor límite inferior 90 %', 'p de Holm', 'Criterios fallidos'], campaignThreeRejected: 'Rechazada',
    campaignThreeBoundary: 'Qué autoriza el resultado', campaignThreeBoundaryBody: 'Nada aguas abajo. Construcción del modelo, Validación, Holdout, activación de Candidatos, afirmaciones sobre opciones, publicación y negociación siguen cerrados.',
    foundation: 'Resumen de la base de investigación', foundationNote: 'Evidencia verificada y versionada que ya existe en la estación de trabajo de investigación. Cada punto indica tanto su utilidad como su límite.', foundationBadge: 'EVIDENCIA REVISADA · 15 SEP 2026',
    foundationItems: [
      ['Base de mercado a cinco años', 'PROFUNDIDAD COMPLETA', 'La profundidad continua de precios diarios e identidad estable está completa.', 'verified'],
      ['Composición histórica', 'RECONSTRUIDA', '1.250 sesiones son reconstruidas y tres son prospectivas; la reconstrucción no equivale a un registro operativo de la fecha.', 'qualified'],
      ['Acciones corporativas', 'EVIDENCIA PARCIAL', '4.623 de 4.643 exposiciones del primer estudio tienen fecha de evento exacta; no se ha demostrado la neutralidad de las ausencias.', 'qualified'],
      ['Ciclo de vida y terminal', 'REFERENCIAS ACOTADAS', 'Las 302 trayectorias disponen de una referencia exacta o de intervalo finito; una referencia no es un resultado de estrategia.', 'qualified'],
      ['Fundamentales a fecha de conocimiento', 'PILOTO DE INGENIERÍA', 'Existen cuatro consultas SEC registradas y cuatro sesiones con proyección estricta según la información disponible entonces; sigue siendo evidencia de ingeniería.', 'qualified'],
    ],
    foundationControls: 'Controles ya congelados para la tercera campaña', controlLabels: ['Pruebas registradas', 'Mitades cronológicas', 'Longitudes de bloque bootstrap', 'Escenarios de costes por lado', 'Ejecución formal / reproducción exacta'],
    foundationBoundary: 'Estos hechos no se combinan en un único porcentaje de avance. Una familia de evidencia obligatoria insuficiente mantiene bloqueada la investigación de rendimiento.',
    factorQualification: 'Calificación de factores V2', factorQualificationNote: 'El catálogo de ocho factores se calculó dos veces sobre la misma población congelada en la estación de trabajo. La reproducción exacta evalúa solo la aptitud de las fuentes y de la implementación; nunca consulta rendimientos futuros.', factorQualificationBadge: 'SUPERADA · REPRODUCCIÓN EXACTA',
    factorStats: ['Factores registrados', 'Vectores completos', 'Cobertura', 'Pares revisados', 'Grupos casi duplicados'],
    factorCoverageMeaning: 'De 437.402 trayectorias declaradas, 431.249 produjeron vectores completos de ocho factores. Las 6.153 incompletas siguen explícitas, sin rellenarlas con cero. La disponibilidad alcanzó el 98,59 % en 267 sesiones aptas, repartidas 123 / 144 entre las dos mitades cronológicas congeladas.',
    factorRedundancy: 'Relación contemporánea más intensa', factorRedundancyBody: 'La mayor relación de Spearman ponderada en valor absoluto fue 0,8942 entre las dos salvaguardas de riesgo. Ningún par cumplió la regla completa de casi duplicado. Esto supera una prueba de datos, pero no demuestra capacidad predictiva.',
    factorRoles: 'Funciones del catálogo', factorRoleValues: ['4 medidas candidatas de Alpha', '1 condicionante de configuración', '1 variable de aplicabilidad', '2 salvaguardas de riesgo'],
    factorInspect: 'Examinar las ocho definiciones registradas y sus fórmulas exactas',
    factorRole: 'Función', factorFormula: 'Fórmula exacta', factorWindow: 'Ventana point-in-time', factorExpectation: 'Relación registrada', source: 'Fuente', cutoff: 'Corte de disponibilidad', missing: 'Tratamiento de ausencias',
    factorCutoffValue: 'cierre completo de la sesión → primera ejecución en la apertura siguiente', factorMissingValue: 'ausencia explícita · nunca se rellena con cero',
    factorVerdict: 'Qué habilitó V2', factorVerdictValue: '8 / 8 aptos para revisar el protocolo', factorVerdictBody: 'Las cuatro medidas candidatas de Alpha, un condicionante, una variable de aplicabilidad y dos salvaguardas superaron cobertura, cronología, variación, empates y redundancia. Son mediciones pendientes de una prueba registrada, no factores admitidos.',
    factorNext: 'Después de la calificación', factorNextValue: 'FILTRO COMPLETADO · DECISIÓN ABAJO', factorNextBody: 'Las ocho mediciones obtuvieron permiso para ser evaluadas, no una presunción de utilidad. El filtro rechazó todos los candidatos de Alpha y conservó intacta la calificación.',
    factorLimits: 'Límites de la calificación', factorLimitsBody: 'La composición está reconstruida y no registrada tal como se operó; la clasificación histórica y una diversidad amplia de regímenes no están demostradas; las barras diarias no observan diferenciales ni flujo firmado; la neutralidad de ausencias de splits sigue declarada como limitación incluso tras la calificación.',
    screeningV2: 'Selección de Desarrollo completada · Catálogo V2', screeningV2Note: 'Este es el resultado inmutable de la pregunta preinscrita, no un backtest elegido por su apariencia. La reproducción exacta coincidió en todos los resultados y recuentos.', screeningV2Badge: 'CERRADO · REPRODUCCIÓN EXACTA',
    screeningV2Stats: ['Pruebas formales', 'Pruebas acumuladas', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras'],
    screeningV2State: 'Decisión sobre Alpha', screeningV2StateValue: '0 / 4 admitidos', screeningV2StateBody: 'Las cuatro medidas candidatas de Alpha fallaron al menos un criterio congelado. Sus fórmulas y umbrales no pueden repararse después de observar los resultados.',
    screeningV2Selection: 'Evidencia de riesgo', screeningV2SelectionValue: '2 calificadas · 0 seleccionadas', screeningV2SelectionBody: 'Las dos salvaguardas bajistas superaron sus criterios. Se conservan como evidencia, pero no pasan a ser entradas de modelo porque ningún Alpha sobrevivió.',
    screeningV2Decisions: 'Las seis decisiones registradas', screeningV2DecisionLabels: ['Efecto robusto', 'Límite inferior 90 %', 'p de Holm', 'Filtros fallidos'], screeningV2Risk: 'Evidencia de riesgo · no seleccionada', screeningV2Rejected: 'Rechazado',
    screeningV2Next: 'Resultado de la campaña sucesora', screeningV2NextValue: '3 PRUEBAS · TODAS RECHAZADAS', screeningV2NextBody: 'La tercera campaña completó su selección congelada y la reproducción exacta. No produjo Alpha candidato, salvaguarda calificada ni entrada de modelo.',
    screeningV2Inspect: 'Examinar el protocolo, linaje e identidad del informe', screeningV2Protocol: 'Evaluación congelada', screeningV2ProtocolBody: 'Resultado principal a 3 sesiones · decaimiento a 1/5 · rangos por sesión · 10.000 réplicas bootstrap con bloques circulares de cinco sesiones · filtros V1 sin cambios · Holm en familias de 4 Alpha y 2 riesgos · diagnósticos de 0/10/25/50 pb por lado.', screeningV2Limits: 'Qué permanece cerrado', screeningV2LimitsBody: 'No se dispone de neutralización sectorial histórica ni de diversidad amplia de regímenes. Solo es evidencia reconstruida de Desarrollo; Validación, Holdout, modelo, estrategia, Candidatos, opciones y negociación siguen bloqueados.',
    factorScreen: 'Selección histórica en Desarrollo · Catálogo V1', factorScreenNote: 'Investigación fallida conservada, no la campaña actual. El protocolo finito se confirmó antes de consultar resultados y se ejecutó dos veces sobre la misma cohorte; ningún candidato de Alpha superó los filtros.', factorScreenBadge: 'FALLO CONSERVADO · REPRODUCCIÓN EXACTA',
    factorScreenStats: ['Hipótesis formales', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras', 'Alpha / riesgo seleccionados'],
    factorScreenOutcome: 'Resultado sin adornos', factorScreenOutcomeBody: 'Ningún candidato de Alpha superó los filtros congelados. El Catálogo V1 se cierra sin modelo predictivo y no puede modificar la clasificación de acciones.',
    factorScreenSelected: 'Evidencia conservada', factorScreenSelectedBody: 'La máxima caída móvil de 10 sesiones superó los filtros como salvaguarda bajista: efecto robusto de rango 0,2540, límite inferior del 90 % de 0,2322 y p de Holm 0,0003. Puede limitar un modelo futuro; por sí sola no es Alpha.',
    factorScreenDecisions: 'Las ocho decisiones registradas', factorScreenDecisionLabels: ['Efecto robusto', 'Límite inferior 90 %', 'p de Holm', 'Filtros fallidos'], factorScreenPassed: 'Salvaguarda conservada', factorScreenRejected: 'Rechazado',
    factorScreenInspect: 'Examinar protocolo, custodia, límites e identidad exacta',
    factorScreenProtocol: 'Evaluación congelada', factorScreenProtocolBody: 'Horizonte principal: 3 sesiones; diagnósticos de decaimiento: 1 y 5; 10.000 réplicas bootstrap con bloques circulares de cinco sesiones; intervalos del 90 %; control familiar de Holm; costes de 0/10/25/50 pb por lado.',
    factorScreenLimits: 'Límite de interpretación', factorScreenLimitsBody: 'Solo Desarrollo; composición reconstruida; 106 sesiones de señal; clasificación histórica y diversidad amplia de regímenes no demostradas; los costes fijos son escenarios, no calibración de ejecución. Validación y Holdout nunca se abrieron.',
    owner: 'Titularidad de la investigación', ownerValue: 'Investigación cuantitativa propia de WH Alpha',
    boundary: 'Límite de autoridad', boundaryBody: 'El Laboratorio custodia la evidencia de factores, modelos, expresiones y evaluación. Candidatos solo podrá consumir un conjunto pequeño y revisado de expresiones activadas, sin un límite numérico permanente.',
    lifecycle: 'Ruta de promoción de tres capas', stages: ['Descubrimiento de factores', 'Construcción del modelo', 'Expresión de estrategia', 'Validación', 'Holdout sellado', 'Sombra', 'Activación'],
    current: 'Actual', locked: 'Bloqueado', blocked: 'Bloqueado por la evidencia',
    results: 'Registro de investigación actual', resultsNote: 'Los fallos siguen visibles; sin sustitutos sintéticos ni rendimiento activo implícito',
    resultCards: [['Primera campaña de factores', 'Cerrada · sin Alpha candidato'], ['Segunda campaña de factores', 'Cerrada · sin Alpha candidato'], ['Tercera campaña de factores', 'Cerrada · sin Alpha candidato'], ['Modelos / estrategias activos', 'Ninguno / ninguna']],
    interpret: 'Cómo se presentará la evidencia futura', interpretBody: 'La investigación de señales mostrará expectativa neta, incertidumbre, costes, cobertura de muestra, tasa de aciertos/payoff/PF, MFE/MAE, sensibilidad, concentración y evidencia contraria. No se reducirá a una sola puntuación.',
    optionBoundary: 'La evidencia de una acción no es rendimiento de opciones', optionBoundaryBody: 'Las opciones requieren una capa de expresión independiente con cotizaciones contemporáneas, IV, griegas, diferenciales, interés abierto, vencimiento y riesgo de eventos.',
  },
} as const;

const ASHARE_COPY = {
  en: {
    title: 'China A-share research track',
    note: 'A separately governed market foundation using the same research standard—not U.S. data relabeled for another market.',
    badge: 'FOUNDATION PILOT · NOT BACKTEST READY',
    stats: [
      ['Pilot interval', '5 YEARS', '16 Sep 2021 → 16 Sep 2026'],
      ['Market scope', '6 SECURITIES', 'SSE / SZSE pilot · BSE quarantined'],
      ['Official calendar', '1,211 SESSIONS', '12 annual notices · zero date differences'],
      ['Market mechanics', '7,266 DECISIONS', 'Zero observed-bar violations · zero unresolved rules'],
      ['Factor research', '0 CAMPAIGNS', 'No A-share Alpha, model, ranking, or strategy exists'],
    ],
    dataTitle: 'What has been built and reread',
    dataItems: [
      ['Unadjusted daily evidence', '7,255 bars and 7,266 daily trading-state rows across the six bound SSE/SZSE pilot securities.'],
      ['Tradability state', 'The source-state history includes 11 suspended sessions and 259 present-but-unspecified risk-warning states; absent bars are not invented.'],
      ['Adjustment observations', 'Twenty-eight provider factor changes are retained with all three source fields, but normalized-return use remains unauthorized.'],
      ['Calendar evidence', 'Twelve exact SSE/SZSE annual notices reconcile 94 weekday closures, all 1,211 expected sessions, and every pilot state history.'],
      ['Custody', 'Calendar and mechanics official bytes are hash-bound, owner-only, immutable, and exactly reread. Internal IDs, paths, and hashes stay off the public page.'],
    ],
    mechanicsTitle: 'Rules, fees, and account-cost assumptions',
    mechanicsItems: [
      ['Official rule evidence', 'Thirteen exact official pages support 10 effective-dated trading rules and 14 statutory fee rules.'],
      ['Board mechanics', 'Main-board normal limits are 10%; STAR and ChiNext are 20%. Main-board risk-warning limits change from 5% to 10% on 6 Jul 2026. T+1 and lot rules remain effective-dated.'],
      ['Statutory costs', 'Seller-only stamp duty, securities regulatory fee, exchange handling fee, and transfer fee are modeled by exchange and effective date, including the 2022 and 2023 changes.'],
      ['Account scenario', 'Ping An Securities via Tonghuashun: user-reported commission 0.01% per side, conservatively CNY 5 minimum, plus 5 bps slippage per side.'],
      ['Uncertainty retained', 'The all-in commission interpretation, account-specific minimum, and historical backcast await broker-statement confirmation and must be stress-tested before performance use.'],
    ],
    gateTitle: 'Admission state and next gates',
    passed: 'QUALIFIED FOR THIS PILOT',
    passedItems: ['SSE/SZSE calendar', 'Effective-dated trading rules', 'Theoretical price-limit reconciliation', 'Statutory fee schedule', 'Cost-scenario registration'],
    blocked: 'STILL BLOCKED',
    blockedItems: ['Return-authorized adjustment semantics', 'Corporate-action economics', 'Listed-security lifecycle', 'Daily point-in-time Universe', 'Full-market and BSE route', 'Complete 13-family admission'],
    next: 'Next sequence',
    nextBody: 'Reconcile adjustment factors against corporate actions, close lifecycle evidence, build one daily Universe decision per instrument/session, expand the market in bounded partitions, then publish the 13-family admission report. Only a passing report can open the first outcome-blind A-share factor batch.',
    boundary: 'No A-share backtest, Alpha, model, candidate ranking, Product publication, or trading authority is active. The U.S. and A-share datasets, calendars, rules, Universes, results, and admissions remain physically and logically separate.',
  },
  zh: {
    title: '中国 A 股研究轨道',
    note: '采用同一套专业研究标准，但数据与治理完全独立；不会把美股数据换一个市场标签后重复使用。',
    badge: '基础试点 · 尚未达到回测准入',
    stats: [
      ['试点区间', '5 年', '2021-09-16 → 2026-09-16'],
      ['市场范围', '6 只证券', '上交所 / 深交所试点 · 北交所隔离'],
      ['官方交易日历', '1,211 个交易日', '12 份年度公告 · 日期差异为零'],
      ['市场制度判定', '7,266 条', '观察价格违规为零 · 未解析规则为零'],
      ['因子研究', '0 个批次', '尚无 A 股 Alpha、模型、排名或策略'],
    ],
    dataTitle: '已经建立并完成精确重读的证据',
    dataItems: [
      ['未复权日频证据', '六只已绑定沪深试点证券共 7,255 条日线与 7,266 条逐日交易状态。'],
      ['可交易状态', '历史中明确包含 11 个停牌交易日和 259 个“存在但细分类型未明”的风险警示状态；不会为停牌日虚构价格。'],
      ['复权观察', '保留 28 次因子变化及数据源的三个原始字段，但尚未授权用于标准化收益。'],
      ['日历证据', '12 份上交所/深交所年度原文公告覆盖 94 个工作日休市日，并与 1,211 个预期交易日及全部试点状态历史零差异对齐。'],
      ['证据保管', '日历与市场制度原始官方页面均绑定哈希、只允许所有者读取、不可变并完成精确重读；内部 ID、路径和哈希不在公开页面展示。'],
    ],
    mechanicsTitle: '交易规则、税费与账户成本假设',
    mechanicsItems: [
      ['官方规则证据', '13 个官方页面支持 10 条按生效日期管理的交易规则和 14 条法定费用规则。'],
      ['板块制度', '主板正常股票 10%，科创板与创业板 20%；主板风险警示股自 2026-07-06 由 5% 调整为 10%。T+1 与申报数量规则同样按生效日期管理。'],
      ['法定成本', '卖方印花税、证管费、交易所经手费和过户费按交易所与生效日期建模，包含 2022 和 2023 年的制度变更。'],
      ['账户场景', '平安证券经同花顺：用户提供佣金为买卖双边各万分之一，保守采用每笔最低 5 元，并加入单边 5 bps 滑点。'],
      ['保留不确定性', '佣金是否全包、实际账户是否收取最低 5 元、现行费率能否回推历史，仍待交割单确认；进入绩效研究前必须做压力测试。'],
    ],
    gateTitle: '准入状态与下一道关口',
    passed: '本试点已通过',
    passedItems: ['沪深交易日历', '按生效日期管理的交易规则', '理论涨跌停价格核对', '法定费用表', '账户成本场景登记'],
    blocked: '仍未通过',
    blockedItems: ['可用于收益的复权语义', '公司行动经济处理', '上市证券生命周期', '逐日点时 Universe', '全市场扩展与北交所路径', '完整 13 类数据准入'],
    next: '下一步顺序',
    nextBody: '先用公司行动核对复权因子，再补齐上市证券生命周期，为每只证券的每个交易日生成唯一 Universe 决策，分区扩展全市场，最后发布 13 类数据准入报告。只有正式通过后，才会开放第一批结果盲的 A 股因子研究。',
    boundary: '当前没有任何 A 股回测、Alpha、模型、候选排名、产品发布或交易权限。美股与 A 股的数据、日历、规则、Universe、研究结果和准入始终在物理与逻辑上隔离。',
  },
  es: {
    title: 'Línea de investigación de acciones A de China',
    note: 'Aplica el mismo estándar profesional, pero con datos y gobierno independientes; no reutiliza datos de EE. UU. bajo otra etiqueta.',
    badge: 'PILOTO DE BASE · AÚN NO APTO PARA BACKTEST',
    stats: [
      ['Intervalo piloto', '5 AÑOS', '16 sep 2021 → 16 sep 2026'],
      ['Ámbito', '6 VALORES', 'Piloto SSE / SZSE · BSE en cuarentena'],
      ['Calendario oficial', '1.211 SESIONES', '12 avisos anuales · cero diferencias'],
      ['Reglas de mercado', '7.266 DECISIONES', 'Cero infracciones observadas · cero reglas pendientes'],
      ['Investigación factorial', '0 CAMPAÑAS', 'No existe Alpha, modelo, ranking ni estrategia para acciones A'],
    ],
    dataTitle: 'Evidencia construida y releída exactamente',
    dataItems: [
      ['Evidencia diaria sin ajustar', '7.255 barras y 7.266 estados diarios para los seis valores piloto vinculados de SSE/SZSE.'],
      ['Estado de negociación', 'Incluye 11 sesiones suspendidas y 259 estados de advertencia de riesgo sin subtipo; no se inventan barras durante suspensiones.'],
      ['Observaciones de ajuste', 'Se conservan 28 cambios y los tres campos originales del proveedor, pero aún no autorizan retornos normalizados.'],
      ['Evidencia del calendario', 'Doce avisos exactos de SSE/SZSE concilian 94 cierres laborables, 1.211 sesiones esperadas y todos los historiales piloto sin diferencias.'],
      ['Custodia', 'Los bytes oficiales de calendario y reglas están ligados a hashes, son inmutables, de acceso restringido y tienen relectura exacta. Los identificadores internos no se publican.'],
    ],
    mechanicsTitle: 'Reglas, tasas y supuestos de costes',
    mechanicsItems: [
      ['Evidencia oficial', 'Trece páginas oficiales respaldan 10 reglas de negociación y 14 reglas de tasas con vigencia temporal.'],
      ['Mecánica por segmento', 'El límite normal del mercado principal es 10%; STAR y ChiNext usan 20%. La advertencia de riesgo del mercado principal pasa de 5% a 10% el 6 jul 2026. T+1 y los lotes también son temporales.'],
      ['Costes legales', 'Impuesto de timbre del vendedor, tasa regulatoria, tarifa bursátil y transferencia se modelan por bolsa y fecha, incluidos los cambios de 2022 y 2023.'],
      ['Escenario de cuenta', 'Ping An Securities vía Tonghuashun: comisión comunicada por el usuario de 0,01% por lado, mínimo conservador de CNY 5 y deslizamiento de 5 pb por lado.'],
      ['Incertidumbre explícita', 'La interpretación de comisión integral, el mínimo real y la extrapolación histórica esperan confirmación documental y pruebas de estrés.'],
    ],
    gateTitle: 'Estado de admisión y siguientes puertas',
    passed: 'CALIFICADO PARA ESTE PILOTO',
    passedItems: ['Calendario SSE/SZSE', 'Reglas con vigencia temporal', 'Conciliación teórica de límites', 'Tabla de tasas legales', 'Registro del escenario de costes'],
    blocked: 'AÚN BLOQUEADO',
    blockedItems: ['Semántica de ajustes apta para retornos', 'Economía de acciones corporativas', 'Ciclo de vida del valor cotizado', 'Universo diario point-in-time', 'Expansión total y ruta BSE', 'Admisión completa de 13 familias'],
    next: 'Secuencia siguiente',
    nextBody: 'Conciliar ajustes con acciones corporativas, cerrar el ciclo de vida, generar una decisión diaria de Universo por valor y sesión, ampliar el mercado por particiones y publicar la admisión de 13 familias. Solo un informe aprobado abrirá la primera campaña factorial sin resultados.',
    boundary: 'No hay backtest, Alpha, modelo, ranking, publicación de Producto ni autoridad de negociación para acciones A. Los datos, calendarios, reglas, Universos, resultados y admisiones de EE. UU. y China permanecen separados.',
  },
} as const;

function humanize(value: string): string {
  return value.split('_').join(' ');
}

export function QuantResearchLabPage(): JSX.Element {
  const { locale } = useI18n();
  const c = COPY[locale];
  const architecture = ARCHITECTURE_COPY[locale];
  const ashare = ASHARE_COPY[locale];
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
    numberFormat.format(factorScreeningV2.signal_session_count),
    numberFormat.format(factorScreeningV2.observation_count),
    numberFormat.format(factorScreeningV2.label_count),
  ];
  const campaignThreeStats = [
    numberFormat.format(campaignThreeScreening.formal_trial_count),
    numberFormat.format(campaignThreeScreening.cumulative_trial_count),
    numberFormat.format(campaignThreeScreening.signal_session_count),
    numberFormat.format(campaignThreeScreening.observation_count),
    numberFormat.format(campaignThreeScreening.label_count),
  ];
  const factorScreenStats = [
    numberFormat.format(factorScreening.formal_hypothesis_count),
    numberFormat.format(factorScreening.signal_session_count),
    numberFormat.format(factorScreening.observation_count),
    numberFormat.format(factorScreening.label_count),
    `${factorScreening.selected_alpha_count} / ${factorScreening.selected_risk_guard_count}`,
  ];
  const cycleStats = [
    c.cycleStatValues[0],
    c.cycleStatValues[1],
    numberFormat.format(discoveryCycle.completed_campaign_count),
    numberFormat.format(discoveryCycle.cumulative_formal_trial_count),
    c.cycleStatValues[4],
  ];
  const foundationValues = [
    numberFormat.format(1_255),
    `${numberFormat.format(1_253)} / ${numberFormat.format(1_255)}`,
    `${numberFormat.format(4_623)} / ${numberFormat.format(4_643)}`,
    `${numberFormat.format(219)} + ${numberFormat.format(83)}`,
    '4',
  ];
  const evaluationControls = [
    ['3', c.controlLabels[0]],
    ['53 / 53', c.controlLabels[1]],
    ['10 / 20 sessions', c.controlLabels[2]],
    ['0 / 10 / 25 / 50 bps', c.controlLabels[3]],
    ['1 / 1', c.controlLabels[4]],
  ];

  return <main className="research-page">
    <section className="research-hero">
      <div className="research-hero-copy"><span className="eyebrow">{c.eyebrow}</span><h1>{c.title}</h1><p>{c.subtitle}</p></div>
      <div className="research-status"><span>{c.status}</span><strong>{c.statusValue}</strong><p>{c.statusNote}</p></div>
      <div className="research-progress-copy"><strong>{c.coverage}</strong><span>{c.coverageNote}</span><small>{c.coverageBoundary}</small></div>
    </section>

    <p className="research-foundation-boundary">
      {c.submission}{' '}
      <a href="https://x.com/whalphalab" target="_blank" rel="noreferrer">
        {c.submissionContact} · @whalphalab
      </a>
    </p>

    <section className="research-card research-architecture" aria-labelledby="research-architecture-title">
      <header><span>00</span><div><p>{architecture.eyebrow}</p><h2 id="research-architecture-title">{architecture.title}</h2><small>{architecture.note}</small></div></header>
      <div className="research-architecture-grid">
        {architecture.layers.map(([index, title, state, body], layerIndex) => <article className={layerIndex === 0 ? 'active' : 'locked'} key={title}><div><span>{index}</span><b>{state}</b></div><h3>{title}</h3><p>{body}</p></article>)}
      </div>
      <strong className="research-architecture-boundary">{architecture.boundary}</strong>
    </section>

    <section className="research-card research-engineering-evidence" aria-labelledby="research-cycle-title">
      <header><span>∞</span><div><h2 id="research-cycle-title">{c.cycle}</h2><p>{c.cycleNote}</p></div><b>{c.cycleBadge}</b></header>
      <div className="research-factor-stats">
        {c.cycleStats.map((label, index) => <article key={label}><span>{label}</span><strong>{cycleStats[index]}</strong></article>)}
      </div>
      <ol className="research-engineering-rail">
        {c.cycleStages.map(([index, title, state, body], stageIndex) => <li className={stageIndex < 4 ? 'done' : 'current'} key={title}><i>{stageIndex < 4 ? '✓' : '●'}</i><strong>{index} · {title}</strong><small>{state} · {body}</small></li>)}
      </ol>
      <div className="research-screen-verdict">
        <article className="retained"><span>{c.cycleCurrent}</span><strong>{c.cycleCurrentValue}</strong><p>{c.cycleCurrentBody}</p></article>
        <article className="retained"><span>{c.cycleContinuity}</span><strong>{c.cycleContinuityValue}</strong><p>{c.cycleContinuityBody}</p></article>
        <article className="retained"><span>{c.cycleInfrastructure}</span><strong>{c.cycleInfrastructureValue}</strong><p>{c.cycleInfrastructureBody}</p></article>
      </div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.cycleInspect}</summary>
        <div className="research-screen-protocol">
          {c.cycleGuardTitles.map((title, index) => <article key={title}><strong>{title}</strong><p>{c.cycleGuardBodies[index]}</p></article>)}
        </div>
      </details>
    </section>

    <section className="research-card research-engineering-evidence research-agent-pilot" aria-labelledby="research-agent-pilot-title">
      <header><span>MA</span><div><h2 id="research-agent-pilot-title">{c.agentPilot}</h2><p>{c.agentPilotNote}</p></div><b>{c.agentPilotBadge}</b></header>
      <div className="research-factor-stats research-agent-stats">
        {c.agentStats.map((label, index) => <article key={label}><span>{label}</span><strong>{c.agentStatValues[index]}</strong></article>)}
      </div>
      <ol className="research-engineering-rail research-agent-rail">
        {c.agentStages.map(([index, title, state, body]) => <li className="done" key={title}><i>✓</i><strong>{index} · {title}</strong><small>{state} · {body}</small></li>)}
      </ol>
      <div className="research-engineering-boundary"><strong>{c.agentBoundary}</strong><p>{c.agentBoundaryBody}</p></div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.agentInspect}</summary>
        <div className="research-screen-protocol research-agent-role-grid">
          {multiAgentGovernance.role_policies.map((role, index) => <article key={role.role_id}><strong>{c.agentRoleNames[index]}</strong><p>{humanize(role.maximum_data_access)} · {humanize(role.required_handoff)}</p></article>)}
        </div>
      </details>
    </section>

    <section className="research-card research-factor-screening research-factor-screening-current" aria-labelledby="research-campaign-three-title">
      <header><span>C3</span><div><h2 id="research-campaign-three-title">{c.campaignThree}</h2><p>{c.campaignThreeNote}</p></div><b>{c.campaignThreeBadge}</b></header>
      <div className="research-factor-stats research-screen-stats">
        {c.campaignThreeStats.map((label, index) => <article key={label}><span>{label}</span><strong>{campaignThreeStats[index]}</strong></article>)}
      </div>
      <div className="research-screen-verdict">
        <article className="rejected"><span>{c.campaignThreeAlpha}</span><strong>{c.campaignThreeAlphaValue}</strong><p>{c.campaignThreeAlphaBody}</p></article>
        <article className="rejected"><span>{c.campaignThreeRisk}</span><strong>{c.campaignThreeRiskValue}</strong><p>{c.campaignThreeRiskBody}</p></article>
      </div>
      <h3 className="research-screen-decision-title">{c.campaignThreeDecisions}</h3>
      <div className="research-screen-decisions">
        {campaignThreeScreening.decisions.map((decision) => <article className="rejected" key={decision.decision_key}>
          <header><div><strong>{CAMPAIGN_THREE_DECISION_NAMES[locale][decision.decision_key]}</strong><span>{c.campaignThreeDecisionLabels[4]} · {numberFormat.format(decision.failed_gate_count)}</span></div><b>{c.campaignThreeRejected}</b></header>
          <dl>
            <div><dt>{c.campaignThreeDecisionLabels[0]}</dt><dd>{screeningMetricFormat.format(decision.interaction_beta)}</dd></div>
            <div><dt>{c.campaignThreeDecisionLabels[1]}</dt><dd>{screeningMetricFormat.format(decision.second_half_beta)}</dd></div>
            <div><dt>{c.campaignThreeDecisionLabels[2]}</dt><dd>{screeningMetricFormat.format(decision.robust_lower_bound)}</dd></div>
            <div><dt>{c.campaignThreeDecisionLabels[3]}</dt><dd>{screeningMetricFormat.format(decision.holm_adjusted_p_value)}</dd></div>
          </dl>
        </article>)}
      </div>
      <div className="research-factor-limit"><strong>{c.campaignThreeBoundary}</strong><p>{c.campaignThreeBoundaryBody}</p></div>
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

    <section className="research-card research-foundation research-ashare" aria-labelledby="research-ashare-title">
      <header><span>CN</span><div><h2 id="research-ashare-title">{ashare.title}</h2><p>{ashare.note}</p></div><b>{ashare.badge}</b></header>
      <div className="research-factor-stats research-ashare-stats">
        {ashare.stats.map(([label, value, body]) => <article key={label}><span>{label}</span><strong>{value}</strong><small>{body}</small></article>)}
      </div>
      <div className="research-ashare-ledger">
        <details className="research-factor-details" open>
          <summary>{ashare.dataTitle}</summary>
          <dl className="research-record-ledger">{ashare.dataItems.map(([label, body]) => <div key={label}><dt>{label}</dt><dd>{body}</dd></div>)}</dl>
        </details>
        <details className="research-factor-details">
          <summary>{ashare.mechanicsTitle}</summary>
          <dl className="research-record-ledger">{ashare.mechanicsItems.map(([label, body]) => <div key={label}><dt>{label}</dt><dd>{body}</dd></div>)}</dl>
        </details>
        <details className="research-factor-details" open>
          <summary>{ashare.gateTitle}</summary>
          <div className="research-screen-verdict research-ashare-gates">
            <article className="retained"><strong>{ashare.passed}</strong><ul>{ashare.passedItems.map((item) => <li key={item}>{item}</li>)}</ul></article>
            <article className="blocked"><strong>{ashare.blocked}</strong><ul>{ashare.blockedItems.map((item) => <li key={item}>{item}</li>)}</ul></article>
          </div>
          <div className="research-factor-limit research-ashare-next"><strong>{ashare.next}</strong><p>{ashare.nextBody}</p></div>
        </details>
      </div>
      <p className="research-foundation-boundary">{ashare.boundary}</p>
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
          <header><span>{FACTOR_TAXONOMY[locale][factor.family]}</span><strong>{FACTOR_NAMES[locale][factor.factor_id]}</strong></header>
          <dl>
            <div><dt>{c.factorRole}</dt><dd>{FACTOR_TAXONOMY[locale][factor.role]}</dd></div>
            <div><dt>{c.factorExpectation}</dt><dd>{FACTOR_TAXONOMY[locale][factor.expected_relationship]}</dd></div>
            <div><dt>{c.factorFormula}</dt><dd><code>{factor.exact_formula}</code></dd></div>
            <div><dt>{c.source}</dt><dd>{factor.source_fields.map(humanize).join(' · ')}</dd></div>
            <div><dt>{c.factorWindow}</dt><dd>{humanize(factor.source_window)}</dd></div>
            <div><dt>{c.cutoff}</dt><dd>{c.factorCutoffValue}</dd></div>
            <div><dt>{c.missing}</dt><dd>{c.factorMissingValue}</dd></div>
          </dl>
        </article>)}</div>
        <dl className="research-factor-reproduction"><div><dt>{c.factorWindow}</dt><dd>{factorQualification.first_session} → {factorQualification.last_session}</dd></div></dl>
      </details>
      <div className="research-factor-limit"><strong>{c.factorLimits}</strong><p>{c.factorLimitsBody}</p></div>
    </section>

    <section className="research-card research-factor-screening research-factor-screening-current" aria-labelledby="research-factor-screening-v2-title">
      <header><span>04</span><div><h2 id="research-factor-screening-v2-title">{c.screeningV2}</h2><p>{c.screeningV2Note}</p></div><b>{c.screeningV2Badge}</b></header>
      <div className="research-factor-stats research-screen-stats">
        {c.screeningV2Stats.map((label, index) => <article key={label}><span>{label}</span><strong>{factorScreeningV2Stats[index]}</strong></article>)}
      </div>
      <div className="research-screen-verdict">
        <article><span>{c.screeningV2State}</span><strong>{c.screeningV2StateValue}</strong><p>{c.screeningV2StateBody}</p></article>
        <article className="retained"><span>{c.screeningV2Selection}</span><strong>{c.screeningV2SelectionValue}</strong><p>{c.screeningV2SelectionBody}</p></article>
      </div>
      <h3 className="research-screen-decision-title">{c.screeningV2Decisions}</h3>
      <div className="research-screen-decisions">
        {factorScreeningV2.decisions.map((decision) => <article className={decision.status === 'qualified_not_selected_cap' ? 'retained' : 'rejected'} key={decision.factor_id}>
          <header><div><span>{FACTOR_TAXONOMY[locale][decision.role]}</span><strong>{FACTOR_NAMES[locale][decision.factor_id]}</strong></div><b>{decision.status === 'qualified_not_selected_cap' ? c.screeningV2Risk : c.screeningV2Rejected}</b></header>
          <dl>
            <div><dt>{c.screeningV2DecisionLabels[0]}</dt><dd>{screeningMetricFormat.format(decision.robust_effect)}</dd></div>
            <div><dt>{c.screeningV2DecisionLabels[1]}</dt><dd>{screeningMetricFormat.format(decision.robust_lower_bound)}</dd></div>
            <div><dt>{c.screeningV2DecisionLabels[2]}</dt><dd>{screeningMetricFormat.format(decision.holm_adjusted_p_value)}</dd></div>
            <div><dt>{c.screeningV2DecisionLabels[3]}</dt><dd>{numberFormat.format(decision.failed_gate_count)}</dd></div>
          </dl>
        </article>)}
      </div>
      <div className="research-factor-limit research-next-campaign"><strong>{c.screeningV2Next}</strong><p><b>{c.screeningV2NextValue}</b>{c.screeningV2NextBody}</p></div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.screeningV2Inspect}</summary>
        <div className="research-screen-protocol">
          <article><strong>{FACTOR_TAXONOMY[locale].candidate_alpha}</strong><ul className="research-record-list">{factorScreeningV2.alpha_factor_ids.map((factorId) => <li key={factorId}>{FACTOR_NAMES[locale][factorId]}</li>)}</ul></article>
          <article><strong>{FACTOR_TAXONOMY[locale].risk_guard}</strong><ul className="research-record-list">{factorScreeningV2.risk_guard_factor_ids.map((factorId) => <li key={factorId}>{FACTOR_NAMES[locale][factorId]}</li>)}</ul></article>
        </div>
        <div className="research-screen-protocol"><article><strong>{c.screeningV2Protocol}</strong><p>{c.screeningV2ProtocolBody}</p></article><article><strong>{c.screeningV2Limits}</strong><p>{c.screeningV2LimitsBody}</p></article></div>
        <dl className="research-factor-reproduction">
          <div><dt>Development window</dt><dd>{factorScreeningV2.first_signal_session} → {factorScreeningV2.last_signal_session}</dd></div>
          <div><dt>incremental control</dt><dd>{FACTOR_NAMES[locale][factorScreeningV2.incremental_baseline_factor_id]}</dd></div>
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
        </dl>
      </details>
    </section>

    <section className="research-boundary-grid"><article><span>{c.owner}</span><strong>{c.ownerValue}</strong></article><article><span>{c.boundary}</span><p>{c.boundaryBody}</p></article></section>

    <section className="research-card research-lifecycle"><header><span>06</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>07</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
