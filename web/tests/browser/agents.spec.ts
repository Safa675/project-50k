import {expect, test, type Page} from '@playwright/test';
import {CASE_ID, login, mockAgents} from './agent-fixtures';

// Synthetic route mocks only: every /api/p/agents and /api/p/chat response comes from agent-fixtures.ts.
const fab = (page: Page) => page.getByRole('button', {name: /^Ajan ekibi ve Raportör/});
const panel = (page: Page) => page.getByRole('dialog', {name: 'Ajan ekibi · 7/24'});
const MODE_CHIPS = ['Yayımlanmış veriler', 'Tarihe göre inceleme', 'Örnek test verileri', 'Örnek test verisi', 'Arşiv verisi', 'Yayımlanmış arşiv verileri'];

async function openPanel(page: Page) {
  await fab(page).click();
  await expect(panel(page)).toBeVisible();
}

test('the dock appears once on every primary page and no page repeats the mode or date as a chip', async ({page}) => {
  await mockAgents(page);
  await login(page);
  for (const path of ['/', '/funds', '/funds/THF', '/stocks', '/stocks/THYAO', '/watchlist', '/notifications', '/method', '/ekip', '/ekip/dogrulayici']) {
    await page.goto(path);
    await expect(fab(page), path).toHaveCount(1);
    await expect(fab(page), path).toBeVisible();
    for (const chip of MODE_CHIPS) await expect(page.getByText(chip, {exact: true}), `${path}: ${chip}`).toHaveCount(0);
    await expect(page.getByRole('button', {name: 'Kanıtlarla sohbet'})).toHaveCount(0);
    await expect(page.getByText('Fon hakkında sorularınız')).toHaveCount(0);
  }
});

test('the panel opens on the live team, shows the workflow and traps focus until Esc', async ({page}) => {
  const mock = await mockAgents(page);
  await login(page);
  await page.goto('/funds');
  await openPanel(page);
  const dialog = panel(page);
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  const expand = dialog.getByRole('button', {name: 'Ekibi genişlet'});
  if (await expand.isVisible()) await expand.click();
  const stage = dialog.getByRole('list', {name: 'Ekibin iş akışı'});
  for (const name of ['Nöbetçi', 'Hipotezci', 'Şüpheci', 'Doğrulayıcı', 'Raportör', 'İnsan kararı']) {
    await expect(stage.getByText(name, {exact: true})).toBeVisible();
  }
  await expect(stage.getByText('Sizinle konuşan ajan')).toBeVisible();
  await expect(dialog.getByText('Sentetik vaka için olası açıklamaları yazıyor.')).toBeVisible();
  await expect(dialog.getByRole('meter', {name: 'Günlük yapay zekâ bütçesi'})).toBeVisible();
  await expect(dialog.getByText('Canlı', {exact: false}).first()).toBeVisible();
  // No identifiers, enum values or raw codes leak into the visible panel.
  const text = await dialog.innerText();
  for (const raw of [CASE_ID, 'waiting_budget', 'hypothesizer', 'case_opened', 'synthetic-model', 'TRIGGERED']) expect(text).not.toContain(raw);
  // Open polling is fast; the team and queue were requested more than once.
  await expect.poll(() => mock.teamCalls(), {timeout: 8000}).toBeGreaterThan(2);
  for (let index = 0; index < 25; index++) {
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(panel(page)).toHaveCount(0);
  await expect(fab(page)).toBeFocused();
});

test('the Sıra tab lists running work, highlighted user requests, budget waits and today’s results', async ({page}) => {
  await mockAgents(page);
  await login(page);
  await page.goto('/funds');
  await openPanel(page);
  await panel(page).getByRole('tab', {name: /^Sıra/}).click();
  const queue = panel(page).getByRole('tabpanel');
  for (const heading of ['Çalışıyor', 'Sırada', 'Bütçe bekliyor', 'Bugün tamamlandı']) await expect(queue.getByRole('heading', {name: new RegExp(`^${heading}`)})).toBeVisible();
  const queued = queue.getByRole('region', {name: /^Sırada/});
  await expect(queued.getByRole('listitem').first()).toContainText('Kullanıcı isteği: sentetik fonu incele');
  await expect(queued.getByRole('listitem').first()).toContainText('Kullanıcı isteği');
  await queue.getByRole('button', {name: /Olası açıklamaları çıkar.*Vakanın akışını aç/}).click();
  const timeline = panel(page).getByRole('tabpanel');
  await expect(timeline.getByRole('heading', {name: 'Sentetik fonda fiyat gelişmesi'})).toBeVisible();
  await expect(timeline.getByRole('list', {name: 'Vakadaki adımlar'})).toContainText('İnsan kararı');
  await expect(timeline.getByText('Gelişme benzer fonlardan ayrışan bir fiyat hareketiyle açıklanabilir.')).toBeVisible();
  await expect(timeline.getByText('Benzer fonlardan ayrışma')).toBeVisible();
});

test('selecting an agent opens its read-only workspace, also as a full page', async ({page}) => {
  await mockAgents(page);
  await login(page);
  await page.goto('/funds');
  await openPanel(page);
  await panel(page).getByRole('button', {name: /^Şüpheci: .*Çalışma alanını aç\.$/}).click();
  const workspace = panel(page).getByRole('tabpanel');
  await expect(workspace.getByRole('heading', {name: 'Şüpheci'})).toBeVisible();
  await expect(workspace.getByText('Ekip çalışması', {exact: true})).toBeVisible();
  await expect(workspace.getByRole('textbox')).toHaveCount(0);
  await workspace.getByRole('link', {name: 'Çalışma alanını tam sayfada aç'}).click();
  await expect(page).toHaveURL(/\/ekip\/supheci$/);
  await expect(page.getByRole('heading', {level: 1, name: 'Şüpheci'})).toBeVisible();
  await expect(page.getByRole('navigation', {name: 'Ajan çalışma alanları'}).getByRole('link', {name: 'Şüpheci'})).toHaveAttribute('aria-current', 'page');
  await page.goto('/ekip/yonetici');
  await expect(page.getByRole('heading', {level: 1, name: 'Şüpheci'})).toHaveCount(0);
});

test('a fund page note leads the Raportör tab and Enter sends to that fund’s conversation', async ({page}) => {
  const mock = await mockAgents(page);
  await login(page);
  await page.goto('/funds/THF');
  await expect.poll(() => mock.pageVisits.some(visit => visit.path === '/funds/THF' && visit.fund_code === 'THF')).toBe(true);
  await openPanel(page);
  await panel(page).getByRole('tab', {name: 'Raportör'}).click();
  const brief = panel(page).getByRole('complementary', {name: 'Bu sayfa için Raportör notu'});
  await expect(brief).toContainText('Bu fonda seçili tarihte inceleme sınırını aşan bir fiyat gelişmesi var.');
  await expect(brief.getByRole('note')).toContainText('Son tarihte kullanılabilir fiyat yok');
  const input = panel(page).getByLabel('Raportöre sorunuz');
  await input.fill('Kaynaklar');
  await input.press('Shift+Enter');
  await expect(input).toHaveValue('Kaynaklar\n');
  await input.fill('Bu fonda hangi kaynaklar var?');
  await input.press('Enter');
  const log = panel(page).getByRole('log', {name: 'Raportör ile sohbet'});
  await expect(log.getByText('Sentetik Raportör yanıtı: Bu fonda hangi kaynaklar var?', {exact: true})).toBeVisible();
  expect(mock.chatBodies.at(-1)).toMatchObject({fund_code: 'THF', question: 'Bu fonda hangi kaynaklar var?', thread_id: null,
    page_context: {path: '/funds/THF', fund_code: 'THF'}});
  await brief.getByRole('button', {name: 'Ekip neyi inceliyor?'}).click();
  await expect(log.getByText('Sentetik Raportör yanıtı: Ekip bu fonda neyi inceliyor?', {exact: true})).toBeVisible();
  expect(mock.chatBodies.at(-1)).toMatchObject({fund_code: 'THF', thread_id: expect.stringMatching(/^0{8}-/)});
  await brief.getByRole('button', {name: 'İncelemeyi öne al'}).click();
  await expect(brief.getByText('İsteğiniz ekibin sırasına alındı.')).toBeVisible();
  expect(mock.requests).toEqual([{fund_code: 'THF', kind: 'investigate'}]);
});

test('outside fund pages the Raportör keeps one general conversation', async ({page}) => {
  const mock = await mockAgents(page);
  await login(page);
  await page.goto('/method');
  await openPanel(page);
  await panel(page).getByRole('tab', {name: 'Raportör'}).click();
  await expect(panel(page).getByRole('button', {name: 'Ekipten inceleme iste'})).toHaveCount(0);
  const input = panel(page).getByLabel('Raportöre sorunuz');
  await input.fill('Ekip şu anda ne yapıyor?');
  await input.press('Enter');
  await expect(panel(page).getByRole('log', {name: 'Raportör ile sohbet'})).toContainText('Sentetik Raportör yanıtı: Ekip şu anda ne yapıyor?');
  expect(mock.chatBodies.at(-1)).toMatchObject({fund_code: null, page_context: {path: '/method', fund_code: null}});
});

test('unavailable agent services show plain error states and no fabricated activity', async ({page}) => {
  await mockAgents(page, {unavailable: true});
  await login(page);
  await page.goto('/funds/THF');
  await openPanel(page);
  await expect(panel(page).getByText('Ekibin canlı durumu şu anda alınamıyor.', {exact: false}).first()).toBeVisible();
  await expect(panel(page).getByText('Çalışıyor', {exact: true})).toHaveCount(0);
  await panel(page).getByRole('tab', {name: 'Raportör'}).click();
  await expect(panel(page).getByText('Bu sayfa için not şu anda hazırlanamadı. Sohbet kullanılabilir.')).toBeVisible();
  await panel(page).getByRole('tab', {name: /^Sıra/}).click();
  await expect(panel(page).getByText('İş sırası şu anda alınamıyor.')).toBeVisible();
});

test('a full daily budget is explained in the queue', async ({page}) => {
  await mockAgents(page, {budgetExhausted: true});
  await login(page);
  await page.goto('/funds');
  await openPanel(page);
  await panel(page).getByRole('tab', {name: /^Sıra/}).click();
  await expect(panel(page).getByRole('note')).toHaveText('Bugünün bütçesi doldu. Yapay zekâ adımları yarın kaldığı yerden devam eder.');
});

test('signed-out visitors get a compact sign-in prompt and no team data', async ({page}) => {
  const mock = await mockAgents(page);
  await page.goto('/');
  const button = page.getByRole('button', {name: 'Ajan ekibi ve Raportör. Kullanmak için giriş gerekir.'});
  await button.click();
  const card = page.getByRole('dialog', {name: 'Ajan ekibi'});
  await expect(card.getByRole('link', {name: 'Giriş yap'})).toHaveAttribute('href', '/login');
  await page.keyboard.press('Escape');
  await expect(card).toHaveCount(0);
  expect(mock.teamCalls() + mock.queueCalls() + mock.pageVisits.length).toBe(0);
});

test('the bottom sheet fits a 390 px screen without horizontal scrolling', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await mockAgents(page);
  await login(page);
  await page.goto('/funds/THF');
  await openPanel(page);
  await expect(panel(page).getByRole('tab', {name: 'Ekip'})).toHaveAttribute('aria-selected', 'true');
  const box = await panel(page).boundingBox();
  expect(box && box.x >= 0 && box.x + box.width <= 390).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await panel(page).getByRole('tab', {name: 'Raportör'}).click();
  await panel(page).getByLabel('Raportöre sorunuz').fill('Kısa bir soru');
  await panel(page).getByLabel('Raportöre sorunuz').press('Enter');
  await expect(panel(page).getByRole('log', {name: 'Raportör ile sohbet'})).toContainText('Sentetik Raportör yanıtı: Kısa bir soru');
  await panel(page).getByRole('button', {name: 'Ajan ekibi panelini kapat'}).click();
  await expect(panel(page)).toHaveCount(0);
});

test('the expanded team gives the conversation 320 px at 712 px height and remembers the graph toggle', async ({page}) => {
  await page.setViewportSize({width: 1480, height: 712});
  await mockAgents(page);
  await login(page);
  await page.goto('/funds/THF');
  await openPanel(page);
  const dialog = panel(page);
  await expect(dialog.getByRole('button', {name: 'Ekibi daralt'})).toHaveAttribute('aria-expanded', 'true');
  await dialog.getByRole('tab', {name: 'Raportör'}).click();
  await expect.poll(async () => (await dialog.getByRole('log', {name: 'Raportör ile sohbet'}).boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(320);
  await expect.poll(async () => {
    const input = await dialog.getByLabel('Raportöre sorunuz').boundingBox(), bounds = await dialog.boundingBox();
    return Boolean(input && bounds && input.y + input.height <= bounds.y + bounds.height);
  }).toBe(true);
  await dialog.getByRole('button', {name: 'Ekibi daralt'}).click();
  await expect(dialog.getByRole('button', {name: 'Ekibi genişlet'})).toHaveAttribute('aria-expanded', 'false');
  await page.reload();
  await openPanel(page);
  await expect(panel(page).getByRole('button', {name: 'Ekibi genişlet'})).toHaveAttribute('aria-expanded', 'false');
});

test('the larger mascot drags without opening, keeps its position and supports keyboard reset', async ({page}) => {
  await page.setViewportSize({width: 1480, height: 712});
  await mockAgents(page);
  await login(page);
  await page.goto('/funds/THF');
  const button = fab(page);
  const initial = await button.boundingBox();
  expect(initial?.width).toBe(96);
  if (!initial) throw new Error('Mascot position unavailable');
  await page.mouse.move(initial.x + initial.width / 2, initial.y + initial.height / 2);
  await page.mouse.down();
  await page.mouse.move(100, 100, {steps: 8});
  await page.mouse.up();
  await expect(panel(page)).toHaveCount(0);
  const moved = await button.boundingBox();
  expect(moved && moved.x < 100 && moved.y < 100).toBe(true);
  await page.reload();
  await expect.poll(async () => Math.round((await button.boundingBox())?.x ?? -1)).toBe(Math.round(moved!.x));
  await button.focus();
  await button.press('ArrowLeft');
  await expect.poll(async () => Math.round((await button.boundingBox())?.x ?? -1)).toBe(Math.max(12, Math.round(moved!.x) - 20));
  await button.press('Home');
  await expect.poll(async () => Math.round((await button.boundingBox())?.x ?? -1)).toBe(Math.round(initial.x));
  await button.press('ArrowLeft');
  await button.press('Enter');
  await expect.poll(async () => {
    const bounds = await panel(page).boundingBox();
    return Boolean(bounds && bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= 1480 && bounds.y + bounds.height <= 712);
  }).toBe(true);
});
