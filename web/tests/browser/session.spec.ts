import {test,expect} from '@playwright/test';
test('login, fund evidence, human review and logout use the isolated real backend',async({page})=>{
  await page.goto('/funds');await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola',{exact:true}).fill('synthetic-browser-password');
  await page.getByRole('button',{name:'Giriş yap',exact:true}).click();
  await expect(page).toHaveURL(/\/funds$/);
  await page.getByLabel('Fon kodu veya adı').fill('THF');
  await page.getByRole('button',{name:'Ara',exact:true}).click();
  await page.getByRole('link',{name:'THF',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Yayımlanmış günlük birim fiyat'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'İnceleme kararı',exact:true})).toBeVisible();
  await page.getByLabel('İnceleme işlemi').selectOption('OVERRIDE');
  await page.getByLabel('Değiştirilen karar').selectOption('MATERIAL');
  await page.getByLabel('Gerekçe',{exact:true}).fill('Synthetic browser review reason');
  await page.getByRole('button',{name:'İncelemeyi kaydet',exact:true}).click();
  await expect(page.getByText('Etkin karar insan incelemesine dayanıyor.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Çıkış yap',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto('/funds');await expect(page).toHaveURL(/\/login$/);
});
test('login remains usable at mobile width without document overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/login');
  await expect(page.getByRole('button',{name:'Giriş yap',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
