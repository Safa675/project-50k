import {test, expect, type Page} from '@playwright/test';
import {DATED_EXACT, LATER_DATE_EXEMPT, deniedTerms} from '../../src/lib/dated-presentation';
import {FIXTURE_DATES, bundleIdFor, datedFixture, errorFixture, indexFixture} from '../fixtures/dated-research';

// Authored synthetic fixtures only. Every mock is keyed by the full pathname
// including the date, and by the date's own bundle; anything else is recorded
// as unexpected and aborted, so a test cannot pass on a vacuous route.
type Options = {
  indexFailures?: number;
  gate?: Record<string, Promise<void>>;
  mutate?: (path: string, payload: Record<string, unknown>) => unknown;
  fail?: (path: string) => {status: number; body: unknown} | undefined;
};
const MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
const SHORT = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
const EARLY = FIXTURE_DATES[0];
const SECOND = FIXTURE_DATES[1];
const LATE = FIXTURE_DATES[11];

async function mockDated(page: Page, options: Options = {}) {
  const requests: string[] = [];
  const unexpected: string[] = [];
  let indexFailures = options.indexFailures ?? 0;
  await page.route('**/api/research/**', async route => { unexpected.push(route.request().url()); await route.abort(); });
  await page.route('**/api/research-dated/**', async route => {
    const url = new URL(route.request().url());
    const key = url.pathname + url.search;
    requests.push(key);
    const reply = async (status: number, body: unknown) => route.fulfill({status, contentType: 'application/json', headers: {'cache-control': 'no-store'}, body: JSON.stringify(body)});
    if (route.request().method() !== 'GET') { unexpected.push(`${route.request().method()} ${key}`); await route.abort(); return; }
    if (url.pathname === '/api/research-dated/v1/dates' && !url.search) {
      if (indexFailures > 0) { indexFailures--; const failure = errorFixture(503, 'INDEX_UNAVAILABLE', 'Tarih dizini şu anda doğrulanamıyor.'); await reply(failure.status, failure.body); return; }
      await reply(200, indexFixture()); return;
    }
    const match = /^\/api\/research-dated\/v1\/dates\/(\d{4}-\d{2}-\d{2})\/(summary|funds|funds\/([A-Z0-9]{3}))$/.exec(url.pathname);
    const date = match?.[1];
    if (!match || !date || !(FIXTURE_DATES as readonly string[]).includes(date) || url.searchParams.getAll('bundle').join() !== bundleIdFor(date) || [...url.searchParams.keys()].length !== 1) {
      unexpected.push(key); await route.abort(); return;
    }
    const fixture = datedFixture(date);
    let payload: unknown = match[2] === 'summary' ? fixture.summary : match[2] === 'funds' ? fixture.list : fixture.detail(match[3]);
    if (options.gate?.[url.pathname]) await options.gate[url.pathname];
    const failure = options.fail?.(url.pathname);
    if (failure) { await reply(failure.status, failure.body); return; }
    if (payload === null) { const missing = errorFixture(404, 'FUND_NOT_FOUND', 'Bu fon seçili 100 fon içinde bulunmuyor.', date); await reply(missing.status, missing.body); return; }
    if (options.mutate) payload = options.mutate(url.pathname, structuredClone(payload) as Record<string, unknown>);
    await reply(200, payload);
  });
  return {requests, unexpected};
}
const rows = (page: Page) => page.locator('.desktop-funds tbody tr');
const perDate = (requests: string[], date: string) => requests.filter(item => item.includes(`/dates/${date}/`));
async function listReady(page: Page, heading: string) {
  await expect(page.getByRole('heading', {level: 1, name: heading, exact: true})).toBeVisible();
  await expect(rows(page)).toHaveCount(100);
}
/** Rendered main text without the selector's options. */
async function mainText(page: Page) {
  return page.evaluate(() => {
    const main = document.querySelector('main')!.cloneNode(true) as HTMLElement;
    main.querySelectorAll('select').forEach(element => element.remove());
    return main.textContent ?? '';
  });
}
/**
 * The only text exempt from the later-date rule, named here one by one
 * (docs/notes/fund-review-dated-design.md, "Protocol clarification 1"): the survivorship
 * sentence, the snapshot label, the "Neden yalnızca bu tarihler?" text and the fixed-view
 * link sentence. The selector's options are removed by mainText. The guard, the
 * no-crossing sentence and every other exact sentence stay in the checked text.
 */
const LATER_DATE_EXEMPT_SENTENCES = [DATED_EXACT.survivorship, DATED_EXACT.whyDates, DATED_EXACT.fixedViewLink];
const SNAPSHOT_LABEL = new RegExp(`Ad ve kategoriler: \\d{1,2} (?:${MONTHS.join('|')}) \\d{4} anlık görüntüsü\\.`, 'g');
function checkedText(text: string): string {
  let remaining = text.replace(/\s+/g, ' ');
  for (const sentence of LATER_DATE_EXEMPT_SENTENCES) remaining = remaining.split(sentence).join(' ');
  return remaining.replace(SNAPSHOT_LABEL, ' ');
}
/** Dates after `selected` mentioned outside the exempt sentences. */
function laterDates(text: string, selected: string): string[] {
  const remaining = checkedText(text);
  const found: string[] = [];
  const day = (y: string, m: number, d: string) => `${y}-${String(m).padStart(2, '0')}-${d.padStart(2, '0')}`;
  for (const match of remaining.matchAll(/(\d{4}-\d{2}-\d{2})/g)) found.push(match[1]);
  for (const match of remaining.matchAll(new RegExp(`(\\d{1,2})\\s(${[...MONTHS, ...SHORT].join('|')})\\s(\\d{4})`, 'g'))) {
    const month = Math.max(MONTHS.indexOf(match[2]), SHORT.indexOf(match[2])) + 1; found.push(day(match[3], month, match[1]));
  }
  for (const match of remaining.matchAll(new RegExp(`(?<!\\d\\s)(${MONTHS.join('|')})\\s(\\d{4})`, 'g'))) found.push(`${match[2]}-${String(MONTHS.indexOf(match[1]) + 1).padStart(2, '0')}-01`);
  return found.filter(value => value > selected);
}
async function checkText(page: Page, selected: string) {
  const text = await mainText(page);
  expect(deniedTerms(text)).toEqual([]);
  expect(laterDates(text, selected)).toEqual([]);
  expect(text).toContain(DATED_EXACT.guard);
  // The guard is not exempt: it went through the later-date check above.
  expect(checkedText(text)).toContain(DATED_EXACT.guard);
}

test('the laterDates helper detects a later date and exempts only the clarified sentences', () => {
  expect([...LATER_DATE_EXEMPT_SENTENCES].sort()).toEqual([...LATER_DATE_EXEMPT].sort());
  expect(laterDates('31 Ekim 2025 ve 16 Eylül 2026', EARLY)).toEqual(['2026-09-16']);
  expect(laterDates(`${DATED_EXACT.fixedViewLink} ${DATED_EXACT.whyDates} ${DATED_EXACT.survivorship} Ad ve kategoriler: 7 Ekim 2026 anlık görüntüsü.`, EARLY)).toEqual([]);
  for (const key of ['guard', 'noCrossing', 'whyDatesTitle', 'windowEnd', 'notComputed'] as const) expect(checkedText(DATED_EXACT[key]).trim()).toBe(DATED_EXACT[key]);
  expect(laterDates(`${DATED_EXACT.guard} 16 Eylül 2026 ${DATED_EXACT.noCrossing}`, EARLY)).toEqual(['2026-09-16']);
  expect(laterDates('Ad ve kategoriler: 31 Ekim 2025 ve 16 Eylül 2026 anlık görüntüsü.', EARLY)).toEqual(['2026-09-16']);
  expect(laterDates('Ağustos 2026 · 2026-01-30 · 3 Kas 2025', EARLY).sort()).toEqual(['2025-11-03', '2026-01-30', '2026-08-01']);
  expect(laterDates('31 Ekim 2025 · 30 Eki 2025 · Ekim 2025', EARLY)).toEqual([]);
});

test('default date shows its own cutoff, guard, survivorship, snapshot and denominators', async ({page}) => {
  const {requests, unexpected} = await mockDated(page);
  await page.goto('/dates');
  await listReady(page, 'Fonlar · 16 Eylül 2026');
  await expect(page.locator('.cutoff')).toContainText('16 Eylül 2026 · 23:59 İstanbul');
  await expect(page.locator('.cutoff')).toContainText(DATED_EXACT.windowEnd);
  for (const sentence of [DATED_EXACT.guard, DATED_EXACT.survivorship, 'Ad ve kategoriler: 7 Ekim 2026 anlık görüntüsü.', DATED_EXACT.notComputed]) await expect(page.getByText(sentence, {exact: false}).first()).toBeVisible();
  await expect(page.getByRole('link', {name: DATED_EXACT.fixedViewLink, exact: true})).toHaveAttribute('href', '/');
  await expect(page.locator('.stats')).toContainText('2 / 100 fon');
  await expect(page.locator('.stats')).toContainText('96 / 100 fon');
  await expect(page.getByText('Seçilen tarihte veya öncesinde fiyat kaydı olmayan fon: 0 / 100 fon', {exact: false})).toBeVisible();
  await expect(rows(page).first()).toHaveAttribute('data-code', 'X11');
  await expect(page).toHaveTitle(/16 Eylül 2026/);
  await expect(page.getByLabel('İnceleme tarihi', {exact: true})).toHaveValue(LATE);
  expect(requests.sort()).toEqual(['/api/research-dated/v1/dates', `/api/research-dated/v1/dates/${LATE}/funds?bundle=${bundleIdFor(LATE)}`, `/api/research-dated/v1/dates/${LATE}/summary?bundle=${bundleIdFor(LATE)}`].sort());
  await checkText(page, LATE);
  expect(unexpected).toEqual([]);
});

test('early date keeps unpriced, stale and unavailable funds distinct and in registered order', async ({page}) => {
  const {unexpected} = await mockDated(page);
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await expect(page.locator('.cutoff')).toContainText('31 Ekim 2025 · 23:59 İstanbul');
  await expect(page.locator('.cutoff')).not.toContainText(DATED_EXACT.windowEnd);
  const codes = await rows(page).evaluateAll(elements => elements.map(element => element.getAttribute('data-code')));
  expect(codes.slice(0, 7)).toEqual(['X00', 'X12', 'X40', 'X50', 'X97', 'X98', 'X99']);
  await expect(rows(page).filter({hasText: 'Bu tarihte fiyat kaydı yok'})).toHaveCount(3);
  await expect(rows(page).filter({hasText: 'Güncel gözlem eksik'})).toHaveCount(1);
  await expect(page.getByText('Seçilen tarihte veya öncesinde fiyat kaydı olmayan fon: 3 / 100 fon', {exact: false})).toBeVisible();
  const noCrossing = rows(page).filter({hasText: 'Eşik aşımı yok'});
  await expect(noCrossing).toHaveCount(93);
  expect(await noCrossing.first().locator('.comment-cell').textContent()).toContain(DATED_EXACT.noCrossing);
  expect((await noCrossing.first().locator('.comment-cell').textContent())!.split(DATED_EXACT.noCrossing)).toHaveLength(2);
  await page.getByLabel('Fon ara', {exact: true}).fill('x97');
  await expect(rows(page)).toHaveCount(1);
  await expect(page.getByText('1 / 100 fon gösteriliyor', {exact: true})).toBeVisible();
  await page.getByLabel('Fon ara', {exact: true}).fill('');
  await checkText(page, EARLY);
  expect(unexpected).toEqual([]);
});

test('changing the select does not navigate; submit does, then focuses the dated h1 and announces it', async ({page}) => {
  const {requests, unexpected} = await mockDated(page);
  await page.goto('/dates');
  await listReady(page, 'Fonlar · 16 Eylül 2026');
  const select = page.getByLabel('İnceleme tarihi', {exact: true});
  await select.selectOption(SECOND);
  await page.waitForTimeout(300);
  await expect(page).toHaveURL(/\/dates$/);
  expect(perDate(requests, SECOND)).toEqual([]);
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Fonlar · 16 Eylül 2026');
  await page.getByRole('button', {name: 'Tarihi göster', exact: true}).click();
  await expect(page).toHaveURL(new RegExp(`/dates\\?date=${SECOND}$`));
  await listReady(page, 'Fonlar · 28 Kasım 2025');
  await expect(page.getByRole('heading', {level: 1})).toBeFocused();
  await expect(page.locator('[data-dated-live]')).toHaveText('28 Kasım 2025 tarihli görünüm yüklendi.');
  await expect(page).toHaveTitle(/28 Kasım 2025/);
  await expect(rows(page).first()).toHaveAttribute('data-code', 'X01');
  await checkText(page, SECOND);
  expect(unexpected).toEqual([]);
});

test('submitting a date that ends in an error, mismatch or unregistered state focuses that h1 and announces it through the alert', async ({page}) => {
  const [THIRD, FOURTH] = [FIXTURE_DATES[2], FIXTURE_DATES[3]];
  const {requests, unexpected} = await mockDated(page, {fail: path =>
    path === `/api/research-dated/v1/dates/${SECOND}/summary` ? errorFixture(503, 'BUNDLE_UNAVAILABLE', 'Araştırma paketi şu anda doğrulanamıyor.', SECOND)
      : path === `/api/research-dated/v1/dates/${THIRD}/funds` ? errorFixture(409, 'CONTEXT_MISMATCH', 'Paket bu tarih için kayıtlı paketle uyuşmuyor.', THIRD)
      : path === `/api/research-dated/v1/dates/${FOURTH}/summary` ? errorFixture(404, 'DATE_NOT_REGISTERED', 'Bu tarih için kayıtlı bir arşiv kesiti yok.', FOURTH)
      : undefined});
  const live = page.locator('[data-dated-live]');
  const alert = page.locator('.error-panel[role="alert"]');
  const show = async (date: string) => {
    await page.getByLabel('İnceleme tarihi', {exact: true}).selectOption(date);
    await page.getByRole('button', {name: 'Tarihi göster', exact: true}).click();
    await expect(page).toHaveURL(new RegExp(`/dates\\?date=${date}$`));
  };
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await show(LATE);
  await listReady(page, 'Fonlar · 16 Eylül 2026');
  await expect(live).toHaveText('16 Eylül 2026 tarihli görünüm yüklendi.');
  for (const [date, title, message] of [
    [SECOND, 'Araştırma verisi alınamadı', 'Araştırma paketi şu anda doğrulanamıyor.'],
    [THIRD, 'Bağlantı kayıtlı paketle uyuşmuyor', 'Paket bu tarih için kayıtlı paketle uyuşmuyor.'],
    [FOURTH, 'Bu tarih kayıtlı değil', 'Bu tarih için kayıtlı bir arşiv kesiti yok.'],
  ] as const) {
    await show(date);
    const heading = page.getByRole('heading', {level: 1, name: title, exact: true});
    await expect(heading).toBeVisible();
    await expect(heading).toBeFocused();
    await expect(heading).toHaveAttribute('tabindex', '-1');
    await expect(alert).toContainText(message);
    await expect(alert).toContainText('Bu durumda fon sonucu gösterilmiyor.');
    // No stale "loaded" announcement survives into an error state.
    await expect(live).not.toContainText('yüklendi');
    await expect(rows(page)).toHaveCount(0);
    await expect(page.getByLabel('İnceleme tarihi', {exact: true})).toHaveValue(date);
    await checkText(page, date);
  }
  await expect(page.getByRole('button', {name: 'Tekrar dene', exact: true})).toHaveCount(0);
  await show(EARLY);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await expect(page.getByRole('heading', {level: 1})).toBeFocused();
  await expect(live).toHaveText('31 Ekim 2025 tarihli görünüm yüklendi.');
  expect(perDate(requests, FOURTH).length).toBeGreaterThan(0);
  expect(unexpected).toEqual([]);
});

test('a detail 404 is "not found" only for FUND_NOT_FOUND; DATE_NOT_REGISTERED shows the unregistered-date state', async ({page}) => {
  const {unexpected} = await mockDated(page, {fail: path =>
    path === `/api/research-dated/v1/dates/${EARLY}/funds/X05` ? errorFixture(404, 'DATE_NOT_REGISTERED', 'Bu tarih için kayıtlı bir arşiv kesiti yok.', EARLY)
      : path === `/api/research-dated/v1/dates/${EARLY}/funds/X06` ? errorFixture(404, 'NOT_FOUND', 'Bu tarih görünümü adresi bulunmuyor.')
      : undefined});
  await page.goto(`/dates/funds/X05?date=${EARLY}&bundle=${bundleIdFor(EARLY)}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Bu tarih kayıtlı değil', exact: true})).toBeVisible();
  await expect(page.locator('.error-panel[role="alert"]')).toContainText('Bu tarih için kayıtlı bir arşiv kesiti yok.');
  await expect(page.getByRole('heading', {level: 1, name: 'Fon bulunamadı', exact: true})).toHaveCount(0);
  await checkText(page, EARLY);
  await page.goto(`/dates/funds/X06?date=${EARLY}&bundle=${bundleIdFor(EARLY)}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Araştırma verisi alınamadı', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Tekrar dene', exact: true})).toBeVisible();
  await page.goto(`/dates/funds/QQQ?date=${EARLY}&bundle=${bundleIdFor(EARLY)}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Fon bulunamadı', exact: true})).toBeVisible();
  await expect(page.locator('.error-panel[role="alert"]')).toContainText('Bu fon seçili 100 fon içinde bulunmuyor.');
  expect(unexpected).toEqual([]);
});

test('a list 404 DATE_NOT_REGISTERED from the API shows the unregistered-date state, not a generic failure', async ({page}) => {
  const {unexpected} = await mockDated(page, {fail: path => path === `/api/research-dated/v1/dates/${SECOND}/funds`
    ? errorFixture(404, 'DATE_NOT_REGISTERED', 'Bu tarih için kayıtlı bir arşiv kesiti yok.', SECOND) : undefined});
  await page.goto(`/dates?date=${SECOND}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Bu tarih kayıtlı değil', exact: true})).toBeVisible();
  await expect(page.locator('.error-panel[role="alert"]')).toContainText('Bu tarih için kayıtlı bir arşiv kesiti yok.');
  await expect(page.getByRole('button', {name: 'Tekrar dene', exact: true})).toHaveCount(0);
  await expect(rows(page)).toHaveCount(0);
  await checkText(page, SECOND);
  expect(unexpected).toEqual([]);
});

test('keyboard reaches the select and submit; the window-end option is labelled', async ({page}) => {
  const {unexpected} = await mockDated(page);
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  const select = page.getByLabel('İnceleme tarihi', {exact: true});
  await expect(select.locator('option')).toHaveCount(12);
  await expect(select.locator(`option[value="${LATE}"]`)).toHaveText(`16 Eylül 2026 · ${DATED_EXACT.windowEnd}`);
  await select.focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', {name: 'Tarihi göster', exact: true})).toBeFocused();
  await page.getByText(DATED_EXACT.whyDatesTitle, {exact: true}).click();
  await expect(page.getByText(DATED_EXACT.whyDates, {exact: true})).toBeVisible();
  const sizes = await page.evaluate(() => [...document.querySelectorAll('.date-selector select, .date-selector button')].map(element => element.getBoundingClientRect().height));
  expect(sizes.every(height => height >= 44)).toBe(true);
  expect(unexpected).toEqual([]);
});

test('a slow next date never shows the previous date rows; back and forward restore each date', async ({page}) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const {unexpected} = await mockDated(page, {gate: {[`/api/research-dated/v1/dates/${SECOND}/funds`]: gate}});
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await page.getByLabel('İnceleme tarihi', {exact: true}).selectOption(SECOND);
  await page.getByRole('button', {name: 'Tarihi göster', exact: true}).click();
  await expect(page).toHaveURL(new RegExp(`date=${SECOND}`));
  await expect(page.getByRole('heading', {level: 1, name: 'Araştırma paketi yükleniyor…'})).toBeVisible();
  await expect(rows(page)).toHaveCount(0);
  await expect(page.locator(`[data-dated-date="${EARLY}"]`)).toHaveCount(0);
  await expect(page.getByText('31 Ekim 2025 · 23:59 İstanbul')).toHaveCount(0);
  release();
  await listReady(page, 'Fonlar · 28 Kasım 2025');
  await expect(page.locator('[data-dated-date]')).toHaveAttribute('data-dated-bundle', bundleIdFor(SECOND));
  await page.goBack();
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await expect(rows(page).first()).toHaveAttribute('data-code', 'X00');
  await expect(page.locator('[data-dated-date]')).toHaveAttribute('data-dated-bundle', bundleIdFor(EARLY));
  await page.goForward();
  await listReady(page, 'Fonlar · 28 Kasım 2025');
  await expect(rows(page).first()).toHaveAttribute('data-code', 'X01');
  expect(unexpected).toEqual([]);
});

test('invalid and unregistered dates are refused before any per-date request', async ({page}) => {
  const {requests, unexpected} = await mockDated(page);
  for (const [query, title] of [['date=2026-02-30', 'Tarih geçersiz'], ['date=2025-10-05', 'Tarih geçersiz'], ['date=2026-9-16', 'Tarih geçersiz'],
    [`date=${EARLY}&date=${SECOND}`, 'Tarih geçersiz'], ['date=2026-09-15', 'Bu tarih kayıtlı değil'], ['date=2025-10-30', 'Bu tarih kayıtlı değil']] as const) {
    await page.goto(`/dates?${query}`);
    await expect(page.getByRole('heading', {level: 1, name: title, exact: true})).toBeVisible();
    await expect(page.locator('.error-panel[role="alert"]')).toContainText('Bu durumda fon sonucu gösterilmiyor.');
    await expect(page.getByLabel('İnceleme tarihi', {exact: true})).toHaveValue(LATE);
    await expect(rows(page)).toHaveCount(0);
    await checkText(page, '2025-10-06');
  }
  expect(requests.filter(item => item !== '/api/research-dated/v1/dates')).toEqual([]);
  expect(unexpected).toEqual([]);
});

test('a link bundle that differs from the index, a 409 or a mismatched response shows the mismatch state', async ({page}) => {
  const {requests, unexpected} = await mockDated(page, {
    fail: path => path === `/api/research-dated/v1/dates/${SECOND}/summary` ? errorFixture(409, 'CONTEXT_MISMATCH', 'Paket bu tarih için kayıtlı paketle uyuşmuyor.', SECOND) : undefined,
    mutate: (path, payload) => path === `/api/research-dated/v1/dates/${FIXTURE_DATES[2]}/funds` ? {...payload, immutable_bundle_id: bundleIdFor(LATE)} : payload,
  });
  await page.goto(`/dates?date=${EARLY}&bundle=${bundleIdFor(LATE)}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Bağlantı kayıtlı paketle uyuşmuyor', exact: true})).toBeVisible();
  expect(perDate(requests, EARLY)).toEqual([]);
  await expect(page.getByRole('link', {name: 'Kayıtlı paketle aç', exact: true})).toHaveAttribute('href', `/dates?date=${EARLY}`);
  await checkText(page, EARLY);
  for (const date of [SECOND, FIXTURE_DATES[2]]) {
    await page.goto(`/dates?date=${date}`);
    await expect(page.getByRole('heading', {level: 1, name: 'Bağlantı kayıtlı paketle uyuşmuyor', exact: true})).toBeVisible();
    await expect(rows(page)).toHaveCount(0);
  }
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  expect(unexpected).toEqual([]);
});

test('index and bundle failures show no fabricated results and recover only by explicit retry', async ({page}) => {
  let corrupt = true;
  const {unexpected} = await mockDated(page, {indexFailures: 1, mutate: (path, payload) => corrupt && path.endsWith('/funds') ? {...payload, funds: (payload.funds as unknown[]).slice(1)} : payload});
  await page.goto(`/dates?date=${EARLY}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Tarih dizini alınamadı', exact: true})).toBeVisible();
  await expect(page.locator('.error-panel[role="alert"]')).toContainText('Tarih dizini şu anda doğrulanamıyor.');
  await expect(page.getByLabel('İnceleme tarihi', {exact: true})).toHaveCount(0);
  await checkText(page, EARLY);
  await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1, name: 'Araştırma verisi alınamadı', exact: true})).toBeVisible();
  await expect(page.locator('.error-panel[role="alert"]')).toContainText('Araştırma yanıtı beklenen veri sözleşmesine uymuyor.');
  await expect(rows(page)).toHaveCount(0);
  await checkText(page, EARLY);
  corrupt = false;
  await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click();
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  expect(unexpected).toEqual([]);
});

test('detail is D1-only with a read-only date, no PDF or KAP link, and returns to the same date and bundle', async ({page}) => {
  const {unexpected} = await mockDated(page);
  await page.goto(`/dates?date=${EARLY}`);
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await rows(page).first().getByRole('link', {name: 'X00 ↗', exact: true}).click();
  await expect(page).toHaveURL(new RegExp(`/dates/funds/X00\\?date=${EARLY}&bundle=${bundleIdFor(EARLY)}$`));
  await expect(page.getByRole('heading', {level: 1})).toContainText('X00');
  await expect(page.getByRole('heading', {name: 'Benzer fonlara göre getiri farkı · D1', exact: true})).toBeVisible();
  await expect(page.locator('.cutoff')).toContainText('31 Ekim 2025 · 23:59 İstanbul');
  await expect(page.getByText('Bu sayfada tarih değiştirilemez', {exact: false})).toBeVisible();
  await expect(page.getByRole('combobox')).toHaveCount(0);
  await expect(page.getByRole('button', {name: /PDF/})).toHaveCount(0);
  await expect(page.locator('a[href*="kap.org.tr"]')).toHaveCount(0);
  await expect(page.getByText('Tahmini para hareketi')).toHaveCount(0);
  await expect(page.getByText(DATED_EXACT.notComputed, {exact: true})).toBeVisible();
  await expect(page.getByText('Günlük fon fiyatları', {exact: false}).first()).toBeVisible();
  await checkText(page, EARLY);
  await page.getByRole('link', {name: '← Fon listesine dön', exact: true}).click();
  await expect(page).toHaveURL(new RegExp(`/dates\\?date=${EARLY}&bundle=${bundleIdFor(EARLY)}$`));
  await listReady(page, 'Fonlar · 31 Ekim 2025');
  await page.goto(`/dates/funds/X97?date=${EARLY}&bundle=${bundleIdFor(EARLY)}`);
  await expect(page.getByText('Seçilen tarihte veya öncesinde bu fonun pozitif fiyat kaydı yok.', {exact: true})).toBeVisible();
  await expect(page.getByText('Grafik için yeterli veri yok', {exact: true})).toBeVisible();
  await checkText(page, EARLY);
  await page.goto(`/dates/funds/QQQ?date=${EARLY}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Fon bulunamadı', exact: true})).toBeVisible();
  await page.goto(`/dates/funds/X05?date=${EARLY}&bundle=${bundleIdFor(SECOND)}`);
  await expect(page.getByRole('heading', {level: 1, name: 'Bağlantı kayıtlı paketle uyuşmuyor', exact: true})).toBeVisible();
  expect(unexpected).toEqual([]);
});

for (const width of [390, 768, 1440]) {
  test(`list and detail have no horizontal page overflow at ${width}px`, async ({page}) => {
    await page.setViewportSize({width, height: 900});
    const {unexpected} = await mockDated(page);
    await page.goto(`/dates?date=${EARLY}`);
    await listReady(page, 'Fonlar · 31 Ekim 2025');
    if (width === 390) { await expect(page.locator('.mobile-funds')).toBeVisible(); await expect(page.locator('.mobile-fund')).toHaveCount(100); }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.goto(`/dates/funds/X00?date=${EARLY}&bundle=${bundleIdFor(EARLY)}`);
    await expect(page.getByRole('heading', {name: 'Benzer fonlara göre getiri farkı · D1', exact: true})).toBeVisible();
    await expect.poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.goto('/dates?date=2026-02-30');
    await expect(page.getByRole('heading', {level: 1, name: 'Tarih geçersiz', exact: true})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(unexpected).toEqual([]);
  });
}
