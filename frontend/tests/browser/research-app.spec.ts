import {test, expect, type Page} from '@playwright/test';
import {ListResponseSchema, SummaryResponseSchema, DetailResponseSchema} from '../../src/lib/research-contract';
import {BUNDLE_ID, CUTOFF_AT, METADATA, SYNTHETIC_PDF, researchFixture} from '../fixtures/research';

// These requests never reach the private archive. Fixtures are independently
// authored and browser artifacts are disabled in playwright.config.ts.
type MockState = {
  failure?: 'missing' | 'corrupt';
  networkFailure?: boolean;
  mutate?: (path: string, payload: unknown) => unknown;
  pdf?: 'wrong-bundle' | 'bad-bytes' | 'missing';
  pdfGate?: Promise<void>;
};
async function mockResearch(page: Page, state: MockState = {}) {
  const fixture = researchFixture();
  const requests: string[] = [];
  await page.route('**/api/research/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    requests.push(path);
    if (state.networkFailure) { await route.abort('failed'); return; }
    if (state.failure) {
      await route.fulfill({status: 503, contentType: 'application/json', headers: {'cache-control': 'no-store'},
        body: JSON.stringify({...METADATA, immutable_bundle_id: null, error: {
          code: state.failure === 'missing' ? 'BUNDLE_UNAVAILABLE' : 'BUNDLE_INVALID',
          message_tr: state.failure === 'missing' ? 'Seçili araştırma paketi bulunamadı.' : 'Araştırma paketinin bütünlüğü doğrulanamadı.',
        }})});
      return;
    }
    if (path.startsWith('/api/research/v1/sources/')) {
      if (state.pdfGate) await state.pdfGate;
      const known = fixture.detail('S00').sources.find(source => source.pdf_available)!;
      if (path !== `/api/research/v1/sources/${known.source_id}` || state.pdf === 'missing') {
        await route.fulfill({status: 404, contentType: 'application/json', headers: {'cache-control': 'no-store'}, body: '{}'});
        return;
      }
      await route.fulfill({status: 200, body: state.pdf === 'bad-bytes' ? Buffer.from('%PDF-corrupt-authored-test') : SYNTHETIC_PDF,
        headers: {'content-type': 'application/pdf', 'cache-control': 'no-store',
          'x-research-bundle-id': state.pdf === 'wrong-bundle' ? 'b'.repeat(64) : BUNDLE_ID,
          'x-research-cutoff-at': CUTOFF_AT, 'x-research-origin': 'HISTORICAL_REPLAY',
          'x-research-analysis-mode': 'EXPLORATORY_ARCHIVE', 'x-research-point-in-time-verified': 'false',
          'x-research-rights-status': 'UNKNOWN'}});
      return;
    }
    let payload: unknown;
    if (path === '/api/research/v1/funds') payload = fixture.list;
    else if (path === '/api/research/v1/summary') payload = fixture.summary;
    else if (path.startsWith('/api/research/v1/funds/')) {
      const detail = fixture.detail(path.slice('/api/research/v1/funds/'.length));
      if (!detail.fund) {
        await route.fulfill({status: 404, contentType: 'application/json', headers: {'cache-control': 'no-store'},
          body: JSON.stringify({...METADATA, error: {code: 'FUND_NOT_FOUND', message_tr: 'Bu fon seçili 100 fon içinde bulunmuyor.'}})});
        return;
      }
      payload = detail;
    } else throw new Error(`Unexpected research route: ${path}`);
    if (state.mutate) payload = state.mutate(path, structuredClone(payload));
    await route.fulfill({status: 200, contentType: 'application/json', headers: {'cache-control': 'no-store'}, body: JSON.stringify(payload)});
  });
  return {fixture, requests};
}
const rows = (page: Page) => page.locator('.desktop-funds tbody tr');
const rowFor = (page: Page, code: string) => rows(page).filter({has: page.getByRole('link', {name: `${code} ↗`, exact: true})});
async function listReady(page: Page, count = 100) {
  await expect(page.getByRole('heading', {name: 'Fonların verileri ne söylüyor?', exact: true})).toBeVisible();
  await expect(page.getByText(`${count} / 100 fon gösteriliyor`, {exact: true})).toBeVisible();
  await expect(rows(page)).toHaveCount(count);
}
async function detailReady(page: Page, code: string) {
  await expect(page.getByRole('heading', {level: 1})).toContainText(code);
  await expect(page.getByRole('heading', {name: 'İki ayrı araştırma hesabı', exact: true})).toBeVisible();
}
async function renderedPdfPage(page: Page, number: number) {
  const dialog = page.getByRole('dialog', {name: 'Orijinal kaynak PDF', exact: true});
  const canvas = dialog.locator(`canvas[aria-label="PDF sayfası ${number}"]`);
  await expect(canvas).toBeVisible();
  // Inspect authored pixels in memory; no screenshot or real archive is used.
  await expect.poll(async () => canvas.evaluate(element => {
    const target = element as HTMLCanvasElement;
    const context = target.getContext('2d');
    if (!context || !target.width || !target.height) return 0;
    const data = context.getImageData(0, 0, target.width, target.height).data;
    let ink = 0;
    for (let index = 0; index < data.length; index += 16) {
      if (data[index + 3] > 0 && Math.min(data[index], data[index + 1], data[index + 2]) < 100) ink++;
    }
    return ink;
  })).toBeGreaterThan(20);
  await expect(dialog.getByText(`Sayfa ${number} / 2`, {exact: true})).toBeVisible();
}
async function pdfTextVisible(page: Page, text: string) {
  const dialog = page.getByRole('dialog', {name: 'Orijinal kaynak PDF', exact: true});
  const summary = dialog.getByText('Sayfanın metnini göster', {exact: true});
  await expect(summary).toBeVisible();
  if (!await summary.locator('..').evaluate(element => (element as HTMLDetailsElement).open)) await summary.click();
  await expect(dialog.getByText(text, {exact: true})).toBeVisible();
}

test('authored 100 records and sources satisfy the strict runtime contract', () => {
  const fixture = researchFixture();
  expect(ListResponseSchema.safeParse(fixture.list).success).toBe(true);
  expect(SummaryResponseSchema.safeParse(fixture.summary).success).toBe(true);
  for (const fund of fixture.list.funds) expect(DetailResponseSchema.safeParse(fixture.detail(fund.code)).success).toBe(true);
  expect(new Set(fixture.list.funds.map(fund => fund.code)).size).toBe(100);
  expect(fixture.summary.summary.two_findings + fixture.summary.summary.one_finding + fixture.summary.summary.unassessable_no_findings + fixture.summary.summary.no_findings).toBe(100);
});

test('real list route retains all 100 funds, independent coverage counts and missing values', async ({page}) => {
  const {requests} = await mockResearch(page);
  await page.goto('/'); await listReady(page);
  for (const [label, count] of [['Listelenen fon', 100], ['İki hesap mevcut', 97], ['Eksik değerlendirme', 2], ['Değerlendirilemiyor', 1]] as const) {
    await expect(page.locator('.stats').getByText(label, {exact: true}).locator('..')).toContainText(String(count));
  }
  await expect(page.getByText('Güncel D1 hesabı: 98 / 100 fon · Tahmini para hareketi hesabı: 98 / 100 fon · Son gözlemi eski D1: 1 / 100 fon')).toBeVisible();
  await expect(rowFor(page, 'S04').locator('.metric-value')).toHaveText(['—', '—']);
  await expect(rowFor(page, 'S03')).toContainText('Güncel gözlem eksik');
  await expect(rowFor(page, 'S02')).toContainText('Eksik değerlendirme');
  await expect(rowFor(page, 'S01')).toContainText('Çıkış tahmini');
  await expect(rowFor(page, 'IAA')).toContainText('güvenlik sonucu değildir');
  expect(requests).toContain('/api/research/v1/funds'); expect(requests).toContain('/api/research/v1/summary');
});

test('ASCII fund codes, Turkish names, category and finding filters keep correct denominators', async ({page}) => {
  await mockResearch(page); await page.goto('/'); await listReady(page);
  const search = page.getByLabel('Fon ara', {exact: true});
  await search.fill('iaa'); await listReady(page, 1); await expect(rowFor(page, 'IAA')).toBeVisible();
  await search.fill('çığ'); await listReady(page, 1); await expect(rowFor(page, 'S00')).toBeVisible();
  await search.fill('s00'); await listReady(page, 1);
  await search.fill(''); await page.getByLabel('Kategori', {exact: true}).selectOption('Örnek Hisse'); await listReady(page, 50);
  await page.getByLabel('Kategori', {exact: true}).selectOption('Örnek Değişken'); await listReady(page, 50);
  await page.getByLabel('Kategori', {exact: true}).selectOption('');
  for (const [filter, count] of [['two', 1], ['one', 2], ['unavailable', 3], ['none', 95]] as const) {
    await page.getByLabel('Bulgu', {exact: true}).selectOption(filter); await listReady(page, count);
  }
  await page.getByLabel('Bulgu', {exact: true}).selectOption('all');
  await search.fill('not a known synthetic fund');
  await expect(page.getByText('Aramanızla eşleşen fon yok', {exact: true})).toBeVisible();
  await expect(page.getByText('0 / 100 fon gösteriliyor', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Filtreleri temizle', exact: true}).first().click(); await listReady(page);
});

test('rapid filter edits keep the latest local choices without stale response overwrites', async ({page}) => {
  await mockResearch(page); await page.goto('/'); await listReady(page);
  const category = page.getByLabel('Kategori', {exact: true});
  await category.selectOption('Örnek Hisse');
  await category.selectOption('Örnek Değişken');
  await category.selectOption('');
  await page.getByLabel('Bulgu', {exact: true}).selectOption('two'); await listReady(page, 1);
  await expect(category).toHaveValue(''); await expect(rowFor(page, 'S00')).toBeVisible();
  await expect(page).toHaveURL(url => !url.searchParams.has('category') && url.searchParams.get('finding') === 'two');
  await page.getByLabel('Bulgu', {exact: true}).selectOption('all');
  const search = page.getByLabel('Fon ara', {exact: true});
  await search.fill('s00'); await search.fill('iaa'); await search.fill('çığ');
  await listReady(page, 1); await expect(search).toHaveValue('çığ'); await expect(rowFor(page, 'S00')).toBeVisible();
  await expect(page).toHaveURL(url => url.searchParams.get('q') === 'çığ' && !url.searchParams.has('finding'));
});

test('detail and back navigation preserve all filters and the immutable bundle', async ({page}) => {
  await mockResearch(page); await page.goto('/'); await listReady(page);
  await page.getByLabel('Fon ara', {exact: true}).fill('s00');
  await page.getByLabel('Kategori', {exact: true}).selectOption('Örnek Hisse');
  await page.getByLabel('Bulgu', {exact: true}).selectOption('two'); await listReady(page, 1);
  await rowFor(page, 'S00').getByRole('link', {name: 'S00 ↗', exact: true}).click(); await detailReady(page, 'S00');
  let url = new URL(page.url()); expect(url.pathname).toBe('/funds/S00'); expect(url.searchParams.get('bundle')).toBe(BUNDLE_ID);
  await page.getByRole('link', {name: 'Fon listesine dön'}).click(); await listReady(page, 1);
  await expect(page.getByLabel('Fon ara', {exact: true})).toHaveValue('s00');
  await expect(page.getByLabel('Kategori', {exact: true})).toHaveValue('Örnek Hisse');
  await expect(page.getByLabel('Bulgu', {exact: true})).toHaveValue('two');
  url = new URL(page.url()); expect(url.searchParams.get('bundle')).toBe(BUNDLE_ID);
});

test('duplicate query parameters are bounded and browser back/forward restores selected filters', async ({page}) => {
  await mockResearch(page);
  await page.goto('/?q=S00&q=S01&category=bad&category=worse&finding=two&finding=one');
  await listReady(page);
  await expect(page.getByLabel('Fon ara', {exact: true})).toHaveValue('');
  await expect(page.getByLabel('Kategori', {exact: true})).toHaveValue('');
  await expect(page.getByLabel('Bulgu', {exact: true})).toHaveValue('all');
  const first = `/?q=s00&category=${encodeURIComponent('Örnek Hisse')}&finding=two&bundle=${BUNDLE_ID}`;
  await page.goto(first); await listReady(page, 1);
  await rowFor(page, 'S00').getByRole('link', {name: 'S00 ↗', exact: true}).click(); await detailReady(page, 'S00');
  await page.getByRole('link', {name: 'Fon listesine dön'}).click(); await listReady(page, 1);
  await page.getByLabel('Fon ara', {exact: true}).fill('s01');
  await expect(page).toHaveURL(url => url.searchParams.get('q') === 's01');
  await page.getByLabel('Kategori', {exact: true}).selectOption('Örnek Değişken');
  await expect(page).toHaveURL(url => url.searchParams.get('q') === 's01' && url.searchParams.get('category') === 'Örnek Değişken');
  await page.getByLabel('Bulgu', {exact: true}).selectOption('one'); await listReady(page, 1);
  await expect(page).toHaveURL(url => url.searchParams.get('q') === 's01' && url.searchParams.get('category') === 'Örnek Değişken' && url.searchParams.get('finding') === 'one');
  await expect(page.getByLabel('Fon ara', {exact: true})).toHaveValue('s01');
  await page.goBack(); await detailReady(page, 'S00');
  await page.goBack(); await listReady(page, 1);
  await expect(page.getByLabel('Fon ara', {exact: true})).toHaveValue('s00');
  await expect(page.getByLabel('Kategori', {exact: true})).toHaveValue('Örnek Hisse');
  await expect(page.getByLabel('Bulgu', {exact: true})).toHaveValue('two');
  await page.goForward(); await detailReady(page, 'S00');
  await page.goForward(); await listReady(page, 1);
  await expect(page.getByLabel('Fon ara', {exact: true})).toHaveValue('s01');
  await expect(page.getByLabel('Kategori', {exact: true})).toHaveValue('Örnek Değişken');
  await expect(page.getByLabel('Bulgu', {exact: true})).toHaveValue('one');
});

for (const failure of ['missing', 'corrupt'] as const) {
  test(`${failure} bundle refuses findings and recovers only after an explicit retry`, async ({page}) => {
    const state: MockState = {failure}; await mockResearch(page, state); await page.goto('/');
    await expect(page.locator('main .error-panel[role="alert"]')).toContainText(failure === 'missing' ? 'paketi bulunamadı' : 'bütünlüğü doğrulanamadı');
    await expect(rows(page)).toHaveCount(0);
    state.failure = undefined; await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click(); await listReady(page);
  });
}

test('unreachable API produces a bounded error and no fabricated results', async ({page}) => {
  const state: MockState = {networkFailure: true}; await mockResearch(page, state); await page.goto('/');
  await expect(page.locator('main .error-panel[role="alert"]')).toContainText('Yerel araştırma API’sine ulaşılamıyor.'); await expect(rows(page)).toHaveCount(0);
  state.networkFailure = false; await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click(); await listReady(page);
});

test('corrupt runtime fields and mismatched bundle responses never render list findings', async ({page}) => {
  const state: MockState = {mutate: (path, payload) => {
    if (path.endsWith('/funds')) {const list = payload as ReturnType<typeof researchFixture>['list']; list.funds[0].d1.statistic = 'NaN';}
    return payload;
  }};
  await mockResearch(page, state); await page.goto('/');
  await expect(page.locator('main .error-panel[role="alert"]')).toContainText('beklenen veri sözleşmesine uymuyor'); await expect(rows(page)).toHaveCount(0);
  state.mutate = (path, payload) => path.endsWith('/summary') ? {...payload as object, immutable_bundle_id: 'b'.repeat(64)} : payload;
  await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click();
  await expect(page.locator('main .error-panel[role="alert"]')).toContainText('yükleme sırasında değişti'); await expect(rows(page)).toHaveCount(0);
  state.mutate = (path, payload) => {
    if (path.endsWith('/summary')) {const summary = payload as ReturnType<typeof researchFixture>['summary']; summary.summary.no_findings--; summary.summary.unassessable_no_findings++;}
    return payload;
  };
  await page.getByRole('button', {name: 'Tekrar dene', exact: true}).click();
  await expect(page.locator('main .error-panel[role="alert"]')).toContainText('Özet sayıları fon listesiyle uyuşmuyor'); await expect(rows(page)).toHaveCount(0);
});

test('unknown fund is explicit; selected-code and expected-bundle mismatches are rejected', async ({page}) => {
  const fixture = researchFixture(); const state: MockState = {};
  await mockResearch(page, state); await page.goto('/funds/ZZZ');
  await expect(page.getByRole('heading', {name: 'Fon bulunamadı', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Tekrar dene', exact: true})).toHaveCount(0);
  state.mutate = (path, payload) => path.endsWith('/funds/S00') ? fixture.detail('S01') : payload;
  await page.goto('/funds/S00'); await expect(page.locator('main .error-panel[role="alert"]')).toContainText('seçilen fonla uyuşmuyor');
  await expect(page.getByRole('heading', {name: 'İki ayrı araştırma hesabı', exact: true})).toHaveCount(0);
  state.mutate = (path, payload) => {
    if (path.endsWith('/funds/S00')) (payload as ReturnType<typeof fixture.detail>).sources.pop();
    return payload;
  };
  await page.goto('/funds/S00'); await expect(page.locator('main .error-panel[role="alert"]')).toContainText('kaynak kayıtları araştırma paketiyle uyuşmuyor');
  state.mutate = (path, payload) => {
    if (path.endsWith('/funds/S00')) {
      const source = (payload as ReturnType<typeof fixture.detail>).sources.find(item => item.pdf_available)!;
      source.disclosure_url = 'https://example.invalid/arbitrary-source';
    }
    return payload;
  };
  await page.goto('/funds/S00'); await expect(page.locator('main .error-panel[role="alert"]')).toContainText('beklenen veri sözleşmesine uymuyor');
  await expect(page.locator('a[href="https://example.invalid/arbitrary-source"]')).toHaveCount(0);
  state.mutate = undefined;
  await page.goto(`/funds/S00?bundle=${'b'.repeat(64)}`); await expect(page.locator('main .error-panel[role="alert"]')).toContainText('Sonuçlar birleştirilemez');
  await page.goto(`/?bundle=${'b'.repeat(64)}`); await expect(page.locator('main .error-panel[role="alert"]')).toContainText('Sonuçlar birleştirilemez');
  await expect(rows(page)).toHaveCount(0);
});

test('monthly report sources belonging to another fund cannot appear as selected-fund evidence', async ({page}) => {
  const state: MockState = {}; await mockResearch(page, state);
  for (const kind of ['KAP_SERIES', 'KAP_PDF']) {
    state.mutate = (path, payload) => {
      if (path.endsWith('/funds/S00')) {
        const source = (payload as ReturnType<ReturnType<typeof researchFixture>['detail']>).sources.find(item => item.kind === kind)!;
        source.fund_code = 'S01';
      }
      return payload;
    };
    await page.goto('/funds/S00');
    await expect(page.locator('main .error-panel[role="alert"]')).toContainText('Aylık rapor kaynağı seçilen fona ait değil');
    await expect(page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true})).toHaveCount(0);
    await expect(page.getByRole('heading', {name: 'İki ayrı araştırma hesabı', exact: true})).toHaveCount(0);
  }
});

test('partial, stale and absent detail data stay distinct from a negative result', async ({page}) => {
  await mockResearch(page); await page.goto('/funds/S02'); await detailReady(page, 'S02');
  await expect(page.getByText('Tek bulgu mevcut; aylık veri eksik. Sentetik test yorumu.', {exact: true})).toBeVisible();
  const metrics = page.locator('.metric-panel');
  await expect(metrics.nth(1).locator('.metric-value')).toHaveText('—');
  await expect(metrics.nth(1)).toContainText('Veri yetersiz');
  await expect(page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true})).toHaveCount(0);
  await expect(page.getByText('Bu pakette açılabilir orijinal PDF bulunmuyor.', {exact: true})).toBeVisible();
  await page.goto('/funds/S03'); await detailReady(page, 'S03');
  await expect(page.locator('.metric-panel').first()).toContainText('Güncel gözlem eksik');
  await expect(page.locator('.metric-panel').first()).toContainText('15 Eyl 2026');
  await page.goto('/funds/S04'); await detailReady(page, 'S04');
  await expect(page.locator('.metric-panel .metric-value')).toHaveText(['—', '—']);
  await expect(page.getByText('Grafik için yeterli veri yok', {exact: true})).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  await expect(page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true})).toHaveCount(0);
  await expect(page.getByText(/Eşik aşımı olmaması da güvenli olduğu anlamına gelmez/)).toBeVisible();
});

test('actual chart canvases have an accessible table that preserves the authored missing gap', async ({page}) => {
  await mockResearch(page); await page.goto('/funds/S00'); await detailReady(page, 'S00');
  const figure = page.getByRole('figure', {name: 'Fon ve kategori benzerlerinin normalleştirilmiş getirisi'});
  await expect(figure).toBeVisible(); await expect(figure.locator('canvas').first()).toBeVisible();
  await expect(figure).toContainText('Eksik gözlemler çizgide boşluk bırakır');
  await figure.getByText('Grafik verilerini tablo olarak göster', {exact: true}).click();
  const table = figure.getByRole('table', {name: 'Ortak başlangıç 100; eksik gözlemler boş bırakılmıştır'});
  await expect(table).toBeVisible(); await expect(table.locator('tbody tr')).toHaveCount(6);
  const gap = table.locator('tbody tr').filter({hasText: '3 Ağu 2026'});
  await expect(gap.getByRole('cell')).toHaveText(['Veri yok', '102']);
  await expect(table.locator('tbody tr').filter({hasText: '1 Tem 2026'}).getByRole('cell')).toHaveText(['100', '100']);
  await expect(figure.getByRole('alert')).toHaveCount(0);
});

test('source dates, unknown currency and official disclosure links use the actual source contract', async ({page}) => {
  await mockResearch(page); await page.goto('/funds/S00'); await detailReady(page, 'S00');
  await expect(page.locator('.metric-panel').nth(1)).toContainText('rapor para birimi');
  await expect(page.locator('.metric-panel').nth(1)).not.toContainText(/TRY|₺/);
  const sources = page.locator('.evidence-source'); await expect(sources).toHaveCount(3);
  const price = sources.filter({hasText: 'Günlük fon fiyatları'});
  await expect(price).toContainText('Bilinmiyor');
  const kapLink = page.getByRole('link', {name: /KAP.*bildirim|KAP.*aç|KAP.*sayfa/i});
  await expect(kapLink).toHaveAttribute('href', 'https://www.kap.org.tr/tr/Bildirim/900000001');
  await expect(kapLink).toHaveAttribute('rel', /noopener|noreferrer/);
  await expect(sources.filter({hasText: 'Orijinal KAP raporu'})).toContainText('2 Eyl 2026');
});

test('native PDF modal verifies bytes, renders both authored pages locally and restores focus on Escape', async ({page}) => {
  let release!: () => void;
  const state: MockState = {pdfGate: new Promise<void>(resolve => {release = resolve;})};
  const {fixture, requests} = await mockResearch(page, state);
  const networkUrls: string[] = [];
  page.on('request', request => {networkUrls.push(request.url());});
  await page.goto('/funds/S00'); await detailReady(page, 'S00');
  const trigger = page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true}); await trigger.click();
  const dialog = page.getByRole('dialog', {name: 'Orijinal kaynak PDF', exact: true}); await expect(dialog).toBeVisible();
  expect(await dialog.evaluate(element => element instanceof HTMLDialogElement && element.open)).toBe(true);
  const close = dialog.getByRole('button', {name: 'Kapat', exact: true}); await expect(close).toBeFocused();
  await expect(dialog.getByRole('status')).toHaveText('PDF doğrulanıyor…');
  expect(await dialog.evaluate(element => element.matches(':modal'))).toBe(true);
  await trigger.evaluate(element => (element as HTMLButtonElement).focus()); await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Tab'); await expect(close).toBeFocused();
  release(); await renderedPdfPage(page, 1);
  await expect(dialog.getByRole('button', {name: 'Önceki sayfa', exact: true})).toBeDisabled();
  await pdfTextVisible(page, 'Authored synthetic browser fixture');
  await dialog.getByRole('button', {name: 'Sonraki sayfa', exact: true}).click(); await renderedPdfPage(page, 2);
  await expect(dialog.getByRole('button', {name: 'Sonraki sayfa', exact: true})).toBeDisabled();
  await pdfTextVisible(page, 'Authored synthetic second page');
  await dialog.getByRole('button', {name: 'Önceki sayfa', exact: true}).click(); await renderedPdfPage(page, 1);
  await expect(dialog.locator('iframe')).toHaveCount(0);
  await expect(dialog.getByRole('link', {name: 'PDF’yi ayrı sekmede aç', exact: true})).toHaveAttribute('href', /^blob:/);
  expect(networkUrls.filter(url => /^https?:/.test(url)).every(url => new URL(url).origin === 'http://127.0.0.1:3060')).toBe(true);
  expect(requests.filter(path => path.startsWith('/api/research/v1/sources/'))).toEqual([`/api/research/v1/sources/${fixture.detail('S00').sources.find(source => source.pdf_available)!.source_id}`]);
  await close.focus(); await page.keyboard.press('Escape'); await expect(dialog).toHaveCount(0); await expect(trigger).toBeFocused();
  let reopen!: () => void;
  state.pdfGate = new Promise<void>(resolve => {reopen = resolve;});
  await trigger.click(); await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('status')).toHaveText('PDF doğrulanıyor…');
  await expect(dialog.locator('canvas')).toHaveCount(0);
  await expect(dialog.getByRole('link', {name: 'Orijinal PDF’yi indir', exact: true})).toHaveCount(0);
  await expect(dialog.getByRole('link', {name: 'PDF’yi ayrı sekmede aç', exact: true})).toHaveCount(0);
  reopen(); await renderedPdfPage(page, 1);
  await close.click(); await expect(dialog).toHaveCount(0); await expect(trigger).toBeFocused();
});

for (const [pdf, error] of [['wrong-bundle', 'araştırma paketiyle eşleşmiyor'], ['bad-bytes', 'kaynak özetiyle eşleşmiyor'], ['missing', 'Orijinal PDF dosyası bulunamadı']] as const) {
  test(`PDF ${pdf} is visible as an error and cannot show unverified bytes`, async ({page}) => {
    const state: MockState = {pdf}; await mockResearch(page, state); await page.goto('/funds/S00'); await detailReady(page, 'S00');
    await page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true}).click();
    const dialog = page.getByRole('dialog', {name: 'Orijinal kaynak PDF', exact: true});
    await expect(dialog.getByRole('alert')).toContainText(error); await expect(dialog.locator('canvas')).toHaveCount(0);
    state.pdf = undefined; await dialog.getByRole('button', {name: 'Yeniden dene', exact: true}).click();
    await renderedPdfPage(page, 1);
  });
}

test('mobile real route retains 100 comments and keyboard filter controls without page overflow', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844}); await mockResearch(page); await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Fonların verileri ne söylüyor?', exact: true})).toBeVisible();
  await expect(page.locator('.mobile-funds')).toBeVisible(); await expect(page.locator('.desktop-funds')).toBeHidden();
  await expect(page.locator('.mobile-fund')).toHaveCount(100);
  await expect(page.locator('.mobile-fund').first()).toContainText('sentetik bir test yorumudur');
  await page.getByLabel('Fon ara', {exact: true}).focus(); await page.keyboard.press('Tab');
  await expect(page.getByLabel('Kategori', {exact: true})).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  await page.locator('.mobile-fund').first().getByRole('link', {name: 'S00 ↗', exact: true}).click(); await detailReady(page, 'S00');
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
});

test('desktop-mounted detail chart resizes to mobile without overflow before and during PDF viewing', async ({page}) => {
  await page.setViewportSize({width: 1280, height: 900}); await mockResearch(page);
  await page.goto('/funds/S00'); await detailReady(page, 'S00');
  const figure = page.getByRole('figure', {name: 'Fon ve kategori benzerlerinin normalleştirilmiş getirisi'});
  await expect(figure.locator('canvas').first()).toBeVisible();
  await figure.getByText('Grafik verilerini tablo olarak göster', {exact: true}).click();
  const table = figure.getByRole('table', {name: 'Ortak başlangıç 100; eksik gözlemler boş bırakılmıştır'});
  await expect(table.locator('tbody tr')).toHaveCount(6);
  const desktopChartWidth = (await figure.boundingBox())!.width;
  expect(desktopChartWidth).toBeGreaterThan(390);

  await page.setViewportSize({width: 390, height: 844});
  await expect.poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect.poll(async () => (await figure.boundingBox())!.width).toBeLessThanOrEqual(390);
  await expect(table.locator('tbody tr')).toHaveCount(6);
  await expect(table.locator('tbody tr').filter({hasText: '3 Ağu 2026'}).getByRole('cell')).toHaveText(['Veri yok', '102']);
  await expect(page.locator('.metric-panel').first().locator('.metric-value')).toHaveAttribute('title', '0.0020');
  await expect(page.getByRole('heading', {level: 1})).toContainText('S00');

  await page.getByRole('button', {name: 'Orijinal PDF’yi aç', exact: true}).click(); await renderedPdfPage(page, 1);
  await expect.poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('dialog', {name: 'Orijinal kaynak PDF', exact: true}).getByRole('button', {name: 'Kapat', exact: true}).click();
  await expect.poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(figure).toBeVisible(); await expect(table.locator('tbody tr')).toHaveCount(6);
});

test('concentration keeps subset share and portfolio coverage together without a third alert', async ({page}) => {
  await mockResearch(page); await page.goto('/'); await listReady(page);
  const row = rowFor(page, 'S00');
  await expect(row.locator('.concentration-cell')).toContainText('%100,00');
  await expect(row.locator('.concentration-cell')).toContainText('Portföy kapsamı: %75,00');
  await expect(row.locator('.concentration-cell')).toContainText('Kısmi portföy');
  await page.getByLabel('Bulgu', {exact: true}).selectOption('two'); await listReady(page, 1);
  await row.getByRole('link', {name: 'S00 ↗', exact: true}).click(); await detailReady(page, 'S00');
  const section = page.locator('.concentration-section');
  await expect(section.getByRole('heading', {name: 'Son açıklanan portföyde yoğunlaşma', exact: true})).toBeVisible();
  await expect(section).toContainText('Portföyün okunabilen payı: %75,00');
  await expect(section).toContainText('Portföyün tamamını temsil etmez');
  await expect(section).toContainText('Okunabilen menkul kıymetler içinde');
  await expect(section).toContainText('16 gün');
  await expect(section).toContainText('Örnek Kıymet Alfa'); await expect(section).toContainText('TRSYNA000001');
  await expect(section).toContainText('değişim hesaplanmadı');
  await expect(page.locator('.metric-panel')).toHaveCount(2);
  await section.getByRole('button', {name: 'Yoğunlaşma raporunun PDF’sini aç', exact: true}).click();
  await renderedPdfPage(page, 1);
  await page.getByRole('dialog').getByRole('button', {name: 'Kapat', exact: true}).click();
  await expect(section.getByRole('button', {name: 'Yoğunlaşma raporunun PDF’sini aç', exact: true})).toBeFocused();
});

test('unavailable and uncomputed concentration never render zero or a safety verdict', async ({page}) => {
  const state: MockState = {}; await mockResearch(page, state);
  await page.goto('/funds/S01'); await detailReady(page, 'S01');
  const section = page.locator('.concentration-section');
  await expect(section).toContainText('Portföy yoğunlaşması hesaplanamadı');
  await expect(section.locator('.holding-table')).toHaveCount(0);
  state.mutate = (path, payload) => {
    if (path.endsWith('/funds/S00')) (payload as ReturnType<ReturnType<typeof researchFixture>['detail']>).fund!.concentration = null;
    return payload;
  };
  await page.goto('/funds/S00'); await detailReady(page, 'S00');
  await expect(section).toContainText('Bu pakette portföy yoğunlaşması hesaplanmadı');
  await expect(section.locator('.holding-metrics')).toHaveCount(0);
  await expect(page.locator('.metric-panel')).toHaveCount(2);
});

test('mobile concentration retains coverage and accessible PDF row details without body overflow', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844}); await mockResearch(page);
  await page.goto('/'); await listReady(page);
  const mobile = page.locator('.mobile-fund').filter({has: page.getByRole('link', {name: 'S00 ↗', exact: true})});
  await expect(mobile.locator('.mobile-concentration')).toContainText('Portföy kapsamı: %75,00');
  await mobile.getByRole('link', {name: 'S00 ↗', exact: true}).click(); await detailReady(page, 'S00');
  const section = page.locator('.concentration-section');
  await section.getByText('Sayfa 1', {exact: true}).click();
  await expect(section).toContainText('Rapor değeri: 600,00');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await section.getByRole('button', {name: 'Yoğunlaşma raporunun PDF’sini aç', exact: true}).click();
  await renderedPdfPage(page, 1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('current concentration PDF uses the exact report identity when two reports share a publication instant', async ({page}) => {
  const state: MockState = {mutate: (path, payload) => {
    if (path.endsWith('/funds/S00')) {
      const detail = payload as ReturnType<ReturnType<typeof researchFixture>['detail']>;
      const current = detail.sources.find(source => source.kind === 'KAP_PDF')!;
      const previous = {...current, source_id: 'd'.repeat(64), file_name: '2026-07_authored-report.pdf'};
      detail.sources.unshift(previous);
      detail.fund!.concentration!.input_refs.push(previous.source_id);
      detail.fund!.concentration!.comparison = {...detail.fund!.concentration!.comparison, previous_period: '2026-07', previous_effective_date: '2026-07-31', previous_published_at: previous.published_at, input_refs: [previous.source_id]};
    }
    return payload;
  }};
  const {fixture, requests} = await mockResearch(page, state);
  await page.goto('/funds/S00'); await detailReady(page, 'S00');
  await page.locator('.concentration-section').getByRole('button', {name: 'Yoğunlaşma raporunun PDF’sini aç', exact: true}).click();
  await renderedPdfPage(page, 1);
  expect(requests.filter(path => path.startsWith('/api/research/v1/sources/'))).toEqual([`/api/research/v1/sources/${fixture.detail('S00').fund!.concentration!.current_source_id}`]);
});
