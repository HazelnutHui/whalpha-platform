(() => {
  const DEFAULT_NEXT = '/dashboard/';
  const navigate = window.__whalphaNavigate || ((path) => window.location.assign(path));
  const i18n = window.__whalphaLoginI18n;

  function safeNext(value) {
    if (
      typeof value === 'string' &&
      value.startsWith('/dashboard/') &&
      !value.startsWith('//') &&
      !value.includes('\\') &&
      !/[\u0000-\u001f\u007f]/.test(value)
    ) {
      return value;
    }
    return DEFAULT_NEXT;
  }

  function withLocale(path) {
    const url = new URL(safeNext(path), window.location.origin);
    url.searchParams.set('lang', i18n?.locale === 'zh' ? 'zh' : 'en');
    return `${url.pathname}${url.search}${url.hash}`;
  }
  const params = new URLSearchParams(window.location.search);
  function targetPath() { return withLocale(params.get('next')); }
  const nextInput = document.getElementById('next');
  if (nextInput instanceof HTMLInputElement) {
    nextInput.value = targetPath();
  }
  window.addEventListener('whalpha:localechange', () => { if (nextInput instanceof HTMLInputElement) nextInput.value = targetPath(); setLoading(isSubmitting || isCheckingStatus); });
  const error = document.getElementById('login-error');
  if (params.get('error') === '1') {
    error?.classList.add('visible');
  }
  const form = document.querySelector('form');
  const button = document.querySelector('.login-submit');
  const username = document.getElementById('username');
  const password = document.getElementById('password');
  let isSubmitting = false;
  let isCheckingStatus = true;

  function setLoading(value) {
    if (button instanceof HTMLButtonElement) {
      button.disabled = value;
      button.setAttribute('aria-busy', value ? 'true' : 'false');
      button.textContent = value ? (i18n?.t('submitting') ?? 'Signing In') : (i18n?.t('submit') ?? 'Sign In');
    }
  }

  function showError() {
    error?.classList.add('visible');
    if (password instanceof HTMLInputElement) {
      password.value = '';
      password.focus();
    }
  }

  function setFormVisible(value) {
    if (form instanceof HTMLFormElement) {
      form.hidden = !value;
    }
  }

  async function checkExistingSession() {
    setFormVisible(false);
    setLoading(true);
    try {
      const response = await fetch('/auth/status', {
        method: 'GET',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (response.status === 204) {
        navigate(targetPath());
        return;
      }
    } catch {
      error?.classList.add('visible');
    } finally {
      isCheckingStatus = false;
      setLoading(false);
      setFormVisible(true);
    }
  }

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (isSubmitting || isCheckingStatus) {
      return;
    }
    if (!(username instanceof HTMLInputElement) || !(password instanceof HTMLInputElement)) {
      showError();
      return;
    }
    isSubmitting = true;
    error?.classList.remove('visible');
    setLoading(true);
    const requestedNext = nextInput instanceof HTMLInputElement ? nextInput.value : targetPath;
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          username: username.value,
          password: password.value,
          next: safeNext(requestedNext),
        }),
      });
      if (!response.ok) {
        showError();
        return;
      }
      const payload = await response.json();
      navigate(safeNext(payload.next));
    } catch {
      showError();
    } finally {
      isSubmitting = false;
      setLoading(false);
    }
  });

  void checkExistingSession();
})();
