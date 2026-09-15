import modelRecord from '../modelRecords/quant-research-lab-model-record-v1.json';
import { useI18n } from '../i18n/I18nProvider';

const ARCHITECTURE_COPY = {
  en: {
    eyebrow: 'Current research architecture · ADR 0274',
    title: 'From measurement to a decision—without collapsing the evidence.',
    note: 'The research universe can expand over time. Every batch that reads outcomes remains finite, registered, and fully counted.',
    layers: [
      ['01', 'Factor Discovery', 'CURRENT · OUTCOME BLIND', 'Define point-in-time measurements, qualify coverage and redundancy, then screen only under a frozen trial budget. Catalog V1 has 12 registered definitions; values and outcomes have not been computed.'],
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
      ['01', '因子发现层', '当前阶段 · 不读取结果', '定义点时测量，先核验覆盖与冗余，再按冻结的试验预算筛选。V1 已登记12项定义；尚未计算因子值，也未读取未来收益。'],
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
      ['01', 'Descubrimiento de factores', 'FASE ACTUAL · SIN RESULTADOS', 'Define mediciones point-in-time, califica cobertura y redundancia y solo después permite una selección con presupuesto congelado. El Catálogo V1 registra 12 definiciones; aún no hay valores ni resultados.'],
      ['02', 'Construcción del modelo', 'BLOQUEADA', 'Combina un pequeño conjunto de factores admitidos en un rango, probabilidad, distribución o estado de riesgo explicable. No hay un modelo preseleccionado.'],
      ['03', 'Expresión de estrategia', 'BLOQUEADA', 'Convierte un modelo bloqueado en reglas de entrada, salida, tenencia, tamaño, costes, capacidad y riesgo. Acciones y opciones se validan por separado.'],
    ],
    boundary: 'Un factor no es un modelo. Un modelo no es una estrategia. Un backtest no concede autoridad al producto.',
    prior: 'Resultado del primer programa',
    priorBody: 'Strong-Leader Pullback está cerrado: V1 fue inconcluso y su única alternativa registrada fue rechazada por inestabilidad entre escenarios terminales. No se bloqueó ningún parámetro ni se abrieron Validación o Holdout.',
  },
} as const;

const COPY = {
  en: {
    eyebrow: 'Factor, model, and strategy research · governed registry',
    title: 'Quant Research Lab',
    subtitle: 'The authoritative record of what is measured, what is modeled, how it becomes a strategy, and where the evidence fails.',
    status: 'FACTOR DISCOVERY V1', statusValue: 'OUTCOME BLIND',
    statusNote: 'Twelve definitions are registered. Factor values and coverage are not yet computed; no model, strategy expression, performance claim, or Candidate authority exists.',
    coverage: 'Evidence state', coverageNote: 'Method completeness and model effectiveness are separate questions.',
    coverageBoundary: 'A published method is not a validated strategy, current-market recommendation, or option-return forecast.',
    readiness: 'Evidence ladder', readinessItems: [
      ['Three-layer architecture', 'ACCEPTED', 'Factor Discovery, Model Construction, and Strategy Expression now have separate version and evidence boundaries.', 'met'],
      ['Factor Catalog V1', 'REGISTERED', 'Twelve exact outcome-blind definitions span five economic families; this is one bounded catalog, not the permanent factor universe.', 'met'],
      ['Coverage & redundancy', 'NEXT', 'Compute values, missingness, distributions, concentration, correlation, and exact replay without future returns.', 'active'],
      ['Model construction', 'LOCKED', 'A screening protocol must be frozen and factor evidence admitted before any model is constructed.', 'locked'],
      ['Strategy expression & Product', 'LOCKED', 'No entry/exit system, validated result, active Candidate model, or option-performance claim exists.', 'locked'],
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
    engineering: 'Method-engineering evidence', engineeringNote: 'The same registered method was run twice over the reconstructed Dell population with identical fingerprints. These facts answer whether the method can be computed—not whether it works.', engineeringBadge: 'REPLAYED · OUTCOME BLIND',
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
    resultCards: [['Pullback V1', 'Inconclusive evidence floor'], ['Pullback replacement', 'Rejected · endpoint instability'], ['Factor Catalog V1', '12 definitions · no outcomes'], ['Active models', 'None']],
    interpret: 'How future evidence will read', interpretBody: 'Signal research will show net expectancy, uncertainty, costs, sample coverage, win/payoff/PF, MFE/MAE, sensitivity, concentration, and counterevidence. It will not be reduced to one score.',
    optionBoundary: 'Stock evidence is not option performance', optionBoundaryBody: 'Options require a separate expression layer using contemporaneous quotes, IV, Greeks, spreads, open interest, expiry, and event risk.',
  },
  zh: {
    eyebrow: '因子、模型与策略研究 · 受控档案库',
    title: '量化研究实验室',
    subtitle: '权威记录测量什么、如何建模、怎样形成策略，以及证据在哪一层失败，而不是只陈列漂亮回测。',
    status: '因子发现 V1', statusValue: '不读取结果',
    statusNote: '已登记12项定义；尚未计算因子值与覆盖，也没有模型、策略表达、绩效主张或候选排名权限。',
    coverage: '证据状态', coverageNote: '方法是否完整与模型是否有效，是两个不同问题。',
    coverageBoundary: '公开方法不代表策略已验证，不代表适合当前市场，也不预测期权收益。',
    readiness: '证据阶梯', readinessItems: [
      ['三层研究架构', '已生效', '因子发现、模型构建与策略表达现在拥有相互独立的版本和证据边界。', 'met'],
      ['因子目录 V1', '已登记', '12项不读取结果的精确定义覆盖5类经济含义；这只是首个有限目录，不是永久因子全集。', 'met'],
      ['覆盖与冗余诊断', '下一步', '在不读取未来收益的前提下计算因子值、缺失、分布、集中度、相关性与精确重放。', 'active'],
      ['模型构建', '锁定', '只有先冻结筛选协议并取得合格因子证据，才允许构建模型。', 'locked'],
      ['策略表达与产品', '锁定', '目前没有入场退出系统、验证结果、已激活候选模型或期权绩效主张。', 'locked'],
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
    engineering: '方法工程证据', engineeringNote: '同一已登记方法已在戴尔重建样本上完整运行两次，结果指纹完全一致。以下事实只回答“方法能否计算”，不回答“策略是否有效”。', engineeringBadge: '已重放 · 不含结果',
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
    resultCards: [['回撤模型 V1', '证据门槛不足'], ['唯一替代方案', '被拒绝 · 终端情景不稳定'], ['因子目录 V1', '12项定义 · 尚未读取结果'], ['已激活模型', '无']],
    interpret: '未来证据如何呈现', interpretBody: '信号研究将展示净期望、不确定性、成本、样本覆盖、胜率/盈亏比/PF、MFE/MAE、敏感性、集中度与反面证据，不会压缩成一个总分。',
    optionBoundary: '股票证据不等于期权表现', optionBoundaryBody: '期权需要独立表达层，并使用当时的报价、IV、Greeks、点差、OI、到期日与事件风险。',
  },
  es: {
    eyebrow: 'Investigación de factores, modelos y estrategias · registro gobernado',
    title: 'Laboratorio de investigación cuantitativa',
    subtitle: 'El registro autoritativo de qué se mide, qué se modela, cómo se expresa una estrategia y en qué capa falla la evidencia.',
    status: 'DESCUBRIMIENTO DE FACTORES V1', statusValue: 'SIN RESULTADOS',
    statusNote: 'Hay 12 definiciones registradas. Aún no se han calculado valores ni cobertura; no existe modelo, expresión de estrategia, rendimiento ni autoridad sobre Candidatos.',
    coverage: 'Estado de la evidencia', coverageNote: 'La integridad del método y la eficacia del modelo son cuestiones distintas.',
    coverageBoundary: 'Publicar un método no convierte la estrategia en validada, adecuada para el mercado actual ni predictiva de rentabilidades de opciones.',
    readiness: 'Escalera de evidencia', readinessItems: [
      ['Arquitectura de tres capas', 'ACEPTADA', 'Descubrimiento de factores, Construcción del modelo y Expresión de estrategia tienen límites de versión y evidencia separados.', 'met'],
      ['Catálogo de factores V1', 'REGISTRADO', 'Doce definiciones exactas y sin resultados cubren cinco familias; es un catálogo acotado, no el universo permanente.', 'met'],
      ['Cobertura y redundancia', 'SIGUIENTE', 'Calcular valores, ausencias, distribuciones, concentración, correlación y reproducción sin rentabilidades futuras.', 'active'],
      ['Construcción del modelo', 'BLOQUEADA', 'Antes de construir un modelo deben congelarse el protocolo de selección y la admisión de factores.', 'locked'],
      ['Expresión de estrategia y Producto', 'BLOQUEADAS', 'No existe sistema de entrada/salida, resultado validado, modelo activo ni afirmación sobre opciones.', 'locked'],
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
    engineering: 'Evidencia de ingeniería del método', engineeringNote: 'El mismo método registrado se ejecutó dos veces sobre la población reconstruida en Dell y produjo huellas idénticas. Estos datos indican si puede calcularse, no si funciona.', engineeringBadge: 'REPRODUCIDO · SIN RESULTADOS',
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
    resultCards: [['Pullback V1', 'Umbral de evidencia inconcluso'], ['Alternativa registrada', 'Rechazada · inestabilidad terminal'], ['Catálogo de factores V1', '12 definiciones · sin resultados'], ['Modelos activos', 'Ninguno']],
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

    <section className="research-card research-engineering-evidence" aria-labelledby="research-engineering-title">
      <header><span>03</span><div><h2 id="research-engineering-title">{c.engineering}</h2><p>{c.engineeringNote}</p></div><b>{c.engineeringBadge}</b></header>
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
      <header><span>04</span><div><h2 id="research-model-title">{c.registry}</h2><p>{c.featured}</p></div></header>
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

    <section className="research-card research-lifecycle"><header><span>05</span><h2>{c.lifecycle}</h2></header><ol>{c.stages.map((stage, index) => <li className={index === 0 ? 'active' : 'locked'} key={stage}><i>{index + 1}</i><strong>{stage}</strong><small>{index === 0 ? c.current : c.locked}</small></li>)}</ol></section>

    <section className="research-card research-results"><header><span>06</span><div><h2>{c.results}</h2><p>{c.resultsNote}</p></div></header><div className="research-result-grid">{c.resultCards.map(([name, state]) => <article key={name}><b aria-hidden="true">—</b><strong>{name}</strong><span>{state}</span></article>)}</div></section>

    <section className="research-boundary-grid research-footer-notes"><article><span>{c.interpret}</span><p>{c.interpretBody}</p></article><article><span>{c.optionBoundary}</span><p>{c.optionBoundaryBody}</p></article></section>
  </main>;
}
