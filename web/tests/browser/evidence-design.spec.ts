import {expect,test} from '@playwright/test';

test('immutable evidence page preserves source data, feedback and scoped drawer',async({page})=>{
  await page.goto('/login');
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola',{exact:true}).fill('synthetic-browser-password');
  await page.getByRole('button',{name:'Giriş yap',exact:true}).click();
  await expect(page).toHaveURL(/\/funds$/);
  const response=await page.request.get('/api/p/signals?fund_code=THF');
  expect(response.ok()).toBe(true);
  const {items}=await response.json();expect(items.length).toBeGreaterThan(0);
  const item=items[0];
  await page.goto(`/developments/${encodeURIComponent(item.evidence_id)}?fund=THF`);
  await expect(page.getByRole('heading',{name:'Ne gözlendi',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Evet',exact:true}).click();
  await expect(page.getByText('Geri bildiriminiz kaydedildi.')).toBeVisible();
  await page.reload();await expect(page.getByRole('button',{name:'Evet',exact:true})).toHaveAttribute('aria-pressed','true');
  await page.route('**/api/p/chat',async route=>{
    expect(route.request().postDataJSON().evidence_id).toBe(item.evidence_id);
    await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"AI_OFF"}'});
  });
  await page.getByRole('button',{name:'Kanıtlarla sohbet',exact:true}).click();
  const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
  await dialog.getByLabel('Fon kanıtları hakkında sorunuz').fill('Bu kanıt neyi gösteriyor?');
  await dialog.getByRole('button',{name:'Soruyu gönder',exact:true}).click();
  await expect(dialog.getByRole('alert')).toContainText('Sohbet şu anda kapalı');
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
