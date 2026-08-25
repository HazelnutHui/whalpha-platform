import { useI18n } from './I18nProvider';

export function LanguageSelector(): JSX.Element {
  const { locale, setLocale, t } = useI18n();
  return (
    <div className="language-selector" role="group" aria-label={t('language.selectorAria')}>
      <span>{t('language.label')}</span>
      <button type="button" className={locale === 'en' ? 'active' : ''} aria-pressed={locale === 'en'} onClick={() => setLocale('en')}>{t('language.en')}</button>
      <button type="button" className={locale === 'zh' ? 'active' : ''} aria-pressed={locale === 'zh'} onClick={() => setLocale('zh')}>{t('language.zh')}</button>
    </div>
  );
}
