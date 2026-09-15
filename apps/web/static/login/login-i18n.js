(() => {
  const STORAGE_KEY = 'whalpha.interface.locale';
  const messages = {
    en: {
      title: 'WH Alpha Quantitative Research',
      languageLabel: 'Language', languageAria: 'Interface language', english: 'English', chinese: '中文', spanish: 'Español',
      brandDescriptor: 'Quantitative Research', navigationAria: 'Page navigation', navResearch: 'Research', navStandards: 'Standards', navTools: 'Free tools', navAccess: 'Sign in',
      heroEyebrow: 'Systematic U.S. equity research', heroTitle: 'Quantitative research that stands up to scrutiny.',
      heroDescription: 'A governed research system that moves from factor discovery to model construction and strategy expression. Point-in-time data, methods, evidence, failures, and limits remain visible.',
      guestSubmit: 'Continue as guest', guestSubmitting: 'Opening guest access', guestError: 'Guest access is temporarily unavailable.', orGuest: 'or continue without an account',
      trustAria: 'Research principles', trustPointTime: 'Point-in-time data', trustOutSample: 'Out-of-sample first', trustCost: 'Cost-aware', trustTransparent: 'Transparent by design',
      dossierAria: 'Current research record', dossierLabel: 'Current research record', modelFamily: 'DISCOVERY CATALOG', currentProgram: 'Factor Discovery V2', researchState: 'Development screen registered · outcomes unread',
      ledgerData: 'V2 factor catalog', ledgerModel: 'Data qualification', ledgerValidation: 'Model construction', ledgerAuthority: 'Candidate authority',
      stateBuilding: 'Registered · 8 definitions', stateQualified: 'Passed · 98.59% coverage', statePending: 'Locked', stateInactive: 'Inactive', dossierFoot: 'Six finite Development trials are frozen and the cumulative ledger now counts 14. No V2 outcome has been read; exact implementation and one replay are next.', notClaim: 'NO ALPHA FACTOR OR MODEL ADMITTED', priorProgram: 'Factor Catalog V1 and the first Pullback program remain reproducible failures. The V2 screen is registered—not presented as a predictive result.',
      exploreResearch: 'Continue to the research system', scrollPreview: 'Factor evidence · model lineage · free market tools', researchKicker: 'Discover, construct, then express', researchTitle: 'Evidence determines the model—not a fixed strategy menu.',
      researchIntro: 'WH Alpha separates measurements, predictive models, tradable expressions, and Product authority. Each layer is versioned, testable, and permitted to fail.',
      researchCore: 'RESEARCH CORE', labKicker: 'Quant Research Lab', labTitle: 'Three layers. One complete evidence trail.',
      labText: 'Factors define what is measured. Models define what is estimated. Strategy expressions define how an estimate becomes a cost-aware decision. Every version and failure stays traceable.',
      flowAria: 'Research lifecycle', flowHypothesis: 'Factor discovery', flowData: 'Model construction', flowValidation: 'Strategy expression', flowFalsification: 'Locked validation', flowShadow: 'Shadow', flowActivation: 'Activation',
      decisionOutput: 'DECISION OUTPUT', selectionKicker: 'Model-driven equity selection', selectionTitle: 'A ranking must name the model behind it.',
      selectionText: 'Future rankings may use only explicitly activated models. Each stock will show market applicability, rank drivers, entry readiness, chase risk, and invalidation.',
      chainLab: 'Eligible strategy expression', chainReview: 'Human activation', chainCandidates: 'Candidate ranking',
      baselineNote: 'The current Candidate Baseline V1 remains visible and transparent, but is explicitly unvalidated and is not presented as an expected-return model.',
      researchExtension: 'RESEARCH EXTENSION', automationKicker: 'Governed research automation', automationTitle: 'More hypotheses. The same evidence threshold.',
      automationText: 'The planned AI research layer extends traditional quantitative research through bounded hypothesis generation and adversarial review. Isolated data stages, finite budgets, deterministic gates, and retained failures constrain the search.',
      automationPoint1: 'Parallel, deduplicated hypotheses', automationPoint2: 'Automated robustness and leakage attacks', automationPoint3: 'No model promotion without human review',
      standardsKicker: 'Research standard', standardsTitle: 'Rigor should be visible, not merely claimed.',
      standardsIntro: 'Every model exposes its data clock, assumptions, costs, weaknesses, and current authority. Uncertainty is a reported state—not hidden polish.',
      standardDataTitle: 'Point-in-time foundation', standardDataText: 'Stable instrument identity, historical membership, lifecycle evidence, corporate actions, and filing availability are governed without projecting today backward.',
      standardValidationTitle: 'Chronological evidence', standardValidationText: 'Development, validation, sealed holdout, and prospective observation remain distinct. Attractive in-sample results do not become proof.',
      standardCostsTitle: 'Tradable assumptions', standardCostsText: 'Entry timing, turnover, spread, impact, capacity, and instrument-specific risk belong in the evaluation—not in a footnote after the result.',
      standardOpenTitle: 'Fully inspectable', standardOpenText: 'Logic, source fields, formulas, parameters, exclusions, evidence, counterevidence, fingerprints, and invalidation remain open to review.',
      toolsKicker: 'Free market intelligence', toolsTitle: 'Market context stays open.', toolsIntro: 'Three free workspaces provide a disciplined view of the market before any stock-level idea is considered.', freeBadge: 'FREE',
      toolRegimeTitle: 'Market Regime & Opportunities', toolRegimeText: 'Read risk support, internal quality, directional strength, ETF relationships, and counterevidence across independent horizons.',
      toolSectorTitle: 'Sector ETF Rotation', toolSectorText: 'Compare sector proxies with SPY across 5, 10, and 20 sessions to see leadership, persistence, acceleration, and deterioration.',
      toolStructureTitle: 'Market Structure & Activity', toolStructureText: 'Inspect breadth, advancing and declining participation, benchmark structure, leaders, laggards, and trading activity.',
      workspaceReady: 'Research workspace available', signIn: 'Account sign in', continue: 'Enter the research workspace with an existing account.', invalid: 'Invalid username or password.',
      username: 'Username', password: 'Password', submit: 'Sign in', submitting: 'Signing in', guestNote: 'Guest and signed-in sessions currently receive identical product capability.',
      footerText: 'Transparent quantitative research for U.S. equities.',
    },
    zh: {
      title: 'WH Alpha 量化研究',
      languageLabel: '语言', languageAria: '界面语言', english: 'English', chinese: '中文', spanish: 'Español',
      brandDescriptor: '量化研究', navigationAria: '页面导航', navResearch: '研究体系', navStandards: '研究标准', navTools: '免费工具', navAccess: '登录',
      heroEyebrow: '系统化美股量化研究', heroTitle: '让每一个美股模型，都经得起追问。',
      heroDescription: '一套从因子发现、模型构建走向策略表达的受治理研究系统。点时数据、方法、证据、失败与边界始终可查。',
      guestSubmit: '以游客身份进入', guestSubmitting: '正在打开游客入口', guestError: '游客访问暂时不可用。', orGuest: '或无需账号直接进入',
      trustAria: '研究原则', trustPointTime: '点时数据', trustOutSample: '样本外优先', trustCost: '计入交易成本', trustTransparent: '从设计上保持透明',
      dossierAria: '当前研究档案', dossierLabel: '当前研究档案', modelFamily: '因子发现目录', currentProgram: '因子发现 V2', researchState: '开发期筛选已登记 · 尚未读取结果',
      ledgerData: 'V2 因子目录', ledgerModel: '数据资格诊断', ledgerValidation: '模型构建', ledgerAuthority: '候选排行权限',
      stateBuilding: '已登记 · 8项定义', stateQualified: '已通过 · 覆盖率98.59%', statePending: '保持锁定', stateInactive: '未激活', dossierFoot: '6项有限开发期试验已经冻结，累计账本现完整记录14项试验。V2尚未读取任何结果；下一步是精确实现和一次重放。', notClaim: '尚无获准的 Alpha 因子或模型', priorProgram: '因子目录 V1 与首个强势股回撤项目继续作为可复现失败留档；V2筛选已登记，但不是预测结果。',
      exploreResearch: '继续向下了解研究体系', scrollPreview: '因子证据 · 模型谱系 · 免费市场工具', researchKicker: '先发现，再构建，最后表达', researchTitle: '由证据决定模型，而不是由固定策略清单决定。',
      researchIntro: 'WH Alpha 将测量因子、预测模型、可交易表达和产品权限严格分开；每一层都独立版本化、可检验，也允许得到失败结论。',
      researchCore: '研究核心', labKicker: '量化研究实验室', labTitle: '三层结构，一条完整证据链。',
      labText: '因子定义测量什么，模型定义估计什么，策略表达定义如何把估计转为计入成本的决策；每个版本与失败都可追溯。',
      flowAria: '研究生命周期', flowHypothesis: '因子发现', flowData: '模型构建', flowValidation: '策略表达', flowFalsification: '锁定后验证', flowShadow: '影子观察', flowActivation: '人工激活',
      decisionOutput: '决策输出', selectionKicker: '模型驱动美股筛选', selectionTitle: '每一个排名，都必须说明来自哪个模型。',
      selectionText: '未来排行只能使用明确激活的模型，并展示市场适用性、排名驱动、进入准备度、追高风险与失效条件。',
      chainLab: '合格策略表达', chainReview: '人工激活审查', chainCandidates: '候选排名',
      baselineNote: '当前 Candidate Baseline V1 仍保持可见与透明，但会明确标注为未经验证，也不会包装成预期收益模型。',
      researchExtension: '研究能力扩展', automationKicker: '受治理的研究自动化', automationTitle: '更多假设，同一套证据门槛。',
      automationText: '规划中的 AI 研究层在传统量化基础上扩展有限假设生成与对抗审查，并由数据阶段隔离、有限预算、确定性门槛和失败留档约束搜索。',
      automationPoint1: '并行且去重的假设探索', automationPoint2: '自动稳健性、泄漏与反证攻击', automationPoint3: '未经人工审查不进入模型应用',
      standardsKicker: '研究标准', standardsTitle: '严谨不应只是声明，而应当可以检查。',
      standardsIntro: '每个模型公开数据时钟、假设、成本、弱点与当前权限。不确定性是明确状态，不被包装隐藏。',
      standardDataTitle: '点时数据基础', standardDataText: '稳定证券身份、历史成分、生命周期、公司行动和披露可得时间均受治理，不把今天的信息倒推到过去。',
      standardValidationTitle: '按时间验证证据', standardValidationText: '开发、验证、密封留出集和前瞻观察相互隔离。漂亮的样本内结果不会被当成证明。',
      standardCostsTitle: '可交易的假设', standardCostsText: '进入时点、换手、点差、冲击、容量与不同工具的风险都属于评估主体，而不是结果之后的一条注释。',
      standardOpenTitle: '完整可检查', standardOpenText: '逻辑、源字段、公式、参数、排除项、支持证据、反面证据、指纹和失效条件全部开放检查。',
      toolsKicker: '免费市场情报', toolsTitle: '市场背景，始终开放。', toolsIntro: '三个免费工作区先建立有纪律的市场认识，再考虑任何个股机会。', freeBadge: '免费',
      toolRegimeTitle: '市场风向与机会', toolRegimeText: '分别观察风险支持、内部质量、强弱方向、ETF 关系与反面证据，不把不同周期压缩为一个结论。',
      toolSectorTitle: '行业 ETF 轮动', toolSectorText: '在 5、10、20 个交易日分别比较行业代理与 SPY，识别领先、持续、加速与走弱。',
      toolStructureTitle: '市场结构与活跃度', toolStructureText: '检查市场广度、上涨与下跌参与、基准结构、强弱个股与交易活跃度。',
      workspaceReady: '研究工作区可用', signIn: '账号登录', continue: '使用已有账号进入研究工作区。', invalid: '用户名或密码错误。',
      username: '用户名', password: '密码', submit: '登录', submitting: '正在登录', guestNote: '游客与登录用户目前获得完全相同的产品能力。',
      footerText: '透明、可验证的美股量化研究。',
    },
    es: {
      title: 'WH Alpha Investigación Cuantitativa',
      languageLabel: 'Idioma', languageAria: 'Idioma de la interfaz', english: 'English', chinese: '中文', spanish: 'Español',
      brandDescriptor: 'Investigación cuantitativa', navigationAria: 'Navegación de la página', navResearch: 'Investigación', navStandards: 'Estándares', navTools: 'Herramientas gratuitas', navAccess: 'Acceder',
      heroEyebrow: 'Investigación sistemática de acciones estadounidenses', heroTitle: 'Investigación cuantitativa que resiste un examen riguroso.',
      heroDescription: 'Un sistema gobernado que avanza del descubrimiento de factores a la construcción de modelos y la expresión de estrategias. Los datos point-in-time, métodos, fallos y límites permanecen visibles.',
      guestSubmit: 'Continuar como invitado', guestSubmitting: 'Abriendo el acceso de invitado', guestError: 'El acceso de invitado no está disponible temporalmente.', orGuest: 'o continuar sin una cuenta',
      trustAria: 'Principios de investigación', trustPointTime: 'Datos point-in-time', trustOutSample: 'Prioridad fuera de muestra', trustCost: 'Costes incorporados', trustTransparent: 'Transparente desde el diseño',
      dossierAria: 'Registro de investigación actual', dossierLabel: 'Registro de investigación actual', modelFamily: 'CATÁLOGO DE DESCUBRIMIENTO', currentProgram: 'Descubrimiento de factores V2', researchState: 'Selección en Desarrollo registrada · resultados sin consultar',
      ledgerData: 'Catálogo de factores V2', ledgerModel: 'Calificación de datos', ledgerValidation: 'Construcción del modelo', ledgerAuthority: 'Autoridad sobre Candidatos',
      stateBuilding: 'Registrado · 8 definiciones', stateQualified: 'Superada · cobertura del 98,59 %', statePending: 'Bloqueada', stateInactive: 'Inactiva', dossierFoot: 'Se han congelado seis pruebas finitas de Desarrollo y el registro acumulativo ya contabiliza 14. No se ha consultado ningún resultado V2; siguen la implementación exacta y una reproducción.', notClaim: 'NINGÚN FACTOR ALPHA NI MODELO ADMITIDO', priorProgram: 'El Catálogo V1 y el primer programa Pullback se conservan como fallos reproducibles. La selección V2 está registrada, pero no es un resultado predictivo.',
      exploreResearch: 'Continuar al sistema de investigación', scrollPreview: 'Evidencia de factores · linaje de modelos · herramientas de mercado gratuitas', researchKicker: 'Descubrir, construir y después expresar', researchTitle: 'La evidencia determina el modelo, no un menú fijo de estrategias.',
      researchIntro: 'WH Alpha separa las mediciones, los modelos predictivos, las expresiones negociables y la autoridad del producto. Cada capa está versionada, es comprobable y puede ser rechazada.',
      researchCore: 'NÚCLEO DE INVESTIGACIÓN', labKicker: 'Laboratorio de investigación cuantitativa', labTitle: 'Tres capas. Una trazabilidad completa de la evidencia.',
      labText: 'Los factores definen qué se mide; los modelos, qué se estima; y las expresiones de estrategia, cómo una estimación se convierte en una decisión neta de costes. Cada versión y fallo permanece trazable.',
      flowAria: 'Ciclo de vida de la investigación', flowHypothesis: 'Descubrimiento de factores', flowData: 'Construcción del modelo', flowValidation: 'Expresión de estrategia', flowFalsification: 'Validación bloqueada', flowShadow: 'Sombra', flowActivation: 'Activación',
      decisionOutput: 'SALIDA DE DECISIÓN', selectionKicker: 'Selección de acciones basada en modelos', selectionTitle: 'Toda clasificación debe identificar el modelo que la sustenta.',
      selectionText: 'Las clasificaciones futuras solo podrán utilizar modelos activados explícitamente. Cada acción mostrará adecuación al mercado, factores de clasificación, preparación de entrada, riesgo de perseguir el precio e invalidación.',
      chainLab: 'Expresión de estrategia apta', chainReview: 'Activación humana', chainCandidates: 'Clasificación de candidatos',
      baselineNote: 'Candidate Baseline V1 permanece visible y transparente, pero se identifica explícitamente como no validada y no se presenta como un modelo de rentabilidad esperada.',
      researchExtension: 'AMPLIACIÓN DE LA INVESTIGACIÓN', automationKicker: 'Automatización gobernada de la investigación', automationTitle: 'Más hipótesis. El mismo umbral de evidencia.',
      automationText: 'La capa de investigación con IA prevista amplía la investigación cuantitativa tradicional mediante generación acotada de hipótesis y revisión adversarial. Etapas de datos aisladas, presupuestos finitos, filtros deterministas y conservación de los fallos limitan la búsqueda.',
      automationPoint1: 'Hipótesis paralelas y deduplicadas', automationPoint2: 'Ataques automatizados de robustez y fuga de información', automationPoint3: 'Ningún modelo se promueve sin revisión humana',
      standardsKicker: 'Estándar de investigación', standardsTitle: 'El rigor debe poder examinarse, no limitarse a una afirmación.',
      standardsIntro: 'Cada modelo expone su reloj de datos, supuestos, costes, debilidades y autoridad actual. La incertidumbre se informa como un estado; no se oculta tras una presentación pulida.',
      standardDataTitle: 'Base point-in-time', standardDataText: 'La identidad estable del instrumento, la composición histórica, la evidencia de ciclo de vida, las acciones corporativas y la disponibilidad de las comunicaciones se gobiernan sin proyectar el presente hacia el pasado.',
      standardValidationTitle: 'Evidencia cronológica', standardValidationText: 'Desarrollo, validación, holdout sellado y observación prospectiva permanecen separados. Un resultado atractivo dentro de muestra no se convierte en prueba.',
      standardCostsTitle: 'Supuestos negociables', standardCostsText: 'Momento de entrada, rotación, diferencial, impacto, capacidad y riesgo específico del instrumento pertenecen a la evaluación, no a una nota al pie posterior al resultado.',
      standardOpenTitle: 'Completamente examinable', standardOpenText: 'La lógica, los campos de origen, las fórmulas, los parámetros, las exclusiones, la evidencia, la evidencia contraria, las huellas y la invalidación permanecen abiertos a revisión.',
      toolsKicker: 'Inteligencia de mercado gratuita', toolsTitle: 'El contexto de mercado permanece abierto.', toolsIntro: 'Tres espacios de trabajo gratuitos ofrecen una lectura disciplinada del mercado antes de considerar cualquier idea sobre una acción.', freeBadge: 'GRATIS',
      toolRegimeTitle: 'Régimen de mercado y oportunidades', toolRegimeText: 'Examine el respaldo al riesgo, la calidad interna, la fortaleza direccional, las relaciones entre ETF y la evidencia contraria en horizontes independientes.',
      toolSectorTitle: 'Rotación de ETF sectoriales', toolSectorText: 'Compare proxies sectoriales con SPY en 5, 10 y 20 sesiones para observar liderazgo, persistencia, aceleración y deterioro.',
      toolStructureTitle: 'Estructura y actividad del mercado', toolStructureText: 'Examine amplitud, participación alcista y bajista, estructura de referencias, líderes, rezagados y actividad negociadora.',
      workspaceReady: 'Espacio de investigación disponible', signIn: 'Acceso a la cuenta', continue: 'Acceda al espacio de investigación con una cuenta existente.', invalid: 'Usuario o contraseña incorrectos.',
      username: 'Usuario', password: 'Contraseña', submit: 'Acceder', submitting: 'Accediendo', guestNote: 'Las sesiones de invitado y con cuenta reciben actualmente las mismas funciones del producto.',
      footerText: 'Investigación cuantitativa transparente para acciones estadounidenses.',
    },
  };

  function valid(value) { return value === 'en' || value === 'zh' || value === 'es'; }
  function stored() { try { return window.localStorage.getItem(STORAGE_KEY); } catch { return null; } }
  function resolve() {
    const fromUrl = new URLSearchParams(window.location.search).get('lang');
    if (fromUrl !== null) return valid(fromUrl) ? fromUrl : 'en';
    const fromStorage = stored();
    return valid(fromStorage) ? fromStorage : 'en';
  }
  let locale = resolve();
  function t(key) { return messages[locale][key]; }
  function canonicalUrl(nextLocale) { const url = new URL(window.location.href); url.searchParams.set('lang', nextLocale); return url; }
  function apply() {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : locale;
    document.title = t('title');
    document.querySelectorAll('[data-i18n]').forEach((node) => { const key = node.getAttribute('data-i18n'); if (key && messages[locale][key]) node.textContent = t(key); });
    document.querySelectorAll('[data-i18n-aria]').forEach((node) => { const key = node.getAttribute('data-i18n-aria'); if (key && messages[locale][key]) node.setAttribute('aria-label', t(key)); });
    document.querySelectorAll('[data-locale]').forEach((node) => { const active = node.getAttribute('data-locale') === locale; node.classList.toggle('active', active); node.setAttribute('aria-pressed', active ? 'true' : 'false'); });
  }
  function setLocale(nextLocale) {
    if (!valid(nextLocale)) return;
    try { window.localStorage.setItem(STORAGE_KEY, nextLocale); } catch { /* An in-session choice still works. */ }
    window.history.pushState(window.history.state, '', canonicalUrl(nextLocale));
    locale = nextLocale; apply();
    window.dispatchEvent(new CustomEvent('whalpha:localechange', { detail: { locale } }));
  }
  const rawLocale = new URLSearchParams(window.location.search).get('lang');
  if (rawLocale !== locale) window.history.replaceState(window.history.state, '', canonicalUrl(locale));
  apply();
  document.querySelectorAll('[data-locale]').forEach((node) => node.addEventListener('click', () => setLocale(node.getAttribute('data-locale'))));
  window.addEventListener('popstate', () => { locale = resolve(); const raw = new URLSearchParams(window.location.search).get('lang'); if (raw !== locale) window.history.replaceState(window.history.state, '', canonicalUrl(locale)); apply(); window.dispatchEvent(new CustomEvent('whalpha:localechange', { detail: { locale } })); });
  window.__whalphaLoginI18n = { get locale() { return locale; }, t, setLocale, messages };
})();
