import { beforeEach, describe, expect, it, vi } from 'vitest';
import dashboardHtml from '../index.html?raw';
import loginHtml from '../static/login/index.html?raw';
import loginScript from '../static/login/login.js?raw';
import loginI18nScript from '../static/login/login-i18n.js?raw';

function renderLogin(url = '/') {
  window.history.replaceState({}, '', url);
  document.body.innerHTML = `
    <div class="login-language" role="group" aria-label="Interface language" data-i18n-aria="languageAria">
      <span data-i18n="languageLabel">Language</span>
      <button type="button" data-locale="en">English</button>
      <button type="button" data-locale="zh">中文</button>
      <button type="button" data-locale="es">ES</button>
    </div>
    <form method="post" action="/auth/login" autocomplete="on">
      <p id="login-error" class="login-error" role="alert" data-i18n="invalid">Invalid username or password.</p>
      <input id="next" name="next" type="hidden" value="/dashboard/" />
      <input id="username" name="username" type="text" autocomplete="username" />
      <input id="password" name="password" type="password" autocomplete="current-password" />
      <button class="login-submit" type="submit">Sign In</button>
      <button class="guest-submit" type="button">Continue as guest</button>
      <p id="guest-error" class="login-error" role="alert" data-i18n="guestError">Guest access is temporarily unavailable.</p>
      <p class="guest-note" data-i18n="guestNote">Guest and signed-in sessions receive the same content.</p>
    </form>
  `;
}

function runLoginScript() {
  Function(loginScript)();
}

function runLoginI18nScript() {
  Function(loginI18nScript)();
}

describe('static login client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    delete (window as unknown as { __whalphaLoginI18n?: unknown }).__whalphaLoginI18n;
    delete (window as unknown as { __whalphaNavigate?: unknown }).__whalphaNavigate;
    renderLogin();
  });

  it('declares the same public PNG favicon and branded search metadata on both entries', () => {
    for (const html of [dashboardHtml, loginHtml]) {
      expect(html).toContain('rel="icon" type="image/png" href="/favicon.png"');
      expect(html).toContain('rel="apple-touch-icon" href="/favicon.png"');
      expect(html).toContain('name="theme-color" content="#061b33"');
    }
    expect(dashboardHtml).toContain('WH Alpha is a transparent U.S. equity quantitative research');
    expect(loginHtml).toContain('WH Alpha is a transparent U.S. equity quantitative research');
  });

  it('presents research authority before free market tools without inventing performance', () => {
    expect(loginHtml).toContain('<img src="/favicon.png" alt="WH Alpha"');
    expect(loginHtml).toContain('id="research"');
    expect(loginHtml).toContain('id="standards"');
    expect(loginHtml).toContain('id="free-tools"');
    expect(loginHtml).toContain('data-whalpha-entry-contract="quant-research-v1"');
    expect(loginHtml).toContain('data-research-layout="core-plus-rail"');
    expect(loginHtml).toContain('data-i18n="notClaim"');
    expect(loginHtml).toContain('data-i18n="baselineNote"');
    expect(loginHtml.match(/data-i18n="freeBadge"/g)).toHaveLength(3);
    expect(loginHtml).toContain('data-i18n="guestNote"');
    expect(loginHtml.indexOf('id="research"')).toBeLessThan(loginHtml.indexOf('id="free-tools"'));
  });

  it('keeps account sign-in first, guest access second, and a visible continuation into the landing narrative', () => {
    expect(loginHtml).toContain('class="login-panel login-panel--hero"');
    expect(loginHtml).toContain('class="scroll-cue"');
    expect(loginHtml).toContain('data-i18n="scrollPreview"');
    expect(loginHtml.indexOf('class="login-submit"')).toBeLessThan(loginHtml.indexOf('class="guest-submit"'));
    expect(loginHtml.indexOf('class="login-panel login-panel--hero"')).toBeLessThan(loginHtml.indexOf('id="research"'));
    expect(loginHtml.match(/<form /g)).toHaveLength(1);
  });

  it('defines both locales for every public-page translation key', () => {
    runLoginI18nScript();
    const loginI18n = (window as unknown as { __whalphaLoginI18n: { messages: Record<'en' | 'zh', Record<string, string>> } }).__whalphaLoginI18n;
    const referencedKeys = new Set(Array.from(loginHtml.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g), (match) => match[1]));
    for (const key of referencedKeys) {
      expect(loginI18n.messages.en[key], `missing English login copy for ${key}`).toBeTruthy();
      expect(loginI18n.messages.zh[key], `missing Chinese login copy for ${key}`).toBeTruthy();
    }
  });

  it('submits JSON to relative auth endpoint and prevents native navigation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockResolvedValueOnce({ ok: false, json: async () => ({ error: 'invalid_credentials' }) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/auth/status', expect.objectContaining({ method: 'GET' })));

    (document.getElementById('username') as HTMLInputElement).value = 'hui';
    (document.getElementById('password') as HTMLInputElement).value = 'invalid-test-password';
    const event = new Event('submit', { bubbles: true, cancelable: true });
    document.querySelector('form')!.dispatchEvent(event);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    expect(event.defaultPrevented).toBe(true);
    expect(fetchMock.mock.calls[1][0]).toBe('/auth/login');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    });
    const body = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(body).toEqual({ username: 'hui', password: 'invalid-test-password', next: '/dashboard/?lang=en' });
    expect(String(fetchMock.mock.calls[1][0])).not.toContain('invalid-test-password');
  });

  it('rejects unsafe next values before submitting', async () => {
    renderLogin('/?next=https%3A%2F%2Fevil.example%2Fdashboard%2F');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockResolvedValueOnce({ ok: false, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    (document.getElementById('username') as HTMLInputElement).value = 'hui';
    (document.getElementById('password') as HTMLInputElement).value = 'invalid-test-password';
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    expect(JSON.parse(fetchMock.mock.calls[1][1].body).next).toBe('/dashboard/?lang=en');
  });

  it('clears password and stays on login page on failure', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockResolvedValueOnce({ ok: false, json: async () => ({ error: 'invalid_credentials' }) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const password = document.getElementById('password') as HTMLInputElement;
    password.value = 'invalid-test-password';
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    expect(password.value).toBe('');
    expect(document.getElementById('login-error')?.classList.contains('visible')).toBe(true);
    expect(window.location.pathname).toBe('/');
  });

  it('blocks duplicate submits while a request is pending', async () => {
    let resolveFetch: (value: { ok: boolean; json: () => Promise<object> }) => void = () => undefined;
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockImplementationOnce(() =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const form = document.querySelector('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    resolveFetch({ ok: false, json: async () => ({}) });
    await vi.waitFor(() => expect((document.querySelector('.login-submit') as HTMLButtonElement).disabled).toBe(false));
  });

  it('redirects an already-authenticated root visitor to dashboard', async () => {
    const navigate = vi.fn();
    (window as unknown as { __whalphaNavigate: typeof navigate }).__whalphaNavigate = navigate;
    const fetchMock = vi.fn().mockResolvedValueOnce({ status: 204, ok: true });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/dashboard/?lang=en'));
  });

  it('opens the same dashboard through a guest Session without credentials', async () => {
    const navigate = vi.fn();
    (window as unknown as { __whalphaNavigate: typeof navigate }).__whalphaNavigate = navigate;
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ authenticated: true, next: '/dashboard/?view=regime&lang=en' }) });
    vi.stubGlobal('fetch', fetchMock);
    renderLogin('/?next=%2Fdashboard%2F%3Fview%3Dregime');
    runLoginI18nScript();
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    (document.querySelector('.guest-submit') as HTMLButtonElement).click();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][0]).toBe('/auth/guest');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST', credentials: 'same-origin' });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ next: '/dashboard/?view=regime&lang=en' });
    expect(fetchMock.mock.calls[1][1].body).not.toContain('username');
    expect(fetchMock.mock.calls[1][1].body).not.toContain('password');
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/dashboard/?view=regime&lang=en'));
  });

  it('accepts only dashboard next paths', async () => {
    renderLogin('/?next=%2Fdashboard%2Fresearch');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ status: 401, ok: false })
      .mockResolvedValueOnce({ ok: false, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    (document.getElementById('username') as HTMLInputElement).value = 'hui';
    (document.getElementById('password') as HTMLInputElement).value = 'invalid-test-password';
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).next).toBe('/dashboard/research?lang=en');
  });

  it('keeps authentication behavior while applying explicit multilingual locale state', async () => {
    Object.defineProperty(window.navigator, 'language', { configurable: true, value: 'zh-CN' });
    renderLogin('/?next=%2Fdashboard%2F%3Fview%3Dregime%26universe%3Dprimary');
    runLoginI18nScript();
    const loginI18n = (window as unknown as { __whalphaLoginI18n: { locale: string; messages: Record<'en' | 'zh' | 'es', Record<string, string>> } }).__whalphaLoginI18n;
    expect(loginI18n.locale).toBe('en');
    expect(Object.keys(loginI18n.messages.en).sort()).toEqual(Object.keys(loginI18n.messages.zh).sort());
    expect(Object.keys(loginI18n.messages.en).sort()).toEqual(Object.keys(loginI18n.messages.es).sort());
    expect(document.documentElement.lang).toBe('en');
    expect(window.location.search).toContain('lang=en');

    const fetchMock = vi.fn().mockResolvedValueOnce({ status: 401, ok: false });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect((document.getElementById('next') as HTMLInputElement).value).toContain('lang=en');

    (document.querySelector('[data-locale="zh"]') as HTMLButtonElement).click();
    expect(window.localStorage.getItem('whalpha.interface.locale')).toBe('zh');
    expect(window.location.search).toContain('lang=zh');
    expect(document.documentElement.lang).toBe('zh-CN');
    expect(document.getElementById('login-error')).toHaveTextContent('用户名或密码错误。');
    expect((document.getElementById('next') as HTMLInputElement).value).toContain('lang=zh');
    expect((document.getElementById('next') as HTMLInputElement).value).toContain('view=regime');
    expect((document.getElementById('next') as HTMLInputElement).value).toContain('universe=primary');

    (document.querySelector('[data-locale="es"]') as HTMLButtonElement).click();
    expect(window.localStorage.getItem('whalpha.interface.locale')).toBe('es');
    expect(window.location.search).toContain('lang=es');
    expect(document.documentElement.lang).toBe('es');
    expect(document.getElementById('login-error')).toHaveTextContent('Usuario o contraseña incorrectos.');
    expect((document.getElementById('next') as HTMLInputElement).value).toContain('lang=es');
  });

  it('lets URL locale override storage and safely canonicalizes invalid locale', () => {
    window.localStorage.setItem('whalpha.interface.locale', 'zh');
    renderLogin('/?lang=en');
    runLoginI18nScript();
    expect((window as unknown as { __whalphaLoginI18n: { locale: string } }).__whalphaLoginI18n.locale).toBe('en');

    renderLogin('/?lang=unsafe%3Cscript%3E');
    window.localStorage.clear();
    runLoginI18nScript();
    expect((window as unknown as { __whalphaLoginI18n: { locale: string } }).__whalphaLoginI18n.locale).toBe('en');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('en');
  });
});
