import {expect, test} from '@playwright/test';

test.beforeEach(async ({page}) => {
  await page.goto('/login');
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola', {exact: true}).fill('synthetic-browser-password');
  await page.getByRole('button', {name: 'Giriş yap', exact: true}).click();
  await expect(page).toHaveURL(/\/funds$/);
  await page.goto('/funds/THF');
});

test('chat sends CSRF and renders only the complete synthetic validated answer as plain text', async ({page}) => {
  const thread = '00000000-0000-4000-8000-000000000001';
  const question = 'Bu fonun kanıt sınırları nelerdir?';
  const answer = 'Sentetik kanıtın kapsamı sınırlıdır. <strong>Bu metin HTML değildir.</strong>';
  const requests: {fund_code: string; question: string; thread_id: string|null}[] = [];
  await page.route('**/api/p/chat', async route => {
    expect(route.request().headers()['x-csrf-token']).toBeTruthy();
    requests.push(route.request().postDataJSON());
    await route.fulfill({contentType: 'text/event-stream', body:
      'event: tool\ndata: {"name":"get_signals"}\n\n' +
      `event: answer\ndata: ${JSON.stringify({thread_id: thread, content: answer, evidence_ids: ['ev:synthetic-browser'], model: 'synthetic-test-model'})}\n\n`,
    });
  });
  await expect(page.getByText(/Yazdığınız sorular OpenAI'a iletilir/)).toBeVisible();
  await page.getByLabel('Fon kanıtları hakkında sorunuz').fill(question);
  await page.getByRole('button', {name: 'Soruyu gönder', exact: true}).click();
  const log = page.getByRole('log', {name: 'Sohbet mesajları'});
  await expect(log.getByText(answer, {exact: true})).toBeVisible();
  expect(await log.locator('strong').allTextContents()).toEqual(['Siz', 'BlackSwan']);
  await log.getByText('Yanıtın kanıt bağlantıları', {exact: true}).click();
  await expect(log.getByText('ev:synthetic-browser', {exact: true})).toBeVisible();
  await page.getByLabel('Fon kanıtları hakkında sorunuz').fill('Bu sınırlamayı açıklar mısın?');
  await page.getByRole('button', {name: 'Soruyu gönder', exact: true}).click();
  await expect(log.locator('.chat-assistant')).toHaveCount(2);
  expect(requests).toEqual([
    {fund_code: 'THF', question, thread_id: null},
    {fund_code: 'THF', question: 'Bu sınırlamayı açıklar mısın?', thread_id: thread},
  ]);
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test('chat rejects partial model text and keeps AI off failures explicit', async ({page}) => {
  await page.route('**/api/p/chat', route => route.fulfill({contentType: 'text/event-stream', body:
    'event: delta\ndata: {"content":"UNVALIDATED_SYNTHETIC_TEXT"}\n\n',
  }));
  await page.getByLabel('Fon kanıtları hakkında sorunuz').fill('Kanıtın kapsamını açıklar mısın?');
  await page.getByRole('button', {name: 'Soruyu gönder', exact: true}).click();
  await expect(page.locator('.chat-panel').getByRole('alert')).toHaveText('Sohbet yanıtı doğrulanamadı ve gösterilmedi.');
  await expect(page.getByText('UNVALIDATED_SYNTHETIC_TEXT', {exact: true})).toHaveCount(0);
  await expect(page.locator('.chat-assistant')).toHaveCount(0);
  await page.unroute('**/api/p/chat');
  await page.route('**/api/p/chat', route => route.fulfill({status: 503, contentType: 'application/json', body: '{"error":"AI_OFF"}'}));
  await page.getByRole('button', {name: 'Soruyu gönder', exact: true}).click();
  await expect(page.locator('.chat-panel').getByRole('alert')).toHaveText('Sohbet şu anda kapalı. Bir model yanıtı üretilmedi.');
  await expect(page.locator('.chat-assistant')).toHaveCount(0);
});

test('chat displays the actual isolated backend AI off response without a fabricated answer', async ({page}) => {
  const response = page.waitForResponse(value => value.url().endsWith('/api/p/chat') && value.request().method() === 'POST');
  await page.getByLabel('Fon kanıtları hakkında sorunuz').fill('Bu fonun detektör kanıtları nelerdir?');
  await page.getByRole('button', {name: 'Soruyu gönder', exact: true}).click();
  const result = await response;
  expect(result.status()).toBe(503);
  expect(await result.json()).toEqual({detail: 'AI_OFF'});
  await expect(page.locator('.chat-panel').getByRole('alert')).toHaveText('Sohbet şu anda kapalı. Bir model yanıtı üretilmedi.');
  await expect(page.locator('.chat-assistant')).toHaveCount(0);
});
