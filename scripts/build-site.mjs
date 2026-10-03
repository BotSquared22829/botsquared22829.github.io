import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, '_site');
const html = await readFile(path.join(root, 'index.html'), 'utf8');
const assets = [...new Set([...html.matchAll(/(?:src|href|poster)="(assets\/[^"?#]+)"/g)].map(match => match[1]))];
const files = ['index.html', 'style.css', 'script.js', ...assets];

await rm(output, { recursive: true, force: true });
for (const file of files) {
  const destination = path.join(output, file);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(root, file), destination);
}
await writeFile(path.join(output, '.nojekyll'), '');
console.log(`Built GitHub Pages site with ${assets.length} referenced assets in _site/`);
