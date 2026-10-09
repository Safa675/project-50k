import {cp, mkdir, readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const version = '6.4.299';
const require = createRequire(import.meta.url);
const source = dirname(require.resolve('pdfjs-dist/package.json'));
const metadata = JSON.parse(await readFile(join(source, 'package.json'), 'utf8'));
if (metadata.version !== version) throw new Error('PDF.js asset version does not match the pinned viewer.');
const frontend = dirname(dirname(fileURLToPath(import.meta.url)));
const destination = join(frontend, 'public', 'pdfjs', version);
await mkdir(destination, {recursive: true});
await cp(join(source, 'build', 'pdf.worker.min.mjs'), join(destination, 'pdf.worker.min.mjs'));
await cp(join(source, 'LICENSE'), join(destination, 'LICENSE'));
for (const directory of ['cmaps', 'standard_fonts', 'wasm', 'iccs']) {
  await cp(join(source, directory), join(destination, directory), {recursive: true});
}
console.log(`Prepared local PDF.js ${version} worker, fonts, CMaps and decoders.`);
