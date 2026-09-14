import modelRecord from '../modelRecords/quant-research-lab-model-record-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const COPY = {
  en: {
    eyebrow: 'Personal model research · governed registry',
    title: 'Quant Research Lab',
    subtitle: 'The authoritative record of model logic, exact formulas, validation evidence, failure, and lifecycle—not a catalogue of polished backtests.',
    status: 'DATA BLOCKED', statusValue: 'METHOD ONLY',
    statusNote: 'The method is registered and inspectable. No real evaluation, performance claim, or Candidate authority exists.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    readiness: 'Evidence ladder', readinessItems: [
      ['Method specification', 'FROZEN', 'The hypothesis, formulas, 24-combination budget, chronology, costs, and gates are versioned.', 'met'],
      ['Deterministic implementation', 'REPLAYED', 'One shared feature calculator and fail-closed cohort logic passed full regression and exact replay.', 'met'],
      ['Reconstructed method coverage', '95.38%', '417,209 of 437,402 declared paths are computable for method diagnostics only.', 'met'],
      ['Performance-grade admission', 'BLOCKED', 'Membership, lifecycle, adjustments, terminal outcomes, costs, and sealed evaluation are not fully admitted.', 'blocked'],
      ['Results & Candidate authority', 'LOCKED', 'No return metrics, selected parameters, validated rank, or Candidate activation exists.', 'locked'],
    ],
    foundation: 'Research foundation snapshot', foundationNote: 'Verified, versioned evidence already built on Dell. Each item states both its useful scope and its limit.', foundationBadge: 'EVIDENCE REVIEWED · 14 SEP 2026',
    foundationItems: [
      ['Five-year market base', 'DEPTH COMPLETE', 'Contiguous EOD price and stable-identity depth are complete.', 'verified'],
      ['Historical membership', 'RECONSTRUCTED', '1,250 sessions are reconstructed and three are prospective; reconstructed history is not as operated.', 'qualified'],
      ['Corporate actions', 'PARTIAL EVIDENCE', '4,623 of 4,643 first-strategy exposures have exact event-date assignments; absence neutrality is not proven.', 'qualified'],
      ['Lifecycle & terminal', 'INCOMPLETE', 'Reference evidence covers 47 of 65 securities and 214 of 302 five-session paths; references are not outcomes.', 'blocked'],
      ['Point-in-time fundamentals', 'ENGINEERING PILOT', 'Four registered SEC query paths and four strict as-operated projection sessions exist; this is engineering evidence only.', 'qualified'],
    ],
    foundationControls: 'Evaluation controls already frozen', controlLabels: ['Registered specifications', 'Chronological split', 'Purge + embargo', 'Cost scenarios per side', 'Sealed holdout use'],
    foundationBoundary: 'These facts are not blended into one readiness percentage. A weak mandatory evidence family keeps performance research locked.',
    engineering: 'Method-engineering evidence', engineeringNote: 'The same registered method was run twice over the reconstructed Dell population with identical fingerprints. These facts answer whether the method can be computed—not whether it works.', engineeringBadge: 'REPLAYED · OUTCOME BLIND',
    engineeringStages: ['Method frozen', 'Implementation tested', 'Population replayed', 'Performance admission'], verified: 'Verified', blockedState: 'Blocked',
    declaredSessions: 'Declared sessions', completeSessions: 'Feature-complete sessions', declaredPaths: 'Declared paths', computablePaths: 'Computable paths', excludedPaths: 'Explicit exclusions',
    coverageMeaning: '95.38% is method-computability coverage—not win rate, prediction accuracy, or return.',
    proxyBoundary: 'What remains provisional', proxyBody: 'Membership is reconstructed rather than as operated; split adjustment has unproven neutral rows; Regime is recomputed; and no Stress-state path appears in this interval.',
    owner: 'Research ownership', ownerValue: 'WH Alpha personal quantitative research',
    boundary: 'Authority boundary', boundaryBody: 'The Lab owns research evidence. Stock Candidates may later consume only one to three separately validated and explicitly activated models.',
    registry: 'Registered model', featured: 'Featured research record',
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
    lifecycle: 'Promotion path', stages: ['Method registered', 'Data qualification', 'Validation', 'Sealed holdout', 'Validated research', 'Shadow', 'Active'],
    current: 'Current', locked: 'Locked', blocked: 'Blocked by evidence',
    results: 'Results workspace', resultsNote: 'Intentionally unavailable—no synthetic substitute and no implied performance',
    resultCards: [['Net expectancy', 'No real event study'], ['Uncertainty & stability', 'No qualified sample'], ['Win / payoff / PF', 'No qualified sample'], ['Portfolio AR / Sharpe / MDD', 'Portfolio not defined']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '个人模型研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '模型逻辑、完整公式、验证证据、失败记录与生命周期的权威档案，而不是陈列漂亮回测的页面。',
    status: '数据尚未达标', statusValue: '仅有方法档案',
    statusNote: '方法已登记并可完整审阅；目前没有真实评估、绩效主张或候选排名权限。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    readiness: '证据阶梯', readinessItems: [
      ['方法规范', '已冻结', '假设、公式、24组参数预算、时间切分、成本与门槛均已版本化。', 'met'],
      ['确定性实现', '已重放', '共享特征计算器与保守拒绝的分组逻辑已通过完整回归和精确重放。', 'met'],
      ['重建样本方法覆盖', '95.38%', '437,402条声明路径中有417,209条可用于方法诊断，仅限方法工程。', 'met'],
      ['绩效级数据准入', '仍阻塞', '成员资格、生命周期、复权、终端收益、成本与封存评估尚未全部准入。', 'blocked'],
      ['结果与候选权限', '锁定', '目前没有收益指标、优选参数、已验证排名或个股候选激活。', 'locked'],
    ],
    foundation: '研究基础快照', foundationNote: '以下是已经在戴尔完成核验并版本化的工程证据；每一项同时标明可用范围与证据边界。', foundationBadge: '证据核对 · 2026-09-14',
    foundationItems: [
      ['五年行情基础', '深度已完成', '连续日线行情与稳定证券身份的五年深度已经完成。', 'verified'],
      ['历史成员资格', '事后重建', '其中1,250个交易日为事后重建、3个为前瞻记录；重建历史不等于当时实录。', 'qualified'],
      ['公司行动', '部分证据', '第一策略4,643条暴露中4,623条已有精确事件日匹配；尚未证明其余空白均为中性。', 'qualified'],
      ['生命周期与终端', '尚未完整', '65只终端证券中47只、302条五日路径中214条有参考证据；参考证据不等于终端收益。', 'blocked'],
      ['点时基本面', '工程试点', '已登记4条SEC查询路径，并取得4个严格按当时可用信息投影的交易日；目前仅属工程证据。', 'qualified'],
    ],
    foundationControls: '已经冻结的评估约束', controlLabels: ['已登记规格', '时间顺序切分', '清洗期 + 隔离期', '单边成本情景', '封存样本外使用次数'],
    foundationBoundary: '不会把不同证据强行合成为一个“总完成度”。任何必需证据族不合格，绩效研究仍保持锁定。',
    engineering: '方法工程证据', engineeringNote: '同一已登记方法已在戴尔重建样本上完整运行两次，结果指纹完全一致。以下事实只回答“方法能否计算”，不回答“策略是否有效”。', engineeringBadge: '已重放 · 不含结果',
    engineeringStages: ['方法已冻结', '实现测试通过', '总体重放完成', '绩效数据准入'], verified: '已核验', blockedState: '仍阻塞',
    declaredSessions: '声明交易日', completeSessions: '特征完整交易日', declaredPaths: '声明路径', computablePaths: '可计算路径', excludedPaths: '明确排除',
    coverageMeaning: '95.38% 是方法可计算路径覆盖率，不是胜率、预测准确率或收益率。',
    proxyBoundary: '仍属临时证据的部分', proxyBody: '成员资格是事后重建而非当时实录；拆股复权仍有未证明的中性空白；Regime 为重新计算；该区间没有 Stress 状态路径。',
    owner: '研究归属', ownerValue: 'WH Alpha 个人量化研究',
    boundary: '权限边界', boundaryBody: '实验室负责研究证据；个股候选未来只能消费一至三个分别通过验证并明确激活的模型。',
    registry: '已登记模型', featured: '当前重点研究档案',
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
    lifecycle: '晋级路径', stages: ['方法已登记', '数据资格审查', '验证', '封存样本外', '研究验证通过', '影子运行', '正式激活'],
    current: '当前', locked: '锁定', blocked: '受证据阻塞',
    results: '结果工作区', resultsNote: '有意保持不可用——不使用合成替代，也不暗示任何绩效',
    resultCards: [['净期望值', '没有真实事件研究'], ['不确定性与稳定性', '没有合格样本'], ['胜率 / 盈亏比 / PF', '没有合格样本'], ['组合 AR / Sharpe / MDD', '尚未定义组合']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
  es: {
    eyebrow: 'Investigación de modelos propios · registro gobernado',
    title: 'Laboratorio de investigación cuantitativa',
    subtitle: 'El registro autoritativo de la lógica, las fórmulas exactas, la evidencia de validación, los fallos y el ciclo de vida de cada modelo; no un catálogo de backtests seleccionados por su atractivo.',
    status: 'DATOS INSUFICIENTES', statusValue: 'SOLO MÉTODO',
    statusNote: 'El método está registrado y puede examinarse. No existe una evaluación real, una afirmación de rendimiento ni autoridad sobre Candidatos.',
    coverage: 'Estado de la evidencia', coverageNote: 'La integridad del método y la eficacia del modelo son cuestiones distintas.',
    coverageBoundary: 'Publicar un método no convierte la estrategia en validada, adecuada para el mercado actual ni predictiva de rentabilidades de opciones.',
    readiness: 'Escalera de evidencia', readinessItems: [
      ['Especificación del método', 'CONGELADA', 'La hipótesis, las fórmulas, el presupuesto de 24 combinaciones, la cronología, los costes y los criterios están versionados.', 'met'],
      ['Implementación determinista', 'REPRODUCIDA', 'El cálculo común de características y la lógica de cohortes conservadora superaron la regresión y la reproducción exacta.', 'met'],
      ['Cobertura metodológica reconstruida', '95,38 %', 'Son computables 417.209 de 437.402 trayectorias declaradas, exclusivamente para diagnóstico del método.', 'met'],
      ['Admisión para medir rendimiento', 'BLOQUEADA', 'Composición, ciclo de vida, ajustes, resultados terminales, costes y evaluación sellada aún no están plenamente admitidos.', 'blocked'],
      ['Resultados y autoridad en Candidatos', 'BLOQUEADOS', 'No hay métricas de rentabilidad, parámetros elegidos, clasificación validada ni activación en Candidatos.', 'locked'],
    ],
    foundation: 'Resumen de la base de investigación', foundationNote: 'Evidencia verificada y versionada que ya existe en Dell. Cada punto indica tanto su utilidad como su límite.', foundationBadge: 'EVIDENCIA REVISADA · 14 SEP 2026',
    foundationItems: [
      ['Base de mercado a cinco años', 'PROFUNDIDAD COMPLETA', 'La profundidad continua de precios diarios e identidad estable está completa.', 'verified'],
      ['Composición histórica', 'RECONSTRUIDA', '1.250 sesiones son reconstruidas y tres son prospectivas; la reconstrucción no equivale a un registro operativo de la fecha.', 'qualified'],
      ['Acciones corporativas', 'EVIDENCIA PARCIAL', '4.623 de 4.643 exposiciones del primer estudio tienen fecha de evento exacta; no se ha demostrado la neutralidad de las ausencias.', 'qualified'],
      ['Ciclo de vida y terminal', 'INCOMPLETO', 'Hay referencias para 47 de 65 valores y 214 de 302 trayectorias a cinco sesiones; una referencia no es un resultado terminal.', 'blocked'],
      ['Fundamentales a fecha de conocimiento', 'PILOTO DE INGENIERÍA', 'Existen cuatro consultas SEC registradas y cuatro sesiones con proyección estricta según la información disponible entonces; sigue siendo evidencia de ingeniería.', 'qualified'],
    ],
    foundationControls: 'Controles de evaluación ya congelados', controlLabels: ['Especificaciones registradas', 'División cronológica', 'Purga + embargo', 'Escenarios de costes por lado', 'Uso del holdout sellado'],
    foundationBoundary: 'Estos hechos no se combinan en un único porcentaje de avance. Una familia de evidencia obligatoria insuficiente mantiene bloqueada la investigación de rendimiento.',
    engineering: 'Evidencia de ingeniería del método', engineeringNote: 'El mismo método registrado se ejecutó dos veces sobre la población reconstruida en Dell y produjo huellas idénticas. Estos datos indican si puede calcularse, no si funciona.', engineeringBadge: 'REPRODUCIDO · SIN RESULTADOS',
    engineeringStages: ['Método congelado', 'Implementación probada', 'Población reproducida', 'Admisión de rendimiento'], verified: 'Verificado', blockedState: 'Bloqueada',
    declaredSessions: 'Sesiones declaradas', completeSessions: 'Sesiones con características completas', declaredPaths: 'Trayectorias declaradas', computablePaths: 'Trayectorias computables', excludedPaths: 'Exclusiones explícitas',
    coverageMeaning: 'El 95,38 % mide cobertura de cálculo del método; no es tasa de acierto, precisión predictiva ni rentabilidad.',
    proxyBoundary: 'Qué sigue siendo provisional', proxyBody: 'La composición está reconstruida y no registrada tal como se operó; hay filas neutrales de ajustes sin demostrar; el régimen se recalculó; y el intervalo no contiene trayectorias en estado Stress.',
    owner: 'Titularidad de la investigación', ownerValue: 'Investigación cuantitativa propia de WH Alpha',
    boundary: 'Límite de autoridad', boundaryBody: 'El Laboratorio custodia la evidencia de investigación. Candidatos solo podrá consumir en el futuro entre uno y tres modelos validados por separado y activados explícitamente.',
    registry: 'Modelo registrado', featured: 'Registro de investigación destacado',
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
    lifecycle: 'Ruta de promoción', stages: ['Método registrado', 'Calificación de datos', 'Validación', 'Holdout sellado', 'Investigación validada', 'Sombra', 'Activo'],
    current: 'Actual', locked: 'Bloqueado', blocked: 'Bloqueado por la evidencia',
    results: 'Espacio de resultados', resultsNote: 'No disponible de forma intencionada: sin sustitutos sintéticos ni rendimiento implícito',
    resultCards: [['Expectativa neta', 'Sin estudio real de eventos'], ['Incertidumbre y estabilidad', 'Sin muestra apta'], ['Aciertos / payoff / PF', 'Sin muestra apta'], ['AR / Sharpe / MDD de cartera', 'Cartera no definida']],
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
  const modelName = locale === 'zh' ? modelRecord.display_name_zh : modelRecord.display_name;
  const evaluation = modelRecord.evaluation_design;
  const engineering = modelRecord.method_engineering_evidence;
  const numberFormat = new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US');
  const foundationValues = [
    numberFormat.format(1_255),
    `${numberFormat.format(1_253)} / ${numberFormat.format(1_255)}`,
    `${numberFormat.format(4_623)} / ${numberFormat.format(4_643)}`,
    '47 / 65',
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

    <section className="research-readiness" aria-labelledby="research-readiness-title"><header><span>00</span><h2 id="research-readiness-title">{c.readiness}</h2></header><div>{c.readinessItems.map(([name, state, body, tone]) => <article className={`research-readiness-${tone}`} key={name}><span>{state}</span><strong>{name}</strong><p>{body}</p></article>)}</div></section>

    <section className="research-card research-foundation" aria-labelledby="research-foundation-title">
      <header><span>01</span><div><h2 id="research-foundation-title">{c.foundation}</h2><p>{c.foundationNote}</p></div><b>{c.foundationBadge}</b></header>
      <div className="research-foundation-grid">
        {c.foundationItems.map(([name, state, body, tone], index) => <article className={`research-foundation-${tone}`} key={name}><div><strong>{foundationValues[index]}</strong><b>{state}</b></div><h3>{name}</h3><p>{body}</p></article>)}
      </div>
      <div className="research-foundation-controls"><strong>{c.foundationControls}</strong><div>{evaluationControls.map(([value, label]) => <span key={label}><b>{value}</b><small>{label}</small></span>)}</div></div>
      <p className="research-foundation-boundary">{c.foundationBoundary}</p>
    </section>

    <section className="research-card research-engineering-evidence" aria-labelledby="research-engineering-title">
      <header><span>02</span><div><h2 id="research-engineering-title">{c.engineering}</h2><p>{c.engineeringNote}</p></div><b>{c.engineeringBadge}</b></header>
      <ol className="research-engineering-rail">{c.engineeringStages.map((stage, index) => <li className={index < 3 ? 'done' : 'blocked'} key={stage}><i>{index < 3 ? '✓' : '!'}</i><strong>{stage}</strong><small>{index < 3 ? c.verified : c.blockedState}</small></li>)}</ol>
      <div className="research-engineering-stats">
        {[[c.declaredSessions, engineering.session_count], [c.completeSessions, engineering.complete_feature_session_count], [c.declaredPaths, engineering.expected_path_count], [c.computablePaths, engineering.complete_observation_count], [c.excludedPaths, engineering.excluded_path_count]].map(([label, value]) => <article key={label}><span>{label}</span><strong>{numberFormat.format(Number(value))}</strong></article>)}
      </div>
      <p className="research-engineering-meaning"><strong>{locale === 'es' ? '95,38 %' : '95.38%'}</strong>{c.coverageMeaning}</p>
      <div className="research-engineering-boundary"><strong>{c.proxyBoundary}</strong><p>{c.proxyBody}</p></div>
    </section>

    <section className="research-boundary-grid"><article><span>{c.owner}</span><strong>{c.ownerValue}</strong></article><article><span>{c.boundary}</span><p>{c.boundaryBody}</p></article></section>

    <section className="research-card research-model-registry" aria-labelledby="research-model-title">
      <header><span>03</span><div><h2 id="research-model-title">{c.registry}</h2><p>{c.featured}</p></div></header>
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

    <section className="research-card research-lifecycle"><header><span>04</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'done' : index === 1 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : index === 1 ? c.blocked : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>05</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
