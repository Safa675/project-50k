import {test, expect, type Page} from '@playwright/test';
import {BUNDLE_ID, researchFixture} from '../fixtures/research';

// Regression for the unchanged fixed-date view, using the existing v1 fixture
// mock pattern. Dated routes must never be requested from the fixed view.
async function mockFixed(page: Page) {
  const fixture = researchFixture();
  const unexpected: string[] = [];
  await page.route('**/api/research-dated/**', async route => { unexpected.push(route.request().url()); await route.abort(); });
  await page.route('**/api/research/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let payload: unknown;
    if (path === '/api/research/v1/funds') payload = fixture.list;
    else if (path === '/api/research/v1/summary') payload = fixture.summary;
    else if (path.startsWith('/api/research/v1/funds/')) payload = fixture.detail(path.slice('/api/research/v1/funds/'.length));
    if (payload === undefined) { unexpected.push(path); await route.abort(); return; }
    await route.fulfill({status: 200, contentType: 'application/json', headers: {'cache-control': 'no-store'}, body: JSON.stringify(payload)});
  });
  return unexpected;
}

test('fixed list still shows its 16 September cutoff and July → August flow period', async ({page}) => {
  const unexpected = await mockFixed(page);
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Fonların verileri ne söylüyor?', exact: true})).toBeVisible();
  await expect(page.locator('.cutoff')).toContainText('16 Eylül 2026 · 23:59 İstanbul');
  await expect(page.getByText('Temmuz → Ağustos 2026', {exact: false})).toBeVisible();
  await expect(page.getByLabel('İnceleme tarihi')).toHaveCount(0);
  expect(unexpected).toEqual([]);
});

test('fixed detail still shows its 16 September cutoff and July/August endpoints', async ({page}) => {
  const unexpected = await mockFixed(page);
  await page.goto(`/funds/S00?bundle=${BUNDLE_ID}`);
  await expect(page.getByRole('heading', {name: 'İki ayrı araştırma hesabı', exact: true})).toBeVisible();
  await expect(page.locator('.cutoff')).toContainText('16 Eylül 2026 · 23:59 İstanbul');
  await expect(page.getByText('Temmuz toplam değer', {exact: true}).first()).toBeVisible();
  await expect(page.getByText('Ağustos toplam değer', {exact: true}).first()).toBeVisible();
  expect(unexpected).toEqual([]);
});
