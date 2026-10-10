// Run the repository's browser tests against a server on a spare port while port 3060 is busy.
// The browser origin stays http://127.0.0.1:3060 (the tests assert it); Chrome maps it to the spare port.
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const port = Number(process.env.P50K_SPARE_PORT || 3061);
if (!Number.isInteger(port) || port < 1024 || port > 65535 || port === 3060) {
  throw new Error('Set P50K_SPARE_PORT to a free port other than 3060.');
}
// The repository that contains this config, even when the session was started in another checkout.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');

export default {
  testDir: resolve(root, 'frontend/tests/browser'),
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  outputDir: resolve(root, 'frontend/test-results'),
  use: {
    baseURL: 'http://127.0.0.1:3060',
    channel: 'chrome',
    headless: true,
    screenshot: 'off',
    trace: 'off',
    video: 'off',
    launchOptions: {args: [`--host-rules=MAP 127.0.0.1:3060 127.0.0.1:${port}`]},
  },
};
