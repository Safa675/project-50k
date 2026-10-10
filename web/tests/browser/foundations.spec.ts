import {expect, test} from '@playwright/test';

test('public landing reports real database readiness and preserves integrity labels', async ({page, request}) => {
  await page.goto('/');
  await expect(page).toHaveTitle('BlackSwan');
  await expect(page.locator('html')).toHaveAttribute('lang', 'tr');
  await expect(page.getByRole('status')).toHaveText('Veritabanı bağlantısı hazır');
  await expect(page.locator('footer')).toContainText('Veri hakları incelenmedi');
  await expect(page.locator('footer')).toContainText('Yatırım tavsiyesi değildir');
  const response = await request.get('/api/p/funds');
  expect(response.status()).toBe(401);
  expect(await response.json()).toEqual({error: 'AUTHENTICATION_REQUIRED'});
});

test('mobile landing has no horizontal page overflow', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto('/');
  await expect(page.getByRole('heading', {level: 1})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
