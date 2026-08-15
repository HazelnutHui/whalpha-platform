(() => {
  const params = new URLSearchParams(window.location.search);
  const next = params.get('next');
  const safeNext = next && next.startsWith('/dashboard/') ? next : '/dashboard/';
  const nextInput = document.getElementById('next');
  if (nextInput instanceof HTMLInputElement) {
    nextInput.value = safeNext;
  }
  if (params.get('error') === '1') {
    document.getElementById('login-error')?.classList.add('visible');
  }
  const form = document.querySelector('form');
  const button = document.querySelector('.login-submit');
  form?.addEventListener('submit', () => {
    if (button instanceof HTMLButtonElement) {
      button.setAttribute('aria-busy', 'true');
      button.textContent = 'Signing In';
    }
  });
})();
