import {expect, test} from '@playwright/test';

test('protected stock catalog and daily-close evidence use the isolated synthetic backend', async ({page}) => {
  await page.goto('/stocks');
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola', {exact: true}).fill('synthetic-browser-password');
  await page.getByRole('button', {name: 'Giriş yap', exact: true}).click();
  await expect(page).toHaveURL(/\/funds$/);
  await expect(page.getByRole('link', {name: 'İş akışı', exact: true})).toBeVisible();
  await page.getByRole('link', {name: 'Hisseler', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Türkiye hisseleri', exact: true})).toBeVisible();
  await expect(page.getByRole('link', {name: 'İş akışı', exact: true})).toBeVisible();
  await expect(page.getByText('Katalog güncel BIST 30 üyeliğini gösterir. Bu üyelik geçmiş tarihli endeks kapsamı olarak kullanılamaz.', {exact: true})).toBeVisible();
  await page.getByLabel('Hisse kodu veya adı').fill('TESTA');
  await page.getByRole('button', {name: 'Ara', exact: true}).click();
  await page.getByRole('link', {name: 'TESTA', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Yayımlanmış günlük kapanış fiyatı', exact: true})).toBeVisible();
  await expect(page.getByRole('img', {name: /günlük hisse kapanış fiyatı, TRY/})).toBeVisible();
  await expect(page.getByText(/Bölünme ve temettü düzeltmesinin yapıldığı doğrulanmadı/)).toBeVisible();
  await page.getByText('Kapanış fiyatlarını ve kaynaklarını tablo olarak göster', {exact: true}).click();
  await expect(page.getByRole('columnheader', {name: 'Kaynak erişim zamanı', exact: true})).toBeVisible();
  await expect(page.getByRole('cell', {name: 'Veri yok', exact: true}).first()).toBeVisible();
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByRole('link', {name: 'Fonlar', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Türkiye yatırım fonları', exact: true})).toBeVisible();
});
