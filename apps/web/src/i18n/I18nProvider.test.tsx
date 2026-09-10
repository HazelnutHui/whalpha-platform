import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { LanguageSelector } from './LanguageSelector';
import {
  I18nProvider,
  LOCALE_STORAGE_KEY,
  canonicalLocaleUrl,
  resolveLocale,
  useI18n,
} from './I18nProvider';
import { catalogs, englishMessages, loadCatalog } from './catalog';

function Probe(): JSX.Element {
  const { locale, htmlLang, t } = useI18n();
  return <><output data-testid="locale">{locale}</output><output data-testid="html-lang">{htmlLang}</output><h1>{t('regime.title')}</h1><LanguageSelector /></>;
}

function mount(url = '/dashboard/?view=regime&universe=provider_classified_common_shares_v1'): void {
  window.history.replaceState({}, '', url);
  render(<I18nProvider><Probe /></I18nProvider>);
}

describe('typed interface locale state', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = '';
  });
  afterEach(cleanup);

  it('keeps the English, Chinese, and Spanish dictionary key sets exactly aligned', async () => {
    const spanish = await loadCatalog('es');
    expect(Object.keys(catalogs.en).sort()).toEqual(Object.keys(catalogs.zh).sort());
    expect(Object.keys(catalogs.en).sort()).toEqual(Object.keys(spanish).sort());
    expect(Object.keys(catalogs.en)).toHaveLength(Object.keys(englishMessages).length);
    expect(Object.values(catalogs.en).every(Boolean)).toBe(true);
    expect(Object.values(catalogs.zh).every(Boolean)).toBe(true);
    expect(Object.values(spanish).every(Boolean)).toBe(true);
    const placeholders = (value: string) => Array.from(value.matchAll(/\{([A-Za-z0-9_]+)\}/g), (match) => match[1]).sort();
    for (const key of Object.keys(englishMessages) as Array<keyof typeof englishMessages>) {
      expect(placeholders(spanish[key]), `Spanish placeholders for ${key}`).toEqual(placeholders(englishMessages[key]));
    }
    expect(Object.keys(englishMessages).filter((key) => spanish[key as keyof typeof englishMessages] === englishMessages[key as keyof typeof englishMessages]).length).toBeLessThan(40);
  });

  it('uses legal URL locale, then explicit storage, then English', () => {
    expect(resolveLocale('?lang=en', 'zh')).toBe('en');
    expect(resolveLocale('?lang=zh', 'en')).toBe('zh');
    expect(resolveLocale('?lang=es', 'zh')).toBe('es');
    expect(resolveLocale('?view=regime', 'zh')).toBe('zh');
    expect(resolveLocale('?view=regime', null)).toBe('en');
    expect(resolveLocale('?lang=javascript%3Aalert(1)', 'zh')).toBe('en');
  });

  it('defaults to English regardless of browser language and canonicalizes the URL', async () => {
    Object.defineProperty(window.navigator, 'language', { configurable: true, value: 'zh-CN' });
    mount();
    expect(screen.getByTestId('locale')).toHaveTextContent('en');
    expect(screen.getByText('Market Regime & Opportunities')).toBeInTheDocument();
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('lang')).toBe('en'));
    expect(document.documentElement.lang).toBe('en');
  });

  it('uses stored Chinese only when the URL has no locale', async () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, 'zh');
    mount();
    expect(screen.getByTestId('locale')).toHaveTextContent('zh');
    expect(screen.getByText('市场风向与机会')).toBeInTheDocument();
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh'));
    expect(document.documentElement.lang).toBe('zh-CN');
  });

  it('switches explicitly without losing view or universe and restores locale on popstate', async () => {
    mount('/dashboard/?view=regime&universe=provider_classified_common_shares_v1&lang=en');
    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('zh');
    expect(new URLSearchParams(window.location.search).get('view')).toBe('regime');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_v1');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
    expect(screen.getByText('市场风向与机会')).toBeInTheDocument();

    act(() => {
      window.history.pushState({}, '', '/dashboard/?view=regime&universe=provider_classified_common_shares_plus_adrs_v1&lang=en');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await waitFor(() => expect(screen.getByTestId('locale')).toHaveTextContent('en'));
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');
    expect(screen.getByText('Market Regime & Opportunities')).toBeInTheDocument();
  });

  it('loads professional Spanish on demand without losing query state', async () => {
    mount('/dashboard/?view=regime&universe=provider_classified_common_shares_v1&lang=en');
    fireEvent.click(screen.getByRole('button', { name: 'Español' }));
    await waitFor(() => expect(screen.getByTestId('locale')).toHaveTextContent('es'));
    await waitFor(() => expect(screen.getByText('Régimen de mercado y oportunidades')).toBeInTheDocument());
    expect(document.documentElement.lang).toBe('es');
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('es');
    expect(new URLSearchParams(window.location.search).get('view')).toBe('regime');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_v1');
  });

  it('safely canonicalizes an illegal URL locale to English even with stored Chinese', async () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, 'zh');
    mount('/dashboard/?view=regime&lang=%3Cscript%3E');
    expect(screen.getByTestId('locale')).toHaveTextContent('en');
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('lang')).toBe('en'));
    expect(window.location.search).toContain('view=regime');
  });

  it('builds canonical links without changing unrelated query state', () => {
    const url = canonicalLocaleUrl('http://localhost/dashboard/?view=regime&universe=primary&window=20', 'zh');
    expect(url.searchParams.get('lang')).toBe('zh');
    expect(url.searchParams.get('view')).toBe('regime');
    expect(url.searchParams.get('universe')).toBe('primary');
    expect(url.searchParams.get('window')).toBe('20');
  });
});
