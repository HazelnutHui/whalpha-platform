import { describe, expect, it } from 'vitest';

const productionSources = import.meta.glob<string>('./**/*.{ts,tsx}', {
  eager: true,
  import: 'default',
  query: '?raw',
});

const staticFixtureImport = /(?:^|\n)\s*import(?:\s+type)?[\s\S]*?\sfrom\s+['"][^'"]*fixtures\/marketDemo['"]/m;

describe('production Dashboard demo isolation', () => {
  it('keeps the demo fixture outside every production static dependency edge', () => {
    const violations = Object.entries(productionSources)
      .filter(([path]) => !path.includes('.test.') && !path.includes('/fixtures/'))
      .filter(([, source]) => staticFixtureImport.test(source))
      .map(([path]) => path)
      .sort();

    expect(violations).toEqual([]);
  });

  it('loads the fixture only through the explicit development-only boundary', () => {
    const page = productionSources['./pages/MarketDashboardPage.tsx'];
    expect(page).toContain('import.meta.env.DEV');
    expect(page).toContain("import('../fixtures/marketDemo')");
    expect(page).not.toMatch(/from\s+['"]\.\.\/fixtures\/marketDemo['"]/);
  });
});
