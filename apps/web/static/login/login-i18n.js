(() => {
  const STORAGE_KEY = 'whalpha.interface.locale';
  const messages = {
    en: {
      title: 'WH Alpha Sign In', languageLabel: 'Language', languageAria: 'Interface language', english: 'English', chinese: '中文',
      brandDescriptor: 'Market Intelligence', navigationAria: 'Page navigation', navPlatform: 'Platform', navPrinciples: 'Principles', navAccess: 'Enter workspace',
      heroEyebrow: 'Decision intelligence, not black-box signals', heroTitle: 'Read the market. Find the setup. Manage the decision.',
      platform: 'Quantitative Market Structure & Trading Intelligence Platform',
      description: 'A practical U.S. equity intelligence workspace that connects market state, relative strength, actionable candidates, and the evidence behind every judgment.',
      workflowAria: 'Decision workflow', pathMarket: 'Market state', pathDirection: 'Direction', pathCandidate: 'Candidate', pathDecision: 'Decision',
      workspaceReady: 'Workspace ready', signIn: 'Enter the workspace', continue: 'Sign in with your private credentials, or open the complete workspace as a guest.', invalid: 'Invalid username or password.',
      username: 'Username', password: 'Password', submit: 'Sign in', submitting: 'Signing in', or: 'or',
      guestSubmit: 'Continue as guest', guestSubmitting: 'Opening guest access', guestError: 'Guest access is temporarily unavailable.',
      guestNote: 'Guest and signed-in sessions receive the same data, tools, language options, Universe choices, and analysis.', explorePlatform: 'Explore the platform',
      roadmapKicker: 'The intelligence path', roadmapTitle: 'One decision system, built in connected layers.',
      roadmapIntro: 'WH Alpha is organized around the questions a trader actually asks. Each layer narrows the next decision while keeping evidence, counterevidence, and uncertainty visible.',
      fullWorkflowAria: 'Complete decision chain', chainMarket: 'Market state', chainStrength: 'Strength direction', chainSector: 'Sector / theme', chainStock: 'Stock candidate', chainPrepare: 'Trade preparation', chainEntry: 'Entry / invalidation', chainManage: 'Position management',
      capabilitiesAria: 'Platform capabilities', liveNow: 'Live now', plannedNext: 'Planned next', planned: 'Planned', plannedLater: 'Planned later',
      capRegimeTitle: 'Market Regime & Opportunities', capRegimeText: 'Determine whether the market truly supports broad risk-taking through regime, directional strength, ETF relationships, and counterevidence.', capRegimePoint1: 'Primary and Secondary Universe views', capRegimePoint2: '5 / 10 / 20-session relationships',
      capStructureTitle: 'Market Structure & Activity', capStructureText: 'Explain what changed today through breadth, advancing and declining participation, benchmark structure, and industry proxies.', capStructurePoint1: 'Participation—not claimed capital flow', capStructurePoint2: 'Current state plus historical path',
      capCandidatesTitle: 'Stock Candidates', capCandidatesText: 'Compare stocks inside distinct strategy channels, then show why each candidate ranks, where it sits, and what would invalidate the setup.', capCandidatesPoint1: 'Momentum, pullback, continuation, reversal, and defensive channels', capCandidatesPoint2: 'Ranking reasons before a single total score',
      capEvidenceTitle: 'Evidence & Decision Context', capEvidenceText: 'Keep raw values, parameters, contributions, supporting evidence, counterevidence, signal age, and recent price path open to inspection.', capEvidencePoint1: 'Explainable by design', capEvidencePoint2: 'Fail closed when formal data is unavailable',
      capRotationTitle: 'Sector & Theme Rotation', capRotationText: 'Track leadership, persistence, relative strength, diffusion, and changing opportunity across sectors and themes.', capRotationPoint1: 'Leadership and deterioration', capRotationPoint2: 'Context for defensive and counter-market opportunities',
      capPreparationTitle: 'Watchlist & Trade Preparation', capPreparationText: 'Turn an interesting stock into a monitored setup with trigger, pullback zone, support, resistance, threshold distance, signal age, and invalidation.', capPreparationPoint1: 'Position and timing before action', capPreparationPoint2: 'Fewer, more deliberate alerts',
      capOptionsTitle: 'Options Expression', capOptionsText: 'Compare how to express a stock view through calls, puts, debit spreads, covered calls, moneyness, and DTE—without treating stock returns as option returns.', capOptionsPoint1: 'Liquidity, spread, OI, IV, Greeks, and event risk', capOptionsPoint2: 'Payoff and time-decay trade-offs',
      capFundamentalsTitle: 'Fundamentals, Valuation & Events', capFundamentalsText: 'Add point-in-time financials, earnings quality, relative valuation, catalysts, and event context to price-based evidence.', capFundamentalsPoint1: 'No hindsight-contaminated fundamentals', capFundamentalsPoint2: 'No false surprise model without expectations data',
      capPortfolioTitle: 'Position Management', capPortfolioText: 'Reassess an open position as evidence changes: thesis health, invalidation, event exposure, concentration, and post-entry risk.', capPortfolioPoint1: 'Decision support, never automatic execution', capPortfolioPoint2: 'IBKR-first integration when this phase begins',
      principlesKicker: 'How WH Alpha thinks', principlesTitle: 'Built for judgment, not obedience.', principlesIntro: 'The platform should make a human decision clearer—not hide uncertainty behind a confident label.',
      principleExplainTitle: 'Explain before ranking', principleExplainText: 'A high or low rank must reveal the inputs, position, and trade-offs that produced it.',
      principleCounterTitle: 'Counterevidence is first-class', principleCounterText: 'Every constructive view should show what argues against it and what would make it fail.',
      principleContextTitle: 'Context changes meaning', principleContextText: 'The same setup can mean something different under a different market regime or sector environment.',
      principleHonestyTitle: 'Different instruments, different outcomes', principleHonestyText: 'Price and volume are not capital flow, and a stock signal is not an options-return prediction.',
      closingTitle: 'See the evidence. Keep the decision yours.', closingText: 'Open the complete workspace through either access path.', closingAction: 'Enter workspace', footerText: 'Practical U.S. equity market intelligence.',
    },
    zh: {
      title: 'WH Alpha 登录', languageLabel: '语言', languageAria: '界面语言', english: 'English', chinese: '中文',
      brandDescriptor: '市场情报', navigationAria: '页面导航', navPlatform: '平台能力', navPrinciples: '产品原则', navAccess: '进入工作区',
      heroEyebrow: '决策情报，而非黑箱信号', heroTitle: '读懂市场，找到机会，管理每一次决策。',
      platform: '量化市场结构与交易情报平台',
      description: '面向美国股票市场的实用研究工作台，把市场状态、相对强弱、可执行候选与每项判断背后的证据连接起来。',
      workflowAria: '决策流程', pathMarket: '市场状态', pathDirection: '强弱方向', pathCandidate: '个股候选', pathDecision: '交易决策',
      workspaceReady: '工作区可用', signIn: '进入工作区', continue: '使用私人凭据登录，或以游客身份打开完整工作区。', invalid: '用户名或密码错误。',
      username: '用户名', password: '密码', submit: '登录', submitting: '正在登录', or: '或',
      guestSubmit: '以游客身份继续', guestSubmitting: '正在打开游客访问', guestError: '游客访问暂时不可用。',
      guestNote: '游客与登录用户获得完全相同的数据、工具、语言、股票池选项和分析内容。', explorePlatform: '了解平台能力',
      roadmapKicker: '情报路径', roadmapTitle: '一套由相互连接的层次构成的决策系统。',
      roadmapIntro: 'WH Alpha 按交易者真正会提出的问题组织。每一层都收窄下一步决策，同时让证据、反面证据与不确定性保持可见。',
      fullWorkflowAria: '完整决策链', chainMarket: '市场状态', chainStrength: '强弱方向', chainSector: '行业 / 主题', chainStock: '个股候选', chainPrepare: '交易准备', chainEntry: '进入 / 失效', chainManage: '持仓管理',
      capabilitiesAria: '平台能力', liveNow: '当前可用', plannedNext: '下一阶段', planned: '规划中', plannedLater: '后期规划',
      capRegimeTitle: '市场风向与机会', capRegimeText: '通过市场状态、强弱方向、ETF 关系和反面证据，判断当前是否真正支持全面承担风险。', capRegimePoint1: 'Primary 与 Secondary 股票池视角', capRegimePoint2: '5 / 10 / 20 个交易日关系',
      capStructureTitle: '市场结构与交易活跃度', capStructureText: '通过市场广度、上涨与下跌参与、基准结构和行业代理，解释今天究竟发生了什么。', capStructurePoint1: '表达成交参与，不冒充资金流', capStructurePoint2: '当前状态与历史路径并列',
      capCandidatesTitle: '个股候选', capCandidatesText: '在不同策略通道内比较股票，并说明候选为何靠前、位置如何，以及什么情况会令逻辑失效。', capCandidatesPoint1: '动量、回撤、延续、反转与防御通道', capCandidatesPoint2: '先解释排名原因，再看综合分数',
      capEvidenceTitle: '证据与决策语境', capEvidenceText: '让原始值、参数、贡献、支持证据、反面证据、信号年龄和近期价格路径都可检查。', capEvidencePoint1: '从设计上保持可解释', capEvidencePoint2: '正式数据不可用时关闭输出',
      capRotationTitle: '行业与主题轮动', capRotationText: '追踪行业和主题的领导地位、持续性、相对强弱、扩散程度与机会变化。', capRotationPoint1: '识别领先与走弱', capRotationPoint2: '为防御和逆市场机会提供语境',
      capPreparationTitle: '观察清单与交易准备', capPreparationText: '把值得关注的股票转为可监测的交易准备，包括触发位、回撤区、支撑阻力、阈值距离、信号年龄和失效条件。', capPreparationPoint1: '行动前先判断位置与时机', capPreparationPoint2: '更少但更有目的的提醒',
      capOptionsTitle: '期权表达', capOptionsText: '比较 Call、Put、Debit Spread、Covered Call、价内外程度和 DTE，且绝不把股票收益当作期权收益。', capOptionsPoint1: '流动性、点差、OI、IV、Greeks 与事件风险', capOptionsPoint2: '盈亏结构与时间损耗权衡',
      capFundamentalsTitle: '基本面、估值与事件', capFundamentalsText: '在价格证据之上加入点时财务数据、盈利质量、相对估值、催化剂和事件语境。', capFundamentalsPoint1: '不使用被事后信息污染的基本面', capFundamentalsPoint2: '没有预期数据就不伪造超预期模型',
      capPortfolioTitle: '持仓管理', capPortfolioText: '随着证据变化重新评估持仓：逻辑健康度、失效条件、事件暴露、集中度与进入后的风险。', capPortfolioPoint1: '只提供决策支持，不自动执行交易', capPortfolioPoint2: '进入该阶段后优先对接 IBKR',
      principlesKicker: 'WH Alpha 的思考方式', principlesTitle: '服务于判断，而不是要求服从。', principlesIntro: '平台应当让人的决策更清楚，而不是用一个自信的标签掩盖不确定性。',
      principleExplainTitle: '排名之前先解释', principleExplainText: '任何高低排名都必须说明产生它的输入、位置和取舍。',
      principleCounterTitle: '认真对待反面证据', principleCounterText: '每个积极判断都应同时说明反对它的证据，以及什么会令判断失效。',
      principleContextTitle: '语境改变信号含义', principleContextText: '同样的形态，在不同市场状态或行业环境中可能具有不同含义。',
      principleHonestyTitle: '不同工具，不同结果', principleHonestyText: '价格和成交量不是资金流，股票信号也不是期权收益预测。',
      closingTitle: '看清证据，把决策留在自己手中。', closingText: '通过任一入口打开完整工作区。', closingAction: '进入工作区', footerText: '实用的美国股票市场情报。',
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
