import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, '_site');
const pages = ['index.html', 'about.html'];
const documents = await Promise.all(pages.map(file => readFile(path.join(root, file), 'utf8')));
const assets = [...new Set(documents.flatMap(html => [...html.matchAll(/(?:src|href|poster)="(assets\/[^"?#]+)"/g)].map(match => match[1])))];
const files = [...pages, 'style.css', 'script.js', 'about.js', ...assets];

await rm(output, { recursive: true, force: true });
for (const file of files) {
  const destination = path.join(output, file);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(root, file), destination);
}
// Pages caches assets: a content-based version makes each deployment load its own code.
for (const file of ['style.css', 'script.js', 'about.js']) {
  const content = await readFile(path.join(root, file));
  const version = createHash('sha256').update(content).digest('hex').slice(0, 12);
  documents.forEach((html, index) => { documents[index] = html.replaceAll(`"${file}"`, `"${file}?v=${version}"`); });
}
for (const [index, file] of pages.entries()) await writeFile(path.join(output, file), documents[index]);
await writeFile(path.join(output, '.nojekyll'), '');
console.log(`Built GitHub Pages site with ${assets.length} referenced assets in _site/`);
