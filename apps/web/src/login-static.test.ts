import { beforeEach, describe, expect, it, vi } from 'vitest';
import loginScript from '../static/login/login.js?raw';

function renderLogin(url = '/login/') {
  window.history.replaceState({}, '', url);
  document.body.innerHTML = `
    <form method="post" action="/auth/login" autocomplete="on">
      <p id="login-error" class="login-error" role="alert">Invalid username or password.</p>
      <input id="next" name="next" type="hidden" value="/dashboard/" />
      <input id="username" name="username" type="text" autocomplete="username" />
      <input id="password" name="password" type="password" autocomplete="current-password" />
      <button class="login-submit" type="submit">Sign In</button>
    </form>
  `;
}

function runLoginScript() {
  Function(loginScript)();
}

describe('static login client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    renderLogin();
  });

  it('submits JSON to relative auth endpoint and prevents native navigation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: 'invalid_credentials' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();

    (document.getElementById('username') as HTMLInputElement).value = 'hui';
    (document.getElementById('password') as HTMLInputElement).value = 'invalid-test-password';
    const event = new Event('submit', { bubbles: true, cancelable: true });
    document.querySelector('form')!.dispatchEvent(event);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    expect(event.defaultPrevented).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/login');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toEqual({ username: 'hui', password: 'invalid-test-password', next: '/dashboard/' });
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('invalid-test-password');
  });

  it('rejects unsafe next values before submitting', async () => {
    renderLogin('/login/?next=https%3A%2F%2Fevil.example%2Fdashboard%2F');
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();

    (document.getElementById('username') as HTMLInputElement).value = 'hui';
    (document.getElementById('password') as HTMLInputElement).value = 'invalid-test-password';
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    expect(JSON.parse(fetchMock.mock.calls[0][1].body).next).toBe('/dashboard/');
  });

  it('clears password and stays on login page on failure', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, json: async () => ({ error: 'invalid_credentials' }) });
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();

    const password = document.getElementById('password') as HTMLInputElement;
    password.value = 'invalid-test-password';
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    expect(password.value).toBe('');
    expect(document.getElementById('login-error')?.classList.contains('visible')).toBe(true);
    expect(window.location.pathname).toBe('/login/');
  });

  it('blocks duplicate submits while a request is pending', async () => {
    let resolveFetch: (value: { ok: boolean; json: () => Promise<object> }) => void = () => undefined;
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );
    vi.stubGlobal('fetch', fetchMock);
    runLoginScript();

    const form = document.querySelector('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    resolveFetch({ ok: false, json: async () => ({}) });
    await vi.waitFor(() => expect((document.querySelector('.login-submit') as HTMLButtonElement).disabled).toBe(false));
  });
});
