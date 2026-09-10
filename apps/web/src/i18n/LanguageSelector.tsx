import { useI18n } from './I18nProvider';
import { preloadCatalog } from './catalog';

export function LanguageSelector(): JSX.Element {
  const { locale, setLocale, t } = useI18n();
  return (
    <div className="language-selector" role="group" aria-label={t('language.selectorAria')}>
      <span>{t('language.label')}</span>
      <button type="button" className={locale === 'en' ? 'active' : ''} aria-pressed={locale === 'en'} onClick={() => setLocale('en')}>{t('language.en')}</button>
      <button type="button" className={locale === 'zh' ? 'active' : ''} aria-pressed={locale === 'zh'} onClick={() => setLocale('zh')}>{t('language.zh')}</button>
      <button type="button" className={locale === 'es' ? 'active' : ''} aria-pressed={locale === 'es'} onPointerEnter={() => preloadCatalog('es')} onFocus={() => preloadCatalog('es')} onClick={() => setLocale('es')}>{t('language.es')}</button>
    </div>
  );
}
