(() => {
  const STORAGE_KEY = 'whalpha.interface.locale';
  const messages = {
    en: {
      title: 'WH Alpha Sign In', languageLabel: 'Language', languageAria: 'Interface language', english: 'English', chinese: '中文',
      platform: 'Quantitative Market Structure & Trading Intelligence Platform',
      description: 'A private U.S. equity market intelligence workspace for market breadth, cross-sectional strength, liquidity structure, and daily market analysis.',
      workspaceAria: 'Workspace scope', tagEod: 'End-of-Day Market Structure', tagPrivate: 'Private Research Workspace', tagData: 'Data-Driven Market Intelligence',
      signIn: 'Sign in', continue: 'Use your private dashboard credentials to continue.', invalid: 'Invalid username or password.',
      username: 'Username', password: 'Password', submit: 'Sign In', submitting: 'Signing In', or: 'or',
      guestSubmit: 'Continue as guest', guestSubmitting: 'Opening guest access', guestError: 'Guest access is temporarily unavailable.',
      guestNote: 'Guest and signed-in sessions receive the same data, tools, language options, Universe choices, and analysis.',
    },
    zh: {
      title: 'WH Alpha 登录', languageLabel: '语言', languageAria: '界面语言', english: 'English', chinese: '中文',
      platform: '量化市场结构与交易情报平台',
      description: '面向美国股票市场的私人研究工作台，聚焦市场广度、横截面强弱、流动性结构与每日市场分析。',
      workspaceAria: '研究范围', tagEod: '日终市场结构', tagPrivate: '私人研究工作台', tagData: '数据驱动的市场情报',
      signIn: '登录', continue: '请使用私人仪表盘凭据继续。', invalid: '用户名或密码错误。',
      username: '用户名', password: '密码', submit: '登录', submitting: '正在登录', or: '或',
      guestSubmit: '以游客身份继续', guestSubmitting: '正在打开游客访问', guestError: '游客访问暂时不可用。',
      guestNote: '游客与登录用户获得完全相同的数据、工具、语言、股票池选项和分析内容。',
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
