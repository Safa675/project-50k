import {test,expect} from '@playwright/test';

test('signed-out watchlist opens real login without a fabricated personal feed',async({page})=>{
  await page.goto('/watchlist');
  await expect(page.getByRole('heading',{name:'Takip listesi için giriş gerekir'})).toBeVisible();
  await expect(page.getByText('Fonlar tek yerde',{exact:true})).toBeVisible();
  await expect(page.getByText('Örnek A Portföy Para Piyasası Fonu',{exact:true})).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.locator('.watch-login-call').getByRole('link',{name:'Giriş yap',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
});

test('saved funds survive reload, notification preferences persist and removal updates the list',async({page})=>{
  await page.goto('/login');
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola',{exact:true}).fill('synthetic-browser-password');
  await page.getByRole('button',{name:'Giriş yap',exact:true}).click();
  await expect(page).toHaveURL(/\/funds$/);
  await page.goto('/funds/THF');
  await expect(page.getByRole('button',{name:/^THF: Takip/})).toBeEnabled();
  const remove=page.getByRole('button',{name:'THF: Takipten çıkar',exact:true});
  if(await remove.count())await remove.click();
  await page.getByRole('button',{name:'THF: Takip et',exact:true}).click();
  await expect(page.getByRole('button',{name:'THF: Takipten çıkar',exact:true})).toBeVisible();
  await page.goto('/watchlist');
  await expect(page.getByRole('heading',{name:'Takip listem',exact:true})).toBeVisible();
  await expect(page.locator('.watch-fund-name').filter({hasText:'THF'})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button',{name:'THF: Takipten çıkar',exact:true})).toBeVisible();
  await page.goto('/notifications');
  const preference=page.getByRole('checkbox');
  await preference.uncheck();
  await expect(page.getByRole('heading',{name:'Uygulama içi bildirimler kapalı.'})).toBeVisible();
  await expect(page.locator('.bs-notifications-link')).toHaveAttribute('aria-label','Bildirimler');
  await expect(page.locator('.bs-notification-dot')).toHaveCount(0);
  await page.reload();
  await expect(preference).not.toBeChecked();
  await preference.check();
  await expect(preference).toBeChecked();
  await expect(page.getByRole('heading',{name:'Uygulama içi bildirimler kapalı.'})).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.goto('/watchlist');
  await page.getByRole('button',{name:'THF: Takipten çıkar',exact:true}).click();
  await expect(page.locator('.watch-fund-name').filter({hasText:'THF'})).toHaveCount(0);
});
