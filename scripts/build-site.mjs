import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, '_site');
let html = await readFile(path.join(root, 'index.html'), 'utf8');
const assets = [...new Set([...html.matchAll(/(?:src|href|poster)="(assets\/[^"?#]+)"/g)].map(match => match[1]))];
const files = ['index.html', 'style.css', 'script.js', ...assets];

await rm(output, { recursive: true, force: true });
for (const file of files) {
  const destination = path.join(output, file);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(root, file), destination);
}
// Pages caches assets: a content-based version makes each deployment load its own code.
for (const file of ['style.css', 'script.js']) {
  const content = await readFile(path.join(root, file));
  const version = createHash('sha256').update(content).digest('hex').slice(0, 12);
  html = html.replaceAll(`"${file}"`, `"${file}?v=${version}"`);
}
await writeFile(path.join(output, 'index.html'), html);
await writeFile(path.join(output, '.nojekyll'), '');
console.log(`Built GitHub Pages site with ${assets.length} referenced assets in _site/`);
