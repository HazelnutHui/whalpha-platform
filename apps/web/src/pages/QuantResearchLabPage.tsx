import modelRecord from '../modelRecords/quant-research-lab-model-record-v1.json';
import factorQualification from '../modelRecords/quant-research-factor-qualification-v2.json';
import discoveryCycle from '../modelRecords/quant-research-discovery-cycle-v1.json';
import multiAgentGovernance from '../modelRecords/quant-research-multi-agent-governance-v1.json';
import factorScreeningV2 from '../modelRecords/quant-research-factor-screening-v2.json';
import factorScreening from '../modelRecords/quant-research-factor-screening-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const ARCHITECTURE_COPY = {
  en: {
    eyebrow: 'Current research architecture · ADR 0274',
    title: 'From measurement to a decision—without collapsing the evidence.',
    note: 'The research universe can expand over time. Every batch that reads outcomes remains finite, registered, and fully counted.',
    layers: [
      ['01', 'Factor Discovery', 'CURRENT · V2 CLOSED', 'Catalog V2 completed its frozen Development screen and exact replay. All four candidate-Alpha trials failed; two risk guards passed their own gates but cannot open a model without Alpha. The next campaign must register a genuinely new question.'],
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
      ['01', '因子发现层', '当前阶段 · V2 已关闭', '因子目录 V2 已完成冻结的开发期筛选和精确重放。4项候选 Alpha 全部失败；2项风险护栏通过自身门槛，但没有 Alpha 时不能开启模型。下一批必须登记真正不同的新问题。'],
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
      ['01', 'Descubrimiento de factores', 'FASE ACTUAL · V2 CERRADO', 'El Catálogo V2 completó su filtro de Desarrollo congelado y la reproducción exacta. Fallaron las cuatro pruebas candidatas de Alpha; dos salvaguardas superaron sus propios criterios, pero no pueden abrir un modelo sin Alpha. La próxima campaña debe registrar una pregunta realmente nueva.'],
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
    status: 'FACTOR DISCOVERY V2', statusValue: 'CLOSED · NO CANDIDATE ALPHA',
    statusNote: 'The frozen six-trial screen and exact replay are complete. All four candidate-Alpha measurements failed; two risk guards passed their own gates but receive no model-input authority without Alpha.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    submission: 'Submit a falsifiable factor or strategy hypothesis for independent registration and testing under the same governed workflow. If an idea ultimately enters a usable model and future commercial use, WH Alpha will contact the contributor and report the outcome.',
    submissionContact: 'Contact',
    readiness: 'Evidence ladder', readinessItems: [
      ['Three-layer architecture', 'ACCEPTED', 'Factor Discovery, Model Construction, and Strategy Expression now have separate version and evidence boundaries.', 'met'],
      ['Cumulative research ledger', 'CLOSED · 14 TRIALS', 'All eight V1 and six V2 trials remain counted with their immutable outcomes. No failed trial was removed or relabeled.', 'met'],
      ['Factor Catalog V2', 'SCREENED', 'Eight exact definitions covered continuation, reversal, return timing, defensive state, liquidity applicability, and downside risk.', 'met'],
      ['V2 data qualification', 'PASSED', 'The report and replay are byte-identical: 98.59% complete vectors, 267 eligible sessions, and all eight definitions clear the frozen gates.', 'met'],
      ['Development screen', 'COMPLETED', 'Four Alpha trials failed. Two risk guards passed, but the no-Alpha prerequisite prevents selection into Model Construction.', 'met'],
      ['Exact reproduction', 'VERIFIED', 'The independent replay returned the identical reviewed result with zero canonical, Production, or external writes.', 'met'],
      ['Reusable research inputs', '1 PANEL QUALIFIED', 'The exactly replayed Market-State panel is registered for outcome-blind reuse. Outcome-bearing panels and all new result access remain closed.', 'met'],
      ['Next discovery campaign', 'PROTOCOL FREEZE', 'Outcome-blind qualification and exact replay are complete: two Alpha interactions and one risk guard advance; one Alpha design stopped before outcomes.', 'active'],
      ['Model, strategy & Product', 'LOCKED', 'No predictive model, strategy expression, Candidate authority, or option-performance claim exists.', 'locked'],
    ],
    cycle: 'Renewable factor-discovery loop', cycleNote: 'The research program may continue indefinitely. Every campaign inside it is finite, deduplicated, preregistered, replayed, and permanently counted.', cycleBadge: 'CONTINUOUS SYSTEM · BOUNDED CAMPAIGNS',
    cycleStats: ['Operating mode', 'Current stage', 'Completed campaigns', 'Formal trials consumed', 'Next campaign'], cycleStatValues: ['RENEWABLE', 'PROTOCOL + LEDGER V4', '2', '14', '3 TRIALS · NOT REGISTERED'],
    cycleStages: [
      ['01', 'Propose & deduplicate', 'COMPLETED', 'Five ideas were retained; four advanced and one near-duplicate stopped before any outcome access.'],
      ['02', 'Build without outcomes', 'COMPLETED', 'The exact 106-session report and independent replay matched. Three designs qualified; one Alpha design stopped before outcomes.'],
      ['03', 'Register & falsify', 'CURRENT', 'Freeze exactly two Alpha trials and one risk trial, including outcomes, costs, multiplicity, gates, caps, and stop rule, in Ledger V4.'],
      ['04', 'Replay, close & return', 'LOCKED', 'Attack leakage and stability, reproduce the exact result, append every failure, route any survivor, then return to hypothesis intake.'],
    ],
    cycleCurrent: 'Current position', cycleCurrentValue: '3 DESIGNS · INPUT QUALIFIED', cycleCurrentBody: 'Two candidate-Alpha interactions and one risk guard passed the frozen outcome-blind gates and an exact replay. They are not yet registered return trials and have no performance result.',
    cycleInfrastructure: 'Stopped before outcomes', cycleInfrastructureValue: '1 ALPHA DESIGN REJECTED', cycleInfrastructureBody: 'Defensive resilience lacked balanced natural-zero state support and was overly concentrated, including in the first half. Its threshold was not moved after inspection.',
    cycleContinuity: 'Next boundary', cycleContinuityValue: 'PROTOCOL + LEDGER V4', cycleContinuityBody: 'Only the three qualified designs may be registered. Development outcomes remain inaccessible until the protocol and cumulative ledger are frozen and separately authorized.',
    cycleInspect: 'Inspect deduplication, budget, isolation, and pause rules',
    cycleGuardTitles: ['Duplicate identity', 'Finite trial budget', 'Stage isolation', 'Automatic pause'],
    cycleGuardBodies: [
      'Novelty is checked across mechanism, information set and cutoff, formula, Universe, horizon, parameter neighborhood, and related hypothesis family.',
      'Factor and interaction count, parameter variants, horizons, hypothesis families, multiplicity, selection cap, and stopping rule must all be frozen.',
      'Idea and qualification stages cannot read outcomes. Development access begins only for a newly registered campaign; Validation and Holdout remain separate.',
      'Lineage mismatch, stage leakage, trial-budget breach, replay failure, or sealed-partition breach stops the affected campaign without erasing prior work.',
    ],
    agentPilot: 'Stage-isolated research team', agentPilotNote: 'The supervised multi-Agent pilot has completed market-state qualification, hypothesis intake, and outcome-blind input qualification. Three designs advance to protocol freeze; one stopped before outcomes.', agentPilotBadge: 'INPUTS QUALIFIED · OUTCOMES CLOSED',
    agentStats: ['Market-state qualification', 'Input replay', 'Qualified designs', 'Validation / Holdout'], agentStatValues: ['PASSED · 267 / 287', 'MATCHED · 106 / 106', '3 · NO OUTCOMES', 'SEALED'],
    agentStages: [
      ['01', 'Independent reviews', 'COMPLETED', 'Governance, methodology, and implementation reviewers found and corrected real pre-run defects.'],
      ['02', 'Market-state qualification', 'COMPLETED', 'All 287 sessions were evaluated; reconstructed breadth was jointly available for 267 sessions and the independent canonical-byte replay matched.'],
      ['03', 'Hypotheses and input review', 'COMPLETED', 'Five cards were frozen; three designs passed exact outcome-blind qualification and one accepted Alpha design was rejected.'],
      ['04', 'Protocol and ledger freeze', 'CURRENT', 'Register only the three qualified trials and every evaluation and stopping rule in append-only Ledger V4.'],
      ['05', 'Development evaluation', 'LOCKED', 'A single deterministic execution boundary may open only after separate review and exact authorization.'],
      ['06', 'Replay, red team, and human route', 'LOCKED', 'Agent consensus never replaces exact reproduction, deterministic gates, or human authority.'],
    ],
    agentRoles: 'Role and access map', agentRoleNames: ['Research controller', 'Data & evidence', 'Hypothesis review', 'Implementation', 'Evaluation', 'Red team', 'Approval & publication'],
    agentBoundary: 'What this does not mean', agentBoundaryBody: 'This is not an unattended Alpha miner. No new return trial, model, Validation, Holdout, Candidate authority, deployment, broker access, or trading authority is open.',
    agentInspect: 'Inspect role isolation, serial gates, and shared accounting',
    foundation: 'Research foundation snapshot', foundationNote: 'Verified, versioned evidence already built on the research workstation. Each item states both its useful scope and its limit.', foundationBadge: 'EVIDENCE REVIEWED · 15 SEP 2026',
    foundationItems: [
      ['Five-year market base', 'DEPTH COMPLETE', 'Contiguous EOD price and stable-identity depth are complete.', 'verified'],
      ['Historical membership', 'RECONSTRUCTED', '1,250 sessions are reconstructed and three are prospective; reconstructed history is not as operated.', 'qualified'],
      ['Corporate actions', 'PARTIAL EVIDENCE', '4,623 of 4,643 first-strategy exposures have exact event-date assignments; absence neutrality is not proven.', 'qualified'],
      ['Lifecycle & terminal', 'BOUNDED REFERENCES', 'All 302 five-session paths have either exact or finite-interval references; references are not strategy outcomes.', 'qualified'],
      ['Point-in-time fundamentals', 'ENGINEERING PILOT', 'Four registered SEC query paths and four strict as-operated projection sessions exist; this is engineering evidence only.', 'qualified'],
    ],
    foundationControls: 'Evaluation controls already frozen', controlLabels: ['Registered specifications', 'Chronological split', 'Purge + embargo', 'Cost scenarios per side', 'Sealed holdout use'],
    foundationBoundary: 'These facts are not blended into one readiness percentage. A weak mandatory evidence family keeps performance research locked.',
    factorQualification: 'Factor qualification V2', factorQualificationNote: 'The eight-factor catalog was calculated twice over the same frozen workstation population. The exact replay measures source and implementation fitness only; it never reads future returns.', factorQualificationBadge: 'PASSED · EXACT REPLAY',
    factorStats: ['Registered factors', 'Complete vectors', 'Coverage', 'Pair checks', 'Near-duplicate groups'],
    factorCoverageMeaning: '431,249 of 437,402 declared paths produced complete eight-factor vectors. The 6,153 incomplete paths remain explicit; none was zero-filled. Availability reached 98.59% across 267 eligible sessions, split 123 / 144 across the frozen chronological halves.',
    factorRedundancy: 'Strongest same-session relationship', factorRedundancyBody: 'The largest absolute weighted Spearman relationship was 0.8942 between the two risk guards. No pair met the full near-duplicate rule. This passes a data-qualification test; it says nothing about predictive value.',
    factorRoles: 'Catalog roles', factorRoleValues: ['4 candidate Alpha measurements', '1 setup conditioner', '1 applicability input', '2 risk guards'],
    factorInspect: 'Inspect all eight registered definitions and exact formulas',
    factorRole: 'Role', factorFormula: 'Exact formula', factorWindow: 'Point-in-time source window', factorExpectation: 'Registered relationship',
    factorCutoffValue: 'completed session close → next session open', factorMissingValue: 'explicit unavailable · never zero-fill',
    factorVerdict: 'What V2 earned', factorVerdictValue: '8 / 8 eligible for protocol review', factorVerdictBody: 'Four candidate Alpha measurements, one setup conditioner, one applicability input, and two risk guards cleared coverage, chronology, variation, tie, and redundancy gates. They are measurements awaiting a registered outcome test—not admitted factors.',
    factorNext: 'Qualification outcome', factorNextValue: 'SCREEN COMPLETED · SEE DECISION BELOW', factorNextBody: 'All eight measurements were eligible to be tested, not presumed useful. The completed screen rejected every candidate Alpha and preserved the qualification record unchanged.',
    factorLimits: 'Qualification limits', factorLimitsBody: 'Membership is reconstructed rather than as operated; historical classifications and broad Regime diversity remain unproven; daily bars do not observe spreads or signed order flow; and split-neutral absence remains a disclosed source limitation despite the qualified reconstruction.',
    screeningV2: 'Completed Development Screen · Factor Catalog V2', screeningV2Note: 'This is the immutable result of the preregistered question, not a backtest selected for appearance. The exact replay matched every result and count.', screeningV2Badge: 'CLOSED · EXACT REPLAY',
    screeningV2Stats: ['Formal trials', 'Cumulative trials', 'Signal sessions', 'Observations', 'Forward labels'],
    screeningV2State: 'Candidate Alpha decision', screeningV2StateValue: '0 / 4 admitted', screeningV2StateBody: 'All four candidate-Alpha measurements failed at least one frozen gate. Their formulas and thresholds cannot be repaired after seeing these outcomes.',
    screeningV2Selection: 'Risk evidence', screeningV2SelectionValue: '2 qualified · 0 selected', screeningV2SelectionBody: 'Both downside-risk guards passed their registered gates. They remain useful evidence, but neither becomes a model input because no candidate Alpha survived.',
    screeningV2Decisions: 'All six registered decisions', screeningV2DecisionLabels: ['Robust effect', '90% lower bound', 'Holm p', 'Failed gates'], screeningV2Risk: 'Risk evidence · not selected', screeningV2Rejected: 'Rejected',
    screeningV2Next: 'Next governed question', screeningV2NextValue: '3 DESIGNS · PROTOCOL FREEZE', screeningV2NextBody: 'Two Alpha interactions and one risk guard passed the 106-session outcome-blind input gates and exact replay. One Alpha design stopped before outcomes. Ledger V4 must be frozen before any separate Development-access decision.',
    screeningV2Inspect: 'Inspect the frozen protocol, lineage, and report identity', screeningV2Protocol: 'Frozen evaluation', screeningV2ProtocolBody: '3-session primary stock outcome · 1/5-session decay · same-session ranks · 10,000 circular five-session block-bootstrap replications · unchanged V1 gates · Holm within 4-Alpha and 2-risk families · 0/10/25/50 bps-per-side diagnostics.', screeningV2Limits: 'What remains closed', screeningV2LimitsBody: 'Historical sector neutralization and broad Regime diversity remain unavailable. This is reconstructed Development evidence only; Validation, Holdout, model, strategy, Candidate, options, and trading remain locked.',
    factorScreen: 'Historical Development Screen · Factor Catalog V1', factorScreenNote: 'Retained failed research, not the current campaign. Its finite protocol was committed before outcome access and executed twice against the same Development cohort; no candidate Alpha passed.', factorScreenBadge: 'RETAINED FAILURE · EXACT REPLAY',
    factorScreenStats: ['Formal hypotheses', 'Signal sessions', 'Observations', 'Forward labels', 'Selected Alpha / risk'],
    factorScreenOutcome: 'The honest result', factorScreenOutcomeBody: 'Zero candidate-Alpha factors passed the frozen gates. Factor Catalog V1 therefore closes without a predictive model and cannot change Stock Candidates.',
    factorScreenSelected: 'Evidence retained', factorScreenSelectedBody: '10-session rolling maximum drawdown passed as a downside-risk guard: robust rank effect 0.2540, 90% lower bound 0.2322, Holm-adjusted p 0.0003. It may constrain a later model; it is not Alpha by itself.',
    factorScreenDecisions: 'All eight registered decisions', factorScreenDecisionLabels: ['Robust effect', '90% lower bound', 'Holm p', 'Failed gates'], factorScreenPassed: 'Risk guard retained', factorScreenRejected: 'Rejected',
    factorScreenInspect: 'Inspect protocol, custody, limits, and exact report identity',
    factorScreenProtocol: 'Frozen evaluation', factorScreenProtocolBody: 'Primary horizon: 3 sessions · decay diagnostics: 1 and 5 · 10,000 circular five-session block-bootstrap replications · 90% intervals · Holm family-wise control · 0/10/25/50 bps per-side cost diagnostics.',
    factorScreenLimits: 'Interpretation boundary', factorScreenLimitsBody: 'Development only; reconstructed membership; 106 signal sessions; historical classification and broad Regime diversity not proven; fixed costs are scenarios, not execution calibration. Validation and Holdout were never opened.',
    engineering: 'Historical method-engineering evidence', engineeringNote: 'The first Pullback method was run twice over the reconstructed workstation population with identical results. These retained facts answer whether that method could be computed—not whether it worked.', engineeringBadge: 'HISTORICAL · OUTCOME BLIND',
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
    inspect: 'Inspect complete logic, formulas, parameters, and evaluation',
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
    resultCards: [['Factor Catalog V2', 'Closed · no candidate Alpha'], ['Factor Screen V1', 'Closed · no candidate Alpha'], ['Pullback program', 'Closed · no stable selection'], ['Active models', 'None']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '因子、模型与策略研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '权威记录测量什么、如何建模、怎样形成策略，以及证据在哪一层失败，而不是只陈列漂亮回测。',
    status: '因子发现 V2', statusValue: '已关闭 · 无候选 Alpha',
    statusNote: '冻结的6项开发期筛选和精确重放已经完成。4项候选 Alpha 全部失败；2项风险护栏通过自身门槛，但没有 Alpha 时不获得模型输入权限。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    submission: '欢迎提交可证伪的因子或策略假设。WH Alpha 将按统一研究流程独立登记、测试并保留失败记录；若建议最终进入可用模型并产生未来商业用途，将联系贡献者并反馈结果。',
    submissionContact: '联系',
    readiness: '证据阶梯', readinessItems: [
      ['三层研究架构', '已生效', '因子发现、模型构建与策略表达现在拥有相互独立的版本和证据边界。', 'met'],
      ['累计研究账本', '已关闭 · 共14项试验', 'V1 的8项和 V2 的6项试验及其不可变结论均完整保留；没有删除或改名任何失败记录。', 'met'],
      ['因子目录 V2', '已筛选', '8项精确定义覆盖延续、反转、收益时段、防御状态、流动性适用性与下行风险。', 'met'],
      ['V2 数据资格诊断', '已通过', '报告与重放逐字节一致：完整向量覆盖率98.59%，267个合格交易日，8项定义全部通过冻结门槛；6,491条五年拆股来源与旧正式证据重叠冲突为零。', 'met'],
      ['开发期筛选', '已完成', '4项 Alpha 全部失败；2项风险护栏通过，但因缺少 Alpha 而不能进入模型构建。', 'met'],
      ['精确复现', '已验证', '独立重放得到完全相同且经过审阅的结果，并保持正式数据、生产和外部请求写入为零。', 'met'],
      ['可复用研究输入', '1个面板已合格', '精确重放的市场状态面板已登记为结果盲复用输入；结果型面板和新的结果访问仍全部关闭。', 'met'],
      ['下一批因子发现', '冻结协议', '结果盲资格审查及精确重放已完成：2个 Alpha 交互和1个风险护栏进入下一步，1个 Alpha 设计在读取结果前停止。', 'active'],
      ['模型、策略与产品', '锁定', '目前仍没有预测模型、策略表达、个股候选权限或期权绩效主张。', 'locked'],
    ],
    cycle: '可持续因子发现循环', cycleNote: '整个研究计划可以持续迭代，但其中每一批研究都必须有限、去重、预登记、精确复现并永久计入试验账本。', cycleBadge: '持续研究系统 · 单批次有边界',
    cycleStats: ['运行模式', '当前阶段', '已完成批次', '已消耗正式试验', '下一批次'], cycleStatValues: ['持续循环', '协议 + Ledger V4', '2', '14', '3项试验 · 尚未登记'],
    cycleStages: [
      ['01', '提出假设并去重', '已完成', '共保留5个想法；4个进入下一步，1个近重复想法在任何结果访问前停止。'],
      ['02', '不读取结果地构建', '已完成', '106个交易日的正式报告与独立重放完全一致；3项设计通过，1项 Alpha 在读取结果前停止。'],
      ['03', '预登记并反证', '当前', '只登记2项 Alpha 和1项风险试验，并在 Ledger V4 中冻结结果、成本、重复检验、门槛、入选上限与停止规则。'],
      ['04', '重放、关闭并返回', '锁定', '攻击泄漏与稳定性，精确复现结果，追加全部失败，分流幸存证据，然后返回新假设入口。'],
    ],
    cycleCurrent: '当前位置', cycleCurrentValue: '3项设计 · 输入已合格', cycleCurrentBody: '2个候选 Alpha 交互和1个风险护栏通过冻结的结果盲门槛及精确重放；它们尚未登记为收益试验，也没有绩效结果。',
    cycleInfrastructure: '读取结果前停止', cycleInfrastructureValue: '1项 Alpha 设计被拒绝', cycleInfrastructureBody: '防御韧性的自然零点状态支持不平衡且过度集中，前半段尤其不足；审查后没有移动阈值进行补救。',
    cycleContinuity: '下一道边界', cycleContinuityValue: '协议 + Ledger V4', cycleContinuityBody: '只允许登记3项已合格设计。协议和累计账本冻结并获得单独授权前，开发期结果继续不可访问。',
    cycleInspect: '查看去重、预算、隔离与暂停规则',
    cycleGuardTitles: ['重复身份', '有限试验预算', '阶段隔离', '自动暂停'],
    cycleGuardBodies: [
      '从经济机制、信息集合与截止时点、公式、Universe、周期、参数邻域及相关假设家族七个维度判断是否重复。',
      '因子与交互数量、参数变体、周期、假设家族、重复检验方法、入选上限和停止规则必须全部冻结。',
      '提出想法和资格诊断阶段不能读取结果；只有新批次完成登记后才能打开开发期结果，验证集与留出集继续独立隔离。',
      '来源谱系不一致、阶段泄漏、超出试验预算、重放失败或密封分区泄漏会立即停止受影响批次，但不会抹去已有研究。',
    ],
    agentPilot: '阶段隔离的研究协作组', agentPilotNote: '人工监督的多 Agent 试点已完成市场状态资格、假设登记及结果盲输入资格审查。3项设计进入协议冻结，1项在读取结果前停止。', agentPilotBadge: '输入已合格 · 结果保持关闭',
    agentStats: ['市场状态资格', '输入精确重放', '合格设计', 'Validation / Holdout'], agentStatValues: ['通过 · 267 / 287', '完全一致 · 106 / 106', '3项 · 未读结果', '保持密封'],
    agentStages: [
      ['01', '独立审查', '已完成', '治理、方法和实现审查在真实运行前发现并修正了实质问题。'],
      ['02', '市场状态资格审查', '已完成', '287个交易日全部完成；重建宽度联合可用267日，独立规范字节重放完全一致。'],
      ['03', '假设与输入审查', '已完成', '5张假设卡已经冻结；3项设计通过精确结果盲资格审查，1项已接受 Alpha 设计被拒绝。'],
      ['04', '协议与账本冻结', '当前', '仅登记3项合格试验，并把全部评估和停止规则写入只追加的 Ledger V4。'],
      ['05', 'Development 评估', '锁定', '必须经单独审查和精确授权后，才可由唯一确定性执行边界开启。'],
      ['06', '重放、反证与人工裁决', '锁定', 'Agent 共识不能替代精确复现、确定性门槛或人工权限。'],
    ],
    agentRoles: '角色与访问权限', agentRoleNames: ['研究主控', '数据与证据', '假设审查', '实现', '评估', '反证', '审批与发布'],
    agentBoundary: '这不代表什么', agentBoundaryBody: '这不是无人监管的 Alpha 挖掘器。新的收益试验、模型、Validation、Holdout、候选权限、部署、券商或交易权限均未开放。',
    agentInspect: '查看角色隔离、串行阶段门与共享账本',
    foundation: '研究基础快照', foundationNote: '以下是已经在研究工作站完成核验并版本化的工程证据；每一项同时标明可用范围与证据边界。', foundationBadge: '证据核对 · 2026-09-15',
    foundationItems: [
      ['五年行情基础', '深度已完成', '连续日线行情与稳定证券身份的五年深度已经完成。', 'verified'],
      ['历史成员资格', '事后重建', '其中1,250个交易日为事后重建、3个为前瞻记录；重建历史不等于当时实录。', 'qualified'],
      ['公司行动', '部分证据', '第一策略4,643条暴露中4,623条已有精确事件日匹配；尚未证明其余空白均为中性。', 'qualified'],
      ['生命周期与终端', '参考边界已覆盖', '302条五日路径均已有精确或有限区间参考；参考证据仍不等于策略收益。', 'qualified'],
      ['点时基本面', '工程试点', '已登记4条SEC查询路径，并取得4个严格按当时可用信息投影的交易日；目前仅属工程证据。', 'qualified'],
    ],
    foundationControls: '已经冻结的评估约束', controlLabels: ['已登记规格', '时间顺序切分', '清洗期 + 隔离期', '单边成本情景', '封存样本外使用次数'],
    foundationBoundary: '不会把不同证据强行合成为一个“总完成度”。任何必需证据族不合格，绩效研究仍保持锁定。',
    factorQualification: '因子资格诊断 V2', factorQualificationNote: '8项因子已在工作站同一冻结总体上完整计算两次。精确重放只检验来源与实现是否合格，全程不读取未来收益。', factorQualificationBadge: '已通过 · 精确重放',
    factorStats: ['登记因子', '完整向量', '覆盖率', '成对核验', '近重复组'],
    factorCoverageMeaning: '437,402条声明路径中，431,249条形成完整的8因子向量；6,153条不完整路径继续明确保留，没有静默补零。覆盖率达到98.59%，267个合格交易日在冻结的前后时间段中分布为123 / 144。',
    factorRedundancy: '最强同日关系', factorRedundancyBody: '两个风险护栏之间的绝对加权 Spearman 关系最高，为0.8942；没有因子对满足完整的近重复规则。这只代表数据资格通过，并不代表存在预测价值。',
    factorRoles: '目录角色', factorRoleValues: ['4项候选 Alpha 测量', '1项形态条件因子', '1项适用性输入', '2项风险护栏'],
    factorInspect: '展开审阅8项登记定义与精确公式',
    factorRole: '角色', factorFormula: '精确公式', factorWindow: '点时数据窗口', factorExpectation: '登记关系',
    factorCutoffValue: '当日收盘数据完成 → 最早下一交易日开盘执行', factorMissingValue: '明确标为不可用 · 禁止静默补零',
    factorVerdict: 'V2 获得了什么资格', factorVerdictValue: '8 / 8 项可进入协议审查', factorVerdictBody: '4项候选 Alpha 测量、1项形态条件、1项适用性输入和2项风险护栏均通过覆盖、时间分布、取值、并列与冗余门槛。它们只是等待登记结果检验的测量，并非已获准因子。',
    factorNext: '资格诊断之后', factorNextValue: '筛选已完成 · 结论见下方', factorNextBody: '8项测量获得的是接受检验的资格，不是预设有效。正式筛选拒绝了所有候选 Alpha，并保持原资格报告不变。',
    factorLimits: '资格诊断边界', factorLimitsBody: '成员资格为事后重建而非当时实录；历史行业分类和充分的市场状态多样性尚未证明；日线不能观察点差或带方向订单流；即使重建数据通过资格，拆股空白是否中性仍作为来源限制公开保留。',
    screeningV2: '已完成开发期筛选 · 因子目录 V2', screeningV2Note: '这是预登记问题的不可变结论，不是为了外观挑选出来的回测。精确重放复现了全部结果和计数。', screeningV2Badge: '已关闭 · 精确重放',
    screeningV2Stats: ['正式试验', '累计试验', '信号交易日', '观察数', '前瞻标签'],
    screeningV2State: '候选 Alpha 结论', screeningV2StateValue: '0 / 4 获准', screeningV2StateBody: '4项候选 Alpha 均至少失败一个冻结门槛；已经看到结果后，不得再修补它们的公式或阈值。',
    screeningV2Selection: '风险证据', screeningV2SelectionValue: '2项通过 · 0项入选', screeningV2SelectionBody: '两项下行风险护栏均通过登记门槛，可以作为风险认识保留；但没有候选 Alpha 存活，因此都不能成为模型输入。',
    screeningV2Decisions: '6项登记决策', screeningV2DecisionLabels: ['稳健效应', '90%下界', 'Holm p 值', '失败门槛'], screeningV2Risk: '风险证据 · 未入选', screeningV2Rejected: '未通过',
    screeningV2Next: '下一项受控问题', screeningV2NextValue: '3项设计 · 冻结协议', screeningV2NextBody: '2个 Alpha 交互和1个风险护栏已通过106个交易日的结果盲输入门槛及精确重放；1项 Alpha 在读取结果前停止。任何开发期结果决策前，必须先冻结 Ledger V4。',
    screeningV2Inspect: '展开审阅冻结协议、来源链与报告身份', screeningV2Protocol: '冻结评估规则', screeningV2ProtocolBody: '主要股票结果3个交易日 · 1/5日衰减 · 同日秩 · 10,000次五日循环区块自助法 · V1门槛保持不变 · 4项Alpha与2项风险分别做Holm校正 · 单边0/10/25/50 bps成本诊断。', screeningV2Limits: '仍保持关闭的部分', screeningV2LimitsBody: '历史行业中性化和充分的市场状态多样性仍不可用。筛选仅属于事后重建开发期证据；验证集、留出集、模型、策略、个股候选、期权与交易继续锁定。',
    factorScreen: '历史开发期筛选 · 因子目录 V1', factorScreenNote: '这是保留的失败研究，不是当前项目。有限协议在读取结果前已经提交，并在同一开发样本上完整执行两次；没有候选 Alpha 通过。', factorScreenBadge: '失败留档 · 精确重放',
    factorScreenStats: ['正式假设', '信号交易日', '观察数', '前瞻标签', '入选 Alpha / 风险'],
    factorScreenOutcome: '真实结论', factorScreenOutcomeBody: '没有候选 Alpha 通过冻结门槛。因此因子目录 V1 在没有预测模型的状态下关闭，也不得改变个股候选排名。',
    factorScreenSelected: '保留的证据', factorScreenSelectedBody: '10日滚动最大回撤作为下行风险护栏通过：稳健秩效应0.2540，90%下界0.2322，Holm校正 p 值0.0003。它可以约束未来模型，但自身不是 Alpha。',
    factorScreenDecisions: '8项登记决策', factorScreenDecisionLabels: ['稳健效应', '90%下界', 'Holm p 值', '失败门槛'], factorScreenPassed: '保留风险护栏', factorScreenRejected: '未通过',
    factorScreenInspect: '展开审阅协议、保管、限制与报告身份',
    factorScreenProtocol: '冻结评估规则', factorScreenProtocolBody: '主要周期3个交易日；1日与5日用于衰减诊断；10,000次五日循环区块自助法；90%区间；Holm家族错误控制；单边0/10/25/50 bps成本情景。',
    factorScreenLimits: '解释边界', factorScreenLimitsBody: '仅限开发期；成员资格为事后重建；仅106个信号日；历史分类和充分的市场状态多样性未获证明；固定成本只是情景而非执行校准。验证集和留出集从未打开。',
    engineering: '历史方法工程证据', engineeringNote: '首个回撤方法已在工作站重建样本上完整运行两次，结果完全一致。以下保留事实只回答“该方法能否计算”，不回答“策略是否有效”。', engineeringBadge: '历史记录 · 不含结果',
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
    inspect: '展开审阅完整逻辑、公式、参数与评估设计',
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
    resultCards: [['因子目录 V2', '已关闭 · 无候选 Alpha'], ['因子筛选 V1', '已关闭 · 无候选 Alpha'], ['回撤研究项目', '已关闭 · 无稳定选择'], ['已激活模型', '无']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
  es: {
    eyebrow: 'Investigación de factores, modelos y estrategias · registro gobernado',
    title: 'Laboratorio de investigación cuantitativa',
    subtitle: 'El registro autoritativo de qué se mide, qué se modela, cómo se expresa una estrategia y en qué capa falla la evidencia.',
    status: 'DESCUBRIMIENTO DE FACTORES V2', statusValue: 'CERRADO · SIN ALPHA CANDIDATO',
    statusNote: 'El filtro congelado de seis pruebas y su reproducción exacta han concluido. Fallaron las cuatro medidas candidatas de Alpha; dos salvaguardas superaron sus propios criterios, pero no obtienen permiso de modelo sin Alpha.',
    coverage: 'Estado de la evidencia', coverageNote: 'La integridad del método y la eficacia del modelo son cuestiones distintas.',
    coverageBoundary: 'Publicar un método no convierte la estrategia en validada, adecuada para el mercado actual ni predictiva de rentabilidades de opciones.',
    submission: 'Se aceptan hipótesis refutables de factores o estrategias para su registro y evaluación independiente bajo el mismo proceso gobernado. Si una propuesta llega a un modelo utilizable y a un futuro uso comercial, WH Alpha contactará a la persona colaboradora y comunicará el resultado.',
    submissionContact: 'Contacto',
    readiness: 'Escalera de evidencia', readinessItems: [
      ['Arquitectura de tres capas', 'ACEPTADA', 'Descubrimiento de factores, Construcción del modelo y Expresión de estrategia tienen límites de versión y evidencia separados.', 'met'],
      ['Registro acumulativo de investigación', 'CERRADO · 14 PRUEBAS', 'Las ocho pruebas V1 y las seis V2 permanecen contabilizadas con resultados inmutables; no se eliminó ni renombró ningún fallo.', 'met'],
      ['Catálogo de factores V2', 'EVALUADO', 'Ocho definiciones exactas cubrieron continuación, reversión, momento del retorno, defensa, aplicabilidad de liquidez y riesgo bajista.', 'met'],
      ['Calificación de datos V2', 'SUPERADA', 'El informe y la reproducción son idénticos byte a byte: 98,59 % de vectores completos, 267 sesiones aptas y los ocho factores superan los filtros congelados; no hubo conflictos con la evidencia canónica previa.', 'met'],
      ['Selección en Desarrollo', 'COMPLETADA', 'Fallaron las cuatro pruebas Alpha. Dos salvaguardas superaron los criterios, pero la ausencia de Alpha impide pasar a Construcción del modelo.', 'met'],
      ['Reproducción exacta', 'VERIFICADA', 'La repetición independiente obtuvo el mismo resultado revisado, sin escrituras canónicas, de Producción ni solicitudes externas.', 'met'],
      ['Entradas de investigación reutilizables', '1 PANEL CALIFICADO', 'El panel de estado de mercado, reproducido exactamente, queda registrado para reutilización sin resultados. Los paneles con resultados y todo acceso nuevo siguen cerrados.', 'met'],
      ['Próxima campaña', 'CONGELAR PROTOCOLO', 'La calificación sin resultados y su reproducción exacta concluyeron: avanzan dos interacciones Alpha y una salvaguarda de riesgo; un diseño Alpha se detuvo antes de consultar resultados.', 'active'],
      ['Modelo, estrategia y Producto', 'BLOQUEADOS', 'No existe modelo predictivo, expresión de estrategia, autoridad sobre Candidatos ni afirmación sobre opciones.', 'locked'],
    ],
    cycle: 'Ciclo renovable de descubrimiento de factores', cycleNote: 'El programa puede continuar de forma indefinida. Cada campaña es finita, deduplicada, prerregistrada, reproducida y contabilizada de forma permanente.', cycleBadge: 'SISTEMA CONTINUO · CAMPAÑAS ACOTADAS',
    cycleStats: ['Modo operativo', 'Fase actual', 'Campañas concluidas', 'Pruebas formales consumidas', 'Próxima campaña'], cycleStatValues: ['RENOVABLE', 'PROTOCOLO + LEDGER V4', '2', '14', '3 PRUEBAS · NO REGISTRADAS'],
    cycleStages: [
      ['01', 'Proponer y deduplicar', 'COMPLETADA', 'Se conservaron cinco ideas: cuatro avanzaron y una casi duplicada se detuvo antes de consultar resultados.'],
      ['02', 'Construir sin resultados', 'COMPLETADA', 'El informe de 106 sesiones y la reproducción independiente coincidieron: tres diseños superaron los filtros y un Alpha se detuvo antes de consultar resultados.'],
      ['03', 'Registrar y refutar', 'ACTUAL', 'Registrar solo dos pruebas Alpha y una de riesgo, con resultados, costes, multiplicidad, criterios, límites y parada congelados en Ledger V4.'],
      ['04', 'Reproducir, cerrar y volver', 'BLOQUEADA', 'Atacar fugas y estabilidad, reproducir el resultado exacto, conservar cada fallo, encaminar supervivientes y volver a la entrada de hipótesis.'],
    ],
    cycleCurrent: 'Posición actual', cycleCurrentValue: '3 DISEÑOS · ENTRADAS CALIFICADAS', cycleCurrentBody: 'Dos interacciones Alpha candidatas y una salvaguarda de riesgo superaron los filtros sin resultados y la reproducción exacta. Aún no son pruebas formales ni tienen métricas de rendimiento.',
    cycleInfrastructure: 'Detenido antes de resultados', cycleInfrastructureValue: '1 DISEÑO ALPHA RECHAZADO', cycleInfrastructureBody: 'La resiliencia defensiva carecía de soporte equilibrado alrededor de cero y estaba demasiado concentrada, también en la primera mitad. No se movió el umbral tras inspeccionarla.',
    cycleContinuity: 'Siguiente frontera', cycleContinuityValue: 'PROTOCOLO + LEDGER V4', cycleContinuityBody: 'Solo pueden registrarse los tres diseños calificados. Desarrollo sigue inaccesible hasta congelar protocolo y registro acumulativo y obtener autorización separada.',
    cycleInspect: 'Examinar deduplicación, presupuesto, aislamiento y pausas',
    cycleGuardTitles: ['Identidad de duplicados', 'Presupuesto finito', 'Aislamiento por etapas', 'Pausa automática'],
    cycleGuardBodies: [
      'La novedad se revisa por mecanismo, información y corte, fórmula, universo, horizonte, vecindad de parámetros y familia de hipótesis relacionada.',
      'Deben congelarse el número de factores e interacciones, variantes, horizontes, familias, multiplicidad, límite de selección y regla de parada.',
      'Las fases de ideas y calificación no pueden leer resultados. Desarrollo se abre solo para una campaña nueva registrada; Validación y Holdout siguen separados.',
      'Una discrepancia de linaje, fuga entre etapas, exceso de presupuesto, fallo de reproducción o ruptura de una partición sellada detiene la campaña afectada.',
    ],
    agentPilot: 'Equipo de investigación aislado por etapas', agentPilotNote: 'El piloto multiagente supervisado completó mercado, hipótesis y calificación de entradas sin resultados. Tres diseños pasan a congelar protocolo y uno se detuvo antes de consultar resultados.', agentPilotBadge: 'ENTRADAS CALIFICADAS · RESULTADOS CERRADOS',
    agentStats: ['Calificación de mercado', 'Reproducción de entradas', 'Diseños calificados', 'Validación / Holdout'], agentStatValues: ['SUPERADA · 267 / 287', 'COINCIDE · 106 / 106', '3 · SIN RESULTADOS', 'SELLADOS'],
    agentStages: [
      ['01', 'Revisiones independientes', 'COMPLETADO', 'Las revisiones de gobierno, método e implementación detectaron y corrigieron defectos reales antes de ejecutar datos.'],
      ['02', 'Calificación del estado de mercado', 'COMPLETADA', 'Se evaluaron las 287 sesiones; la amplitud reconstruida estuvo disponible conjuntamente en 267 y la reproducción independiente coincidió byte a byte.'],
      ['03', 'Hipótesis y revisión de entradas', 'COMPLETADA', 'Se congelaron cinco fichas; tres diseños superaron la calificación exacta sin resultados y un Alpha aceptado fue rechazado.'],
      ['04', 'Congelar protocolo y registro', 'ACTUAL', 'Registrar solo las tres pruebas calificadas y todas las reglas de evaluación y parada en Ledger V4.'],
      ['05', 'Evaluación de Desarrollo', 'BLOQUEADA', 'Un único límite de ejecución determinista solo puede abrirse tras revisión y autorización exacta separadas.'],
      ['06', 'Reproducción, ataque y decisión humana', 'BLOQUEADO', 'El consenso de agentes no sustituye la reproducción exacta, las puertas deterministas ni la autoridad humana.'],
    ],
    agentRoles: 'Mapa de roles y acceso', agentRoleNames: ['Control de investigación', 'Datos y evidencia', 'Revisión de hipótesis', 'Implementación', 'Evaluación', 'Equipo adversarial', 'Aprobación y publicación'],
    agentBoundary: 'Lo que esto no significa', agentBoundaryBody: 'No es un minero de Alpha autónomo. No se ha abierto ninguna nueva prueba de retorno, modelo, Validación, Holdout, autoridad de Candidatos, despliegue, bróker ni negociación.',
    agentInspect: 'Examinar aislamiento, puertas seriales y contabilidad compartida',
    foundation: 'Resumen de la base de investigación', foundationNote: 'Evidencia verificada y versionada que ya existe en la estación de trabajo de investigación. Cada punto indica tanto su utilidad como su límite.', foundationBadge: 'EVIDENCIA REVISADA · 15 SEP 2026',
    foundationItems: [
      ['Base de mercado a cinco años', 'PROFUNDIDAD COMPLETA', 'La profundidad continua de precios diarios e identidad estable está completa.', 'verified'],
      ['Composición histórica', 'RECONSTRUIDA', '1.250 sesiones son reconstruidas y tres son prospectivas; la reconstrucción no equivale a un registro operativo de la fecha.', 'qualified'],
      ['Acciones corporativas', 'EVIDENCIA PARCIAL', '4.623 de 4.643 exposiciones del primer estudio tienen fecha de evento exacta; no se ha demostrado la neutralidad de las ausencias.', 'qualified'],
      ['Ciclo de vida y terminal', 'REFERENCIAS ACOTADAS', 'Las 302 trayectorias disponen de una referencia exacta o de intervalo finito; una referencia no es un resultado de estrategia.', 'qualified'],
      ['Fundamentales a fecha de conocimiento', 'PILOTO DE INGENIERÍA', 'Existen cuatro consultas SEC registradas y cuatro sesiones con proyección estricta según la información disponible entonces; sigue siendo evidencia de ingeniería.', 'qualified'],
    ],
    foundationControls: 'Controles de evaluación ya congelados', controlLabels: ['Especificaciones registradas', 'División cronológica', 'Purga + embargo', 'Escenarios de costes por lado', 'Uso del holdout sellado'],
    foundationBoundary: 'Estos hechos no se combinan en un único porcentaje de avance. Una familia de evidencia obligatoria insuficiente mantiene bloqueada la investigación de rendimiento.',
    factorQualification: 'Calificación de factores V2', factorQualificationNote: 'El catálogo de ocho factores se calculó dos veces sobre la misma población congelada en la estación de trabajo. La reproducción exacta evalúa solo la aptitud de las fuentes y de la implementación; nunca consulta rendimientos futuros.', factorQualificationBadge: 'SUPERADA · REPRODUCCIÓN EXACTA',
    factorStats: ['Factores registrados', 'Vectores completos', 'Cobertura', 'Pares revisados', 'Grupos casi duplicados'],
    factorCoverageMeaning: 'De 437.402 trayectorias declaradas, 431.249 produjeron vectores completos de ocho factores. Las 6.153 incompletas siguen explícitas, sin rellenarlas con cero. La disponibilidad alcanzó el 98,59 % en 267 sesiones aptas, repartidas 123 / 144 entre las dos mitades cronológicas congeladas.',
    factorRedundancy: 'Relación contemporánea más intensa', factorRedundancyBody: 'La mayor relación de Spearman ponderada en valor absoluto fue 0,8942 entre las dos salvaguardas de riesgo. Ningún par cumplió la regla completa de casi duplicado. Esto supera una prueba de datos, pero no demuestra capacidad predictiva.',
    factorRoles: 'Funciones del catálogo', factorRoleValues: ['4 medidas candidatas de Alpha', '1 condicionante de configuración', '1 variable de aplicabilidad', '2 salvaguardas de riesgo'],
    factorInspect: 'Examinar las ocho definiciones registradas y sus fórmulas exactas',
    factorRole: 'Función', factorFormula: 'Fórmula exacta', factorWindow: 'Ventana point-in-time', factorExpectation: 'Relación registrada',
    factorCutoffValue: 'cierre completo de la sesión → primera ejecución en la apertura siguiente', factorMissingValue: 'ausencia explícita · nunca se rellena con cero',
    factorVerdict: 'Qué habilitó V2', factorVerdictValue: '8 / 8 aptos para revisar el protocolo', factorVerdictBody: 'Las cuatro medidas candidatas de Alpha, un condicionante, una variable de aplicabilidad y dos salvaguardas superaron cobertura, cronología, variación, empates y redundancia. Son mediciones pendientes de una prueba registrada, no factores admitidos.',
    factorNext: 'Después de la calificación', factorNextValue: 'FILTRO COMPLETADO · DECISIÓN ABAJO', factorNextBody: 'Las ocho mediciones obtuvieron permiso para ser evaluadas, no una presunción de utilidad. El filtro rechazó todos los candidatos de Alpha y conservó intacta la calificación.',
    factorLimits: 'Límites de la calificación', factorLimitsBody: 'La composición está reconstruida y no registrada tal como se operó; la clasificación histórica y una diversidad amplia de regímenes no están demostradas; las barras diarias no observan diferenciales ni flujo firmado; la neutralidad de ausencias de splits sigue declarada como limitación incluso tras la calificación.',
    screeningV2: 'Selección de Desarrollo completada · Catálogo V2', screeningV2Note: 'Este es el resultado inmutable de la pregunta preinscrita, no un backtest elegido por su apariencia. La reproducción exacta coincidió en todos los resultados y recuentos.', screeningV2Badge: 'CERRADO · REPRODUCCIÓN EXACTA',
    screeningV2Stats: ['Pruebas formales', 'Pruebas acumuladas', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras'],
    screeningV2State: 'Decisión sobre Alpha', screeningV2StateValue: '0 / 4 admitidos', screeningV2StateBody: 'Las cuatro medidas candidatas de Alpha fallaron al menos un criterio congelado. Sus fórmulas y umbrales no pueden repararse después de observar los resultados.',
    screeningV2Selection: 'Evidencia de riesgo', screeningV2SelectionValue: '2 calificadas · 0 seleccionadas', screeningV2SelectionBody: 'Las dos salvaguardas bajistas superaron sus criterios. Se conservan como evidencia, pero no pasan a ser entradas de modelo porque ningún Alpha sobrevivió.',
    screeningV2Decisions: 'Las seis decisiones registradas', screeningV2DecisionLabels: ['Efecto robusto', 'Límite inferior 90 %', 'p de Holm', 'Filtros fallidos'], screeningV2Risk: 'Evidencia de riesgo · no seleccionada', screeningV2Rejected: 'Rechazado',
    screeningV2Next: 'Siguiente pregunta gobernada', screeningV2NextValue: '3 DISEÑOS · CONGELAR PROTOCOLO', screeningV2NextBody: 'Dos interacciones Alpha y una salvaguarda superaron los filtros sin resultados de 106 sesiones y la reproducción exacta; un Alpha se detuvo antes de resultados. Ledger V4 debe congelarse antes de decidir cualquier acceso a Desarrollo.',
    screeningV2Inspect: 'Examinar el protocolo, linaje e identidad del informe', screeningV2Protocol: 'Evaluación congelada', screeningV2ProtocolBody: 'Resultado principal a 3 sesiones · decaimiento a 1/5 · rangos por sesión · 10.000 réplicas bootstrap con bloques circulares de cinco sesiones · filtros V1 sin cambios · Holm en familias de 4 Alpha y 2 riesgos · diagnósticos de 0/10/25/50 pb por lado.', screeningV2Limits: 'Qué permanece cerrado', screeningV2LimitsBody: 'No se dispone de neutralización sectorial histórica ni de diversidad amplia de regímenes. Solo es evidencia reconstruida de Desarrollo; Validación, Holdout, modelo, estrategia, Candidatos, opciones y negociación siguen bloqueados.',
    factorScreen: 'Selección histórica en Desarrollo · Catálogo V1', factorScreenNote: 'Investigación fallida conservada, no la campaña actual. El protocolo finito se confirmó antes de consultar resultados y se ejecutó dos veces sobre la misma cohorte; ningún candidato de Alpha superó los filtros.', factorScreenBadge: 'FALLO CONSERVADO · REPRODUCCIÓN EXACTA',
    factorScreenStats: ['Hipótesis formales', 'Sesiones de señal', 'Observaciones', 'Etiquetas futuras', 'Alpha / riesgo seleccionados'],
    factorScreenOutcome: 'Resultado sin adornos', factorScreenOutcomeBody: 'Ningún candidato de Alpha superó los filtros congelados. El Catálogo V1 se cierra sin modelo predictivo y no puede modificar la clasificación de acciones.',
    factorScreenSelected: 'Evidencia conservada', factorScreenSelectedBody: 'La máxima caída móvil de 10 sesiones superó los filtros como salvaguarda bajista: efecto robusto de rango 0,2540, límite inferior del 90 % de 0,2322 y p de Holm 0,0003. Puede limitar un modelo futuro; por sí sola no es Alpha.',
    factorScreenDecisions: 'Las ocho decisiones registradas', factorScreenDecisionLabels: ['Efecto robusto', 'Límite inferior 90 %', 'p de Holm', 'Filtros fallidos'], factorScreenPassed: 'Salvaguarda conservada', factorScreenRejected: 'Rechazado',
    factorScreenInspect: 'Examinar protocolo, custodia, límites e identidad exacta',
    factorScreenProtocol: 'Evaluación congelada', factorScreenProtocolBody: 'Horizonte principal: 3 sesiones; diagnósticos de decaimiento: 1 y 5; 10.000 réplicas bootstrap con bloques circulares de cinco sesiones; intervalos del 90 %; control familiar de Holm; costes de 0/10/25/50 pb por lado.',
    factorScreenLimits: 'Límite de interpretación', factorScreenLimitsBody: 'Solo Desarrollo; composición reconstruida; 106 sesiones de señal; clasificación histórica y diversidad amplia de regímenes no demostradas; los costes fijos son escenarios, no calibración de ejecución. Validación y Holdout nunca se abrieron.',
    engineering: 'Evidencia histórica de ingeniería', engineeringNote: 'El primer método Pullback se ejecutó dos veces sobre la población reconstruida en la estación de trabajo y produjo resultados idénticos. Estos datos conservados indican si aquel método podía calcularse, no si funcionaba.', engineeringBadge: 'HISTÓRICA · SIN RESULTADOS',
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
    inspect: 'Examinar la lógica completa, las fórmulas, los parámetros y la evaluación',
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
    resultCards: [['Catálogo de factores V2', 'Cerrado · sin candidato de Alpha'], ['Selección de factores V1', 'Cerrada · sin candidato de Alpha'], ['Programa Pullback', 'Cerrado · sin selección estable'], ['Modelos activos', 'Ninguno']],
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
    numberFormat.format(factorScreeningV2.signal_session_count),
    numberFormat.format(factorScreeningV2.observation_count),
    numberFormat.format(factorScreeningV2.label_count),
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
        {c.cycleStages.map(([index, title, state, body], stageIndex) => <li className={stageIndex < 2 ? 'done' : stageIndex === 2 ? 'current' : 'blocked'} key={title}><i>{stageIndex < 2 ? '✓' : stageIndex === 2 ? '●' : '→'}</i><strong>{index} · {title}</strong><small>{state} · {body}</small></li>)}
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
        {c.agentStages.map(([index, title, state, body], stageIndex) => <li className={stageIndex < 3 ? 'done' : stageIndex === 3 ? 'current' : 'blocked'} key={title}><i>{stageIndex < 3 ? '✓' : stageIndex === 3 ? '●' : '→'}</i><strong>{index} · {title}</strong><small>{state} · {body}</small></li>)}
      </ol>
      <div className="research-engineering-boundary"><strong>{c.agentBoundary}</strong><p>{c.agentBoundaryBody}</p></div>
      <details className="research-factor-details research-screen-details">
        <summary>{c.agentInspect}</summary>
        <div className="research-screen-protocol research-agent-role-grid">
          {multiAgentGovernance.role_policies.map((role, index) => <article key={role.role_id}><strong>{c.agentRoleNames[index]}</strong><p>{humanize(role.maximum_data_access)} · {humanize(role.required_handoff)}</p></article>)}
        </div>
      </details>
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
        <div className="research-model-heading"><div><h3>{modelName}</h3><p>{modelRecord.hypothesis}</p></div><div className="research-model-badges"><b>{c.methodOnly}</b><b>{c.noCandidate}</b><b>{c.notAssessed}</b></div></div>
        <dl className="research-model-facts">
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

        <div className="research-record-section"><h3>{c.features}</h3><div className="research-feature-grid">{modelRecord.feature_disclosures.map((feature) => <article key={feature.feature_id}><header><span>{humanize(feature.role)}</span><strong>{humanize(feature.feature_id)}</strong></header><code>{feature.exact_formula}</code><dl><div><dt>{c.source}</dt><dd>{humanize(feature.requirement_source_family)} → {feature.raw_source_families.map(humanize).join(' + ')} · {feature.source_fields.map(humanize).join(', ')}</dd></div><div><dt>{c.cutoff}</dt><dd>{humanize(feature.availability_cutoff)}</dd></div><div><dt>{c.lookback}</dt><dd>{feature.lookback_sessions} {c.sessions}</dd></div><div><dt>{c.transform}</dt><dd>{humanize(feature.transform)}</dd></div><div><dt>{c.expected}</dt><dd>{humanize(feature.expected_direction)}</dd></div><div><dt>{c.missing}</dt><dd>{humanize(feature.missingness_rule)}</dd></div></dl></article>)}</div></div>

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
      </details>
    </section>

    <section className="research-card research-lifecycle"><header><span>08</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>09</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
