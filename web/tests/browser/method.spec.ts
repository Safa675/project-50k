import {expect,test} from '@playwright/test';

test('method disclosures explain the actual comparison windows and lower-bound rule',async({page})=>{
  await page.goto('/method');
  const recent=page.locator('.bs-method-list article').filter({has:page.getByRole('heading',{name:'Benzer fonlardan farklı hareket',exact:true})});
  await recent.getByText('Bu sonuca nasıl ulaştık?',{exact:true}).click();
  await expect(recent).toContainText('son 60 tarihin');
  await expect(recent).toContainText('En az 50');
  await expect(recent).toContainText('en az 10 başka fon');
  const relation=page.locator('.bs-method-list article').filter({has:page.getByRole('heading',{name:'Benzer fonlarla birlikte hareket',exact:true})});
  await relation.getByText('Bu sonuca nasıl ulaştık?',{exact:true}).click();
  await expect(relation).toContainText('Son 120 tarih');
  await expect(relation).toContainText('en az 100');
  await expect(relation).toContainText('alt sınırın altına düşmek');
  await expect(page.locator('#evidence')).toContainText('sayıları veya karşılaştırma sınırlarını değiştiremez');
  await expect(page.locator('#limits')).toContainText('bu fon hesaplamaları hisselere uygulanmaz');
  expect(await page.locator('body').innerText()).not.toMatch(/\bD[1-5]\b|AN-DQ-\d+|AN-FND-\d+/);
});
