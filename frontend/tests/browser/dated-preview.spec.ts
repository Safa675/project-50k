import {test, expect, type Page} from '@playwright/test';
import {DATED_EXACT, PREVIEW_STATES, deniedTerms} from '../../src/lib/dated-presentation';

// The preview renders only authored synthetic data from src/lib/dated-synthetic.ts.
// Any API request from it is a failure.
async function guardRequests(page: Page) {
  const api: string[] = [];
  page.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) api.push(request.url()); });
  return api;
}
async function mainText(page: Page) {
  return page.evaluate(() => {
    const main = document.querySelector('main')!.cloneNode(true) as HTMLElement;
    main.querySelectorAll('select').forEach(element => element.remove());
    return main.textContent ?? '';
  });
}

for (const [state] of PREVIEW_STATES) {
  test(`preview state ${state} is labelled synthetic, guarded and free of denylisted wording`, async ({page}) => {
    const api = await guardRequests(page);
    await page.goto(`/preview/dates?state=${state}`);
    await expect(page.locator('.archive-label')).toHaveText('Örnek verilerle tasarım önizlemesi · Tarih görünümü');
    await expect(page.getByText('Bu ekrandaki tarih dizini, fonlar ve sayılar tamamen örnektir.', {exact: false}).first()).toBeVisible();
    await expect(page.getByText(DATED_EXACT.guard, {exact: true})).toBeVisible();
    await expect(page.getByRole('link', {name: 'Fon araştırması', exact: false}).first()).toHaveAttribute('href', '/preview/dates');
    const text = await mainText(page);
    expect(deniedTerms(text)).toEqual([]);
    const codes = await page.locator('.fund-code').allTextContents();
    expect(codes.every(code => /^Z\d{2}\b/.test(code.trim()))).toBe(true);
    if (['index-loading', 'index-error', 'invalid-date', 'unregistered-date', 'bundle-loading', 'bundle-error', 'mismatch'].includes(state)) {
      await expect(page.locator('.desktop-funds')).toHaveCount(0);
      await expect(page.locator('.stats')).toHaveCount(0);
      expect(codes).toEqual([]);
    }
    if (state.includes('error') || state.includes('date') && state !== 'early-date' || state === 'mismatch') await expect(page.locator('.error-panel[role="alert"]')).toContainText('Bu durumda fon sonucu gösterilmiyor.');
    expect(api).toEqual([]);
  });
}

test('ready and early-date previews show their own date, denominators and unpriced records', async ({page}) => {
  await page.goto('/preview/dates');
  await expect(page.getByRole('heading', {level: 1, name: 'Fonlar · 16 Eylül 2026', exact: true})).toBeVisible();
  await expect(page.locator('.desktop-funds tbody tr')).toHaveCount(100);
  await expect(page.getByText('Ad ve kategoriler: 7 Ekim 2026 anlık görüntüsü.', {exact: true})).toBeVisible();
  await page.goto('/preview/dates?state=early-date');
  await expect(page.getByRole('heading', {level: 1, name: 'Fonlar · 31 Ekim 2025', exact: true})).toBeVisible();
  await expect(page.locator('.desktop-funds tbody tr').filter({hasText: 'Bu tarihte fiyat kaydı yok'})).toHaveCount(4);
  await expect(page.locator('.desktop-funds tbody tr').filter({hasText: 'Güncel gözlem eksik'})).toHaveCount(1);
  await expect(page.getByText('Seçilen tarihte veya öncesinde fiyat kaydı olmayan fon: 4 / 100 fon', {exact: false})).toBeVisible();
});

test('preview select and submit are keyboard reachable and navigate only on submit', async ({page}) => {
  await page.goto('/preview/dates');
  const select = page.getByLabel('İnceleme tarihi', {exact: true});
  await select.focus();
  await expect(select).toBeFocused();
  await select.selectOption('2026-01-30');
  await page.waitForTimeout(300);
  await expect(page).toHaveURL(/\/preview\/dates$/);
  await page.keyboard.press('Tab');
  const submit = page.getByRole('button', {name: 'Tarihi göster', exact: true});
  await expect(submit).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/preview\/dates\?date=2026-01-30$/);
  await expect(page.getByRole('heading', {level: 1, name: 'Fonlar · 30 Ocak 2026', exact: true})).toBeVisible();
});

test('preview detail is D1-only and links back to its date', async ({page}) => {
  await page.goto('/preview/dates?state=early-date');
  await page.locator('.desktop-funds').getByRole('link', {name: 'Z00 ↗', exact: true}).click();
  await expect(page).toHaveURL(/state=detail&date=2025-10-31&detail=Z00/);
  await expect(page.getByRole('heading', {name: 'Benzer fonlara göre getiri farkı · D1', exact: true})).toBeVisible();
  await expect(page.getByText('Gösterilen gözlemler tasarım için hazırlanmış örnek veridir.', {exact: false})).toBeVisible();
  await expect(page.getByRole('link', {name: DATED_EXACT.fixedViewLink, exact: true})).toHaveAttribute('href', '/preview');
  await page.getByRole('link', {name: '← Fon listesine dön', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1, name: 'Fonlar · 31 Ekim 2025', exact: true})).toBeVisible();
});

for (const width of [390, 768, 1440]) {
  test(`preview ready and detail have no horizontal overflow at ${width}px`, async ({page}) => {
    await page.setViewportSize({width, height: 900});
    for (const url of ['/preview/dates', '/preview/dates?state=detail', '/preview/dates?state=mismatch']) {
      await page.goto(url);
      await expect(page.getByRole('heading', {level: 1})).toBeVisible();
      await expect.poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
  });
}
