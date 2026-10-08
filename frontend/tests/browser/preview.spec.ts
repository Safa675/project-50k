import {test,expect} from '@playwright/test';
test('synthetic list keeps searchable rows and no-match state',async({page})=>{
 await page.goto('/preview');await expect(page.getByRole('heading',{name:'Fonların verileri ne söylüyor?'})).toBeVisible();
 await expect(page.getByText('Örnek verilerle tasarım önizlemesi')).toBeVisible();
 await page.getByPlaceholder('Kod veya fon adı ara').fill('AAA');await expect(page.getByText('1 / 6 fon gösteriliyor')).toBeVisible();
 await page.getByPlaceholder('Kod veya fon adı ara').fill('no such fund');await expect(page.getByText('Aramanızla eşleşen fon yok')).toBeVisible();
 await page.getByRole('button',{name:'Filtreleri temizle'}).first().click();await expect(page.getByText('6 / 6 fon gösteriliyor')).toBeVisible();
});
test('detail distinguishes period, missing chart and source state',async({page})=>{
 await page.goto('/preview?detail=DDD');await expect(page.getByText('Grafik için yeterli veri yok')).toBeVisible();
 await expect(page.getByRole('heading',{name:'İki ayrı araştırma hesabı'})).toBeVisible();await expect(page.getByText('Kaynak görünümü örneği')).toBeVisible();
 await page.getByRole('link',{name:'Fon listesine dön'}).click();await expect(page.getByRole('heading',{name:'Fonların verileri ne söylüyor?'})).toBeVisible();
});
test('error and loading states do not invent results',async({page})=>{
 await page.goto('/preview?state=error');await expect(page.getByText('Araştırma verisi alınamadı.')).toBeVisible();await expect(page.getByRole('button',{name:'Filtreleri temizle'})).toHaveCount(0);
 await page.goto('/preview?state=loading');await expect(page.getByText('Araştırma verisi yükleniyor…')).toBeVisible();
});
test('mobile retains comments, finding state and keyboard focus',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/preview');
 await expect(page.locator('.mobile-funds')).toBeVisible();await expect(page.locator('.desktop-funds')).toBeHidden();
 await expect(page.locator('.mobile-fund')).toHaveCount(6);
 await expect(page.locator('.mobile-fund').first().getByText('Hisse senedi',{exact:true})).toBeVisible();
 await expect(page.locator('.mobile-fund').first().getByText('Getiri farkı · D1',{exact:true})).toBeVisible();
 await expect(page.locator('.mobile-fund').first().getByText('Tahmini para hareketi',{exact:true})).toBeVisible();
 await page.getByPlaceholder('Kod veya fon adı ara').focus();await page.keyboard.press('Tab');await expect(page.getByLabel('Kategori',{exact:true})).toBeFocused();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);expect(overflow).toBe(false);
});
test('filtered detail navigation returns to the same list filters',async({page})=>{
 await page.goto('/preview?q=AAA&category=Hisse%20senedi&finding=two');
 await expect(page.getByText('1 / 6 fon gösteriliyor')).toBeVisible();
 await page.locator('.desktop-funds').getByRole('link',{name:'AAA ↗'}).click();
 await page.getByRole('link',{name:'Fon listesine dön'}).click();
 await expect(page.getByPlaceholder('Kod veya fon adı ara')).toHaveValue('AAA');
 await expect(page.getByLabel('Kategori',{exact:true})).toHaveValue('Hisse senedi');
 await expect(page.getByLabel('Bulgu',{exact:true})).toHaveValue('two');
 await expect(page.getByText('1 / 6 fon gösteriliyor')).toBeVisible();
});
