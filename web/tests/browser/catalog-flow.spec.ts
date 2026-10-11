import {expect,test} from '@playwright/test';

test('catalog and developments are separate views and filters follow the selected view',async({page})=>{
  await page.goto('/login');await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');await page.getByLabel('Parola',{exact:true}).fill('synthetic-browser-password');await page.getByRole('button',{name:'Giriş yap',exact:true}).click();await expect(page).toHaveURL(/\/funds$/);
  const tabs=page.getByRole('navigation',{name:'Keşfet görünümleri'});
  await expect(tabs.getByRole('link',{name:'Tüm fonlar',exact:true})).toHaveAttribute('aria-current','page');
  await expect(page.locator('#fund-catalog')).toBeVisible();
  await page.getByLabel('Fon kodu veya adı').fill('THF');await page.getByRole('button',{name:'Ara',exact:true}).click();
  await expect(page.getByRole('link',{name:'THF',exact:true})).toBeVisible();
  await tabs.getByRole('link',{name:'Gelişmeler',exact:true}).click();
  await expect(page).toHaveURL(/view=developments.*q=THF/);
  await expect(tabs.getByRole('link',{name:'Gelişmeler',exact:true})).toHaveAttribute('aria-current','page');
  await expect(page.locator('#fund-developments')).toBeVisible();
  await expect(page.locator('#fund-catalog')).toHaveCount(0);
  await page.getByRole('link',{name:'Filtreleri temizle',exact:true}).click();
  await expect(page).toHaveURL(/view=developments$/);
  await tabs.getByRole('link',{name:'Tüm fonlar',exact:true}).click();
  await expect(page.locator('#fund-catalog')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Fon kataloğu',exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
