(() => {
  const STORAGE_KEY = 'whalpha.interface.locale';
  const messages = {
    en: {
      title: 'WH Alpha Quantitative Research',
      languageLabel: 'Language', languageAria: 'Interface language', english: 'English', chinese: '中文',
      brandDescriptor: 'Quantitative Research', navigationAria: 'Page navigation', navResearch: 'Research', navStandards: 'Standards', navTools: 'Free tools', navAccess: 'Private sign in',
      heroEyebrow: 'Systematic U.S. equity research', heroTitle: 'Quantitative research that stands up to scrutiny.',
      heroDescription: 'A professional research system for transparent models, reproducible evidence, and model-driven U.S. equity selection. Every conclusion remains open to inspection.',
      guestSubmit: 'Open the workspace', guestSubmitting: 'Opening workspace', guestError: 'Guest access is temporarily unavailable.', privateAccess: 'Private sign in',
      trustAria: 'Research principles', trustPointTime: 'Point-in-time data', trustOutSample: 'Out-of-sample first', trustCost: 'Cost-aware', trustTransparent: 'Transparent by design',
      dossierAria: 'Current research record', dossierLabel: 'Current research record', modelFamily: 'MODEL FAMILY', researchState: 'Preregistered · data foundation in progress',
      ledgerData: 'Point-in-time data', ledgerModel: 'Model specification', ledgerValidation: 'Out-of-sample evidence', ledgerAuthority: 'Candidate authority',
      stateBuilding: 'Building', stateLocked: 'V1 locked', statePending: 'Not published', stateInactive: 'Not activated', dossierFoot: 'Research status is shown before performance.', notClaim: 'NO PERFORMANCE CLAIM',
      exploreResearch: 'Explore the research system', researchKicker: 'Research before ranking', researchTitle: 'A model earns its place before it influences a candidate list.',
      researchIntro: 'WH Alpha separates research evidence from product authority. The Lab records what a model is, how it was tested, where it fails, and whether it is allowed to affect a daily ranking.',
      researchCore: 'RESEARCH CORE', labKicker: 'Quant Research Lab', labTitle: 'The complete record behind every model.',
      labText: 'Economic logic, point-in-time inputs, feature formulas, fixed parameters, costs, chronological splits, results, counterevidence, failure cases, and lifecycle decisions remain attached to the exact model version.',
      flowAria: 'Research lifecycle', flowHypothesis: 'Hypothesis', flowData: 'Data admission', flowValidation: 'Validation', flowFalsification: 'Falsification', flowShadow: 'Shadow', flowActivation: 'Activation',
      decisionOutput: 'DECISION OUTPUT', selectionKicker: 'Model-driven equity selection', selectionTitle: 'Rankings with an accountable source.',
      selectionText: 'Future candidate rankings will identify the exact activated model, its current-market applicability, the evidence that raised or lowered each stock, entry readiness, chase risk, and invalidation.',
      chainLab: 'Validated Lab model', chainReview: 'Human activation', chainCandidates: 'Candidate ranking',
      baselineNote: 'The current Candidate Baseline V1 remains visible and transparent, but is explicitly unvalidated and is not presented as an expected-return model.',
      researchExtension: 'RESEARCH EXTENSION', automationKicker: 'Governed research automation', automationTitle: 'Scale exploration without weakening the standard.',
      automationText: 'Built on traditional quantitative discipline, the planned AI research layer expands hypothesis exploration, implementation, and adversarial review while finite budgets, isolated data stages, deterministic gates, and retained failures control the search.',
      automationPoint1: 'Parallel, deduplicated hypotheses', automationPoint2: 'Automated robustness and leakage attacks', automationPoint3: 'No model promotion without human review',
      standardsKicker: 'Research standard', standardsTitle: 'The evidence is part of the product.',
      standardsIntro: 'Professional packaging should not conceal uncertainty. A WH Alpha model is useful only when its data clock, assumptions, costs, weaknesses, and current authority are visible.',
      standardDataTitle: 'Point-in-time foundation', standardDataText: 'Stable instrument identity, historical membership, lifecycle evidence, corporate actions, and filing availability are governed without projecting today backward.',
      standardValidationTitle: 'Chronological evidence', standardValidationText: 'Development, validation, sealed holdout, and prospective observation remain distinct. Attractive in-sample results do not become proof.',
      standardCostsTitle: 'Tradable assumptions', standardCostsText: 'Entry timing, turnover, spread, impact, capacity, and instrument-specific risk belong in the evaluation—not in a footnote after the result.',
      standardOpenTitle: 'Fully inspectable', standardOpenText: 'Logic, source fields, formulas, parameters, exclusions, evidence, counterevidence, fingerprints, and invalidation remain open to review.',
      toolsKicker: 'Free market intelligence', toolsTitle: 'Professional context, available without a subscription.', toolsIntro: 'Three established workspaces remain the fast way to understand the current market before examining any stock-level idea.', freeBadge: 'FREE',
      toolRegimeTitle: 'Market Regime & Opportunities', toolRegimeText: 'Read risk support, internal quality, directional strength, ETF relationships, and counterevidence across independent horizons.',
      toolSectorTitle: 'Sector ETF Rotation', toolSectorText: 'Compare sector proxies with SPY across 5, 10, and 20 sessions to see leadership, persistence, acceleration, and deterioration.',
      toolStructureTitle: 'Market Structure & Activity', toolStructureText: 'Inspect breadth, advancing and declining participation, benchmark structure, leaders, laggards, and trading activity.',
      accessKicker: 'Enter WH Alpha', accessTitle: 'Inspect the work. Keep the judgment.', accessText: 'Open the full current workspace as a guest, or use private credentials. Both entry paths currently receive the same data, tools, language options, Universe choices, and analysis.', guestReturn: 'Open guest access above ↑',
      workspaceReady: 'Workspace ready', signIn: 'Private sign in', continue: 'Use the existing private credential to enter the same research workspace.', invalid: 'Invalid username or password.',
      username: 'Username', password: 'Password', submit: 'Sign in', submitting: 'Signing in', guestNote: 'Guest and signed-in sessions currently receive identical product capability.',
      footerText: 'Transparent quantitative research for U.S. equities.',
    },
    zh: {
      title: 'WH Alpha 量化研究',
      languageLabel: '语言', languageAria: '界面语言', english: 'English', chinese: '中文',
      brandDescriptor: '量化研究', navigationAria: '页面导航', navResearch: '研究体系', navStandards: '研究标准', navTools: '免费工具', navAccess: '私人登录',
      heroEyebrow: '系统化美股量化研究', heroTitle: '让每一个美股模型，都经得起追问。',
      heroDescription: '面向透明模型、可复现证据与模型驱动美股筛选的专业研究体系。每一项结论都保留完整的检查路径。',
      guestSubmit: '进入完整工作区', guestSubmitting: '正在打开工作区', guestError: '游客访问暂时不可用。', privateAccess: '私人登录',
      trustAria: '研究原则', trustPointTime: '点时数据', trustOutSample: '样本外优先', trustCost: '计入交易成本', trustTransparent: '从设计上保持透明',
      dossierAria: '当前研究档案', dossierLabel: '当前研究档案', modelFamily: '模型家族', researchState: '已预注册 · 数据基础建设中',
      ledgerData: '点时数据', ledgerModel: '模型规范', ledgerValidation: '样本外证据', ledgerAuthority: '候选排行权限',
      stateBuilding: '建设中', stateLocked: 'V1 已锁定', statePending: '尚未发布', stateInactive: '尚未激活', dossierFoot: '先呈现研究状态，再谈表现。', notClaim: '不构成业绩声明',
      exploreResearch: '了解研究体系', researchKicker: '先研究，再排名', researchTitle: '模型必须先赢得资格，才能影响候选名单。',
      researchIntro: 'WH Alpha 将研究证据与产品权限严格分开。量化研究实验室记录模型是什么、如何验证、在哪里失败，以及它是否获准影响每日排行。',
      researchCore: '研究核心', labKicker: '量化研究实验室', labTitle: '完整记录每一个模型背后的研究。',
      labText: '经济逻辑、点时输入、特征公式、固定参数、交易成本、时间顺序切分、结果、反面证据、失败案例和生命周期决策，始终绑定到准确的模型版本。',
      flowAria: '研究生命周期', flowHypothesis: '提出假设', flowData: '数据准入', flowValidation: '时间验证', flowFalsification: '系统反证', flowShadow: '影子观察', flowActivation: '人工激活',
      decisionOutput: '决策输出', selectionKicker: '模型驱动美股筛选', selectionTitle: '每一个排名都有可追溯的来源。',
      selectionText: '未来的个股候选将明确对应已激活模型、当前市场适用性、推高或压低排名的证据、进入准备度、追高风险与失效条件。',
      chainLab: '实验室验证模型', chainReview: '人工激活审查', chainCandidates: '候选排名',
      baselineNote: '当前 Candidate Baseline V1 仍保持可见与透明，但会明确标注为未经验证，也不会包装成预期收益模型。',
      researchExtension: '研究能力扩展', automationKicker: '受治理的研究自动化', automationTitle: '扩大研究探索，同时不降低验证标准。',
      automationText: '在传统量化研究纪律之上，规划中的 AI 研究层用于扩大假设探索、实现和对抗审查；有限实验预算、阶段隔离、确定性门槛与失败留档共同约束搜索过程。',
      automationPoint1: '并行且去重的假设探索', automationPoint2: '自动稳健性、泄漏与反证攻击', automationPoint3: '未经人工审查不进入模型应用',
      standardsKicker: '研究标准', standardsTitle: '证据本身，就是产品的一部分。',
      standardsIntro: '专业包装不应掩盖不确定性。只有当数据时钟、假设、成本、弱点和当前权限都清楚可见时，模型才真正有用。',
      standardDataTitle: '点时数据基础', standardDataText: '稳定证券身份、历史成分、生命周期、公司行动和披露可得时间均受治理，不把今天的信息倒推到过去。',
      standardValidationTitle: '按时间验证证据', standardValidationText: '开发、验证、密封留出集和前瞻观察相互隔离。漂亮的样本内结果不会被当成证明。',
      standardCostsTitle: '可交易的假设', standardCostsText: '进入时点、换手、点差、冲击、容量与不同工具的风险都属于评估主体，而不是结果之后的一条注释。',
      standardOpenTitle: '完整可检查', standardOpenText: '逻辑、源字段、公式、参数、排除项、支持证据、反面证据、指纹和失效条件全部开放检查。',
      toolsKicker: '免费市场情报', toolsTitle: '无需订阅，也能获得专业的市场背景。', toolsIntro: '三个成熟工作区继续用于快速理解当前市场，再决定是否研究任何具体股票机会。', freeBadge: '免费',
      toolRegimeTitle: '市场风向与机会', toolRegimeText: '分别观察风险支持、内部质量、强弱方向、ETF 关系与反面证据，不把不同周期压缩为一个结论。',
      toolSectorTitle: '行业 ETF 轮动', toolSectorText: '在 5、10、20 个交易日分别比较行业代理与 SPY，识别领先、持续、加速与走弱。',
      toolStructureTitle: '市场结构与活跃度', toolStructureText: '检查市场广度、上涨与下跌参与、基准结构、强弱个股与交易活跃度。',
      accessKicker: '进入 WH Alpha', accessTitle: '检查研究，把判断留在自己手中。', accessText: '可以游客身份打开当前完整工作区，也可以使用私人凭据登录。两个入口目前获得完全相同的数据、工具、语言、股票池和分析内容。', guestReturn: '返回上方游客入口 ↑',
      workspaceReady: '工作区可用', signIn: '私人登录', continue: '使用现有私人凭据进入同一个研究工作区。', invalid: '用户名或密码错误。',
      username: '用户名', password: '密码', submit: '登录', submitting: '正在登录', guestNote: '游客与登录用户目前获得完全相同的产品能力。',
      footerText: '透明、可验证的美股量化研究。',
    },
  };

  function valid(value) { return value === 'en' || value === 'zh'; }
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
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
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
