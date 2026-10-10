import {expect,test} from '@playwright/test';

test('Figma landing preserves access boundaries and theme choice',async({page,request})=>{
  await page.goto('/');
  await expect(page).toHaveTitle('BlackSwan');
  await expect(page.locator('html')).toHaveAttribute('lang','tr');
  await expect(page.getByRole('heading',{level:1})).toContainText('Kara kuğu öngörülemez.');
  await expect(page.getByRole('navigation',{name:'Ana gezinme'}).getByRole('link',{name:'Yöntem'})).toHaveAttribute('href','/method');
  await expect(page.locator('body')).not.toContainText('Veri hakları incelenmedi');
  await expect(page.locator('footer')).toContainText('Yatırım tavsiyesi değildir');
  const toggle=page.getByRole('switch',{name:'Açık tema'});
  await toggle.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.reload();
  await expect(toggle).toBeChecked();
  await toggle.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  const response=await request.get('/api/p/funds');
  expect(response.status()).toBe(401);
  expect(await response.json()).toEqual({error:'AUTHENTICATION_REQUIRED'});
});

test('landing search submits the requested fund to the protected catalog',async({page})=>{
  await page.goto('/');
  const search=page.locator('.bs-search-large input');
  await search.fill('THF');
  await search.press('Enter');
  await expect(page).toHaveURL(/\/login$/);
});

test('method navigation and static assets work at desktop and mobile widths',async({page})=>{
  await page.goto('/method');
  await page.getByRole('navigation',{name:'Yöntem bölümleri'}).getByRole('link',{name:'Sınırlar',exact:true}).click();
  await expect(page).toHaveURL(/#limits$/);
  await expect(page.locator('#limits')).toContainText('BIST 30');
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:900});
    for(const path of ['/','/method']){
      await page.goto(path);
      await expect(page.getByRole('heading',{level:1})).toBeVisible();
      await page.evaluate(()=>document.fonts.ready);
      const geometry=await page.locator('img[src^="/design/"]').evaluateAll(images=>images.map(node=>{
        const image=node as HTMLImageElement,box=image.getBoundingClientRect();
        return {source:image.getAttribute('src'),complete:image.complete,naturalWidth:image.naturalWidth,naturalHeight:image.naturalHeight,width:box.width,height:box.height};
      }));
      expect(geometry.length).toBeGreaterThan(4);
      for(const image of geometry){expect(image.complete).toBe(true);expect(image.naturalWidth).toBeGreaterThan(0);if(image.width>0){expect(Math.abs(image.width-image.naturalWidth)).toBeLessThan(1);expect(Math.abs(image.height-image.naturalHeight)).toBeLessThan(1);}}
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    }
  }
});
