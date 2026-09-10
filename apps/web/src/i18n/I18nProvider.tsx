import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import {
  catalogs,
  immediateCatalog,
  loadCatalog,
  type Locale,
  type MessageCatalog,
  type MessageKey,
  type MessageValues,
} from './catalog';

export const LOCALE_STORAGE_KEY = 'whalpha.interface.locale';
const HTML_LANG: Record<Locale, string> = { en: 'en', zh: 'zh-CN', es: 'es' };

export function isLocale(value: string | null): value is Locale {
  return value === 'en' || value === 'zh' || value === 'es';
}

export function resolveLocale(search: string, storedLocale: string | null): Locale {
  const urlLocale = new URLSearchParams(search).get('lang');
  if (urlLocale !== null) return isLocale(urlLocale) ? urlLocale : 'en';
  return isLocale(storedLocale) ? storedLocale : 'en';
}

export function canonicalLocaleUrl(href: string, locale: Locale): URL {
  const url = new URL(href);
  url.searchParams.set('lang', locale);
  return url;
}

function interpolate(template: string, values: MessageValues = {}): string {
  return template.replace(/\{([A-Za-z0-9_]+)\}/g, (match, key: string) =>
    Object.prototype.hasOwnProperty.call(values, key) ? String(values[key]) : match,
  );
}

export type Translate = (key: MessageKey, values?: MessageValues) => string;

interface I18nContextValue {
  locale: Locale;
  htmlLang: string;
  t: Translate;
  setLocale: (locale: Locale) => void;
}

const defaultTranslate: Translate = (key, values) => interpolate(catalogs.en[key], values);
const I18nContext = createContext<I18nContextValue>({
  locale: 'en',
  htmlLang: HTML_LANG.en,
  t: defaultTranslate,
  setLocale: () => undefined,
});

function readStoredLocale(): string | null {
  try {
    return window.localStorage.getItem(LOCALE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function applyDocumentLocale(locale: Locale, messages: MessageCatalog): void {
  document.documentElement.lang = HTML_LANG[locale];
  document.title = messages['meta.title'];
  const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (description) description.content = messages['meta.description'];
}

export function I18nProvider({ children }: { children: ReactNode }): JSX.Element {
  const [locale, updateLocale] = useState<Locale>(() => resolveLocale(window.location.search, readStoredLocale()));
  const [messages, updateMessages] = useState<MessageCatalog>(() => immediateCatalog(locale) ?? catalogs.en);

  const canonicalize = useCallback((nextLocale: Locale) => {
    const raw = new URLSearchParams(window.location.search).get('lang');
    if (raw !== nextLocale) {
      window.history.replaceState(window.history.state, '', canonicalLocaleUrl(window.location.href, nextLocale));
    }
  }, []);

  useEffect(() => {
    canonicalize(locale);
  }, [canonicalize, locale]);

  useEffect(() => {
    const immediate = immediateCatalog(locale);
    if (immediate) {
      updateMessages(immediate);
      applyDocumentLocale(locale, immediate);
      return undefined;
    }
    let current = true;
    void loadCatalog(locale)
      .then((loaded) => {
        if (!current) return;
        updateMessages(loaded);
        applyDocumentLocale(locale, loaded);
      })
      .catch(() => {
        if (!current) return;
        try { window.localStorage.setItem(LOCALE_STORAGE_KEY, 'en'); } catch { /* Preserve a working in-session fallback. */ }
        updateMessages(catalogs.en);
        updateLocale('en');
        canonicalize('en');
        applyDocumentLocale('en', catalogs.en);
      });
    return () => { current = false; };
  }, [canonicalize, locale]);

  useEffect(() => {
    const onPopState = () => {
      const nextLocale = resolveLocale(window.location.search, readStoredLocale());
      updateLocale(nextLocale);
      canonicalize(nextLocale);
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [canonicalize]);

  const setLocale = useCallback((nextLocale: Locale) => {
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    } catch {
      // A blocked storage backend must not prevent an explicit in-session choice.
    }
    window.history.pushState(window.history.state, '', canonicalLocaleUrl(window.location.href, nextLocale));
    updateLocale(nextLocale);
  }, []);

  const value = useMemo<I18nContextValue>(() => ({
    locale,
    htmlLang: HTML_LANG[locale],
    t: (key, values) => interpolate(messages[key], values),
    setLocale,
  }), [locale, messages, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
