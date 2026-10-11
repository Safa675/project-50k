import {execFileSync} from 'node:child_process';
import {expect, test} from '@playwright/test';
import {login} from './agent-fixtures';

// Actual smoke HTTP and synthetic account only. Never run this against the real
// product, and always leave the isolated team resumed even when an assertion fails.
test.skip(process.env.P50K_CONTROL_SMOKE !== '1', 'Explicit isolated control smoke required');

test('admin can pause and resume the actual smoke team while heartbeat and composer stay usable', async ({page, baseURL}) => {
  expect(baseURL).toBe('http://127.0.0.1:3071');
  await page.setViewportSize({width: 1480, height: 712});
  await login(page);
  const csrf = async () => (await page.context().cookies()).find(cookie => cookie.name === 'p50k_csrf')?.value ?? '';
  const resume = async () => page.request.post('/api/p/agents/control', {
    headers: {Origin: baseURL!, 'X-CSRF-Token': await csrf()}, data: {action: 'RESUME'},
  });
  try {
    const original = await page.request.get('/api/p/agents/team');
    expect(original.ok()).toBe(true);
    const initial = await original.json();
    expect(typeof initial.control?.paused).toBe('boolean');
    if (initial.control.paused) expect((await resume()).ok()).toBe(true);
    await page.reload();
    await page.getByRole('button', {name: /^Ajan ekibi ve Raportör/}).click();
    const panel = page.getByRole('dialog', {name: 'Ajan ekibi · 7/24'});
    await expect(panel).toBeVisible();
    const pauseResponse = page.waitForResponse(response => response.url().endsWith('/api/p/agents/control') && response.request().method() === 'POST');
    await panel.getByRole('button', {name: 'Durdur', exact: true}).click();
    const paused = await pauseResponse;
    expect(paused.ok()).toBe(true);
    expect(paused.request().postDataJSON()).toEqual({action: 'PAUSE'});
    expect((await paused.json()).paused).toBe(true);
    await expect(panel.getByRole('button', {name: 'Devam et', exact: true})).toBeVisible();
    await expect(panel.getByText(/Durduruldu ·|Ekip durduruldu ·/)).toBeVisible();
    const feed = await page.request.get('/api/p/agents/team');
    expect((await feed.json()).control.paused).toBe(true);
    expect((await page.request.get('/api/p/health/ready')).ok()).toBe(true);
    const heartbeat = () => Number(execFileSync('docker', ['exec', 'p50k-smoke-worker-1', 'python', '-c',
      "import pathlib,time; value=float(pathlib.Path('/tmp/p50k-worker-heartbeat').read_text()); assert time.time()-value < 35; print(value)"], {encoding: 'utf8'}).trim());
    const initialHeartbeat = heartbeat();
    await expect.poll(heartbeat, {timeout: 15000}).toBeGreaterThan(initialHeartbeat);
    await expect(panel.getByRole('textbox', {name: 'Raportöre sorunuz'})).toBeVisible();
    const input = await panel.getByRole('textbox', {name: 'Raportöre sorunuz'}).boundingBox();
    expect(input).not.toBeNull();
    expect(input!.y + input!.height).toBeLessThanOrEqual(712);
    const chat = await panel.locator('.ag-chat').boundingBox();
    expect(chat!.height).toBeGreaterThanOrEqual(320);
    const resumeResponse = page.waitForResponse(response => response.url().endsWith('/api/p/agents/control') && response.request().method() === 'POST');
    await panel.getByRole('button', {name: 'Devam et', exact: true}).click();
    const resumed = await resumeResponse;
    expect(resumed.request().postDataJSON()).toEqual({action: 'RESUME'});
    expect((await resumed.json()).paused).toBe(false);
    await expect(panel.getByRole('button', {name: 'Durdur', exact: true})).toBeVisible();
    expect((await (await page.request.get('/api/p/agents/team')).json()).control.paused).toBe(false);
  } finally {
    expect((await resume()).ok()).toBe(true);
    expect((await (await page.request.get('/api/p/agents/team')).json()).control.paused).toBe(false);
  }
});
