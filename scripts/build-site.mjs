import { copyFile, mkdir, mkdtemp, readFile, readdir, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const htmlReferences = /(?<![\w:-])(src|href|poster|srcset)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
const cssReferences = /url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]*))\s*\)|@import\s+(?:"([^"]*)"|'([^']*)')/gi;

function references(source, extension) {
  if (extension === '.html') {
    return [...source.matchAll(htmlReferences)].flatMap((match) => {
      const value = match[2] ?? match[3] ?? match[4];
      if (match[1].toLowerCase() === 'srcset') {
        // Keep commas inside data URLs while separating candidates and descriptors.
        const urls = [];
        let remaining = value;
        while ((remaining = remaining.replace(/^[\s,]+/, ''))) {
          const url = /^\S+/.exec(remaining)[0];
          urls.push(url.replace(/,+$/, ''));
          remaining = remaining.slice(url.length);
          if (!url.endsWith(',')) {
            const delimiter = remaining.indexOf(',');
            remaining = delimiter < 0 ? '' : remaining.slice(delimiter + 1);
          }
        }
        return urls;
      }
      return [value];
    });
  }
  if (extension === '.css') return [...source.matchAll(cssReferences)].map(match => match.slice(1).find(value => value !== undefined));
  // Runtime-created media use literal assets/ URLs; HTML script references seed JS files.
  if (extension === '.js') return [...source.matchAll(/["'`](assets\/[^"'`\s]+)["'`]/g)].map(match => match[1]);
  return [];
}

function localFile(reference, parent) {
  reference = reference.trim();
  if (!reference || /^(?:[a-z][\w+.-]*:|\/\/|#)/i.test(reference)) return null;
  const pathname = decodeURIComponent(reference.split(/[?#]/, 1)[0]);
  if (!pathname) return null;
  const file = path.posix.normalize(pathname.startsWith('/') ? pathname.slice(1) : path.posix.join(path.posix.dirname(parent), pathname));
  const normalized = file === '.' || pathname.endsWith('/') ? path.posix.join(file, 'index.html') : file;
  if (normalized.split('/').some(part => part.startsWith('.'))) throw new Error(`Unsafe local reference in ${parent}: ${reference}`);
  // Only publish the website, never local tools, source models, or hidden files.
  if (!normalized.startsWith('assets/') && (normalized.includes('/') || !/\.(?:html|css|js)$/.test(normalized))) {
    throw new Error(`Non-public local reference in ${parent}: ${reference}`);
  }
  return normalized;
}

export async function buildSite(directory = root) {
  const documentRoot = await realpath(directory);
  const output = path.join(documentRoot, '_site');
  const pages = (await readdir(documentRoot)).filter(file => file.endsWith('.html')).sort();
  if (!pages.includes('index.html')) throw new Error('The website needs index.html');
  const files = new Set(pages);
  const documents = new Map();
  const codeVersions = new Map();
  // Walk references before replacing the previous build, including nested CSS assets.
  for (const file of files) {
    const source = path.join(documentRoot, file);
    const resolved = await realpath(source);
    const relative = path.relative(documentRoot, resolved);
    if (path.isAbsolute(relative) || relative.split(path.sep).some(part => part.startsWith('.'))) throw new Error(`Asset escapes the public root: ${file}`);
    const extension = path.extname(file);
    if (!['.html', '.css', '.js'].includes(extension)) continue;
    const content = await readFile(source, 'utf8');
    if (extension === '.html') documents.set(file, content);
    else codeVersions.set(file, createHash('sha256').update(content).digest('hex').slice(0, 12));
    for (const reference of references(content, extension)) {
      const dependency = localFile(reference, file);
      if (dependency) files.add(dependency);
    }
  }
  const staging = await mkdtemp(path.join(documentRoot, '.site-build-'));
  try {
    for (const file of files) {
      const destination = path.join(staging, file);
      await mkdir(path.dirname(destination), { recursive: true });
      await copyFile(path.join(documentRoot, file), destination);
    }
    for (const [file, html] of documents) {
      const versioned = html.replace(htmlReferences, (attribute, name, double, single, unquoted) => {
        if (name.toLowerCase() === 'srcset') return attribute;
        const reference = double ?? single ?? unquoted;
        const dependency = localFile(reference, file);
        const version = codeVersions.get(dependency);
        if (!version) return attribute;
        const hashIndex = reference.indexOf('#');
        const hash = hashIndex < 0 ? '' : reference.slice(hashIndex);
        const beforeHash = hashIndex < 0 ? reference : reference.slice(0, hashIndex);
        const queryIndex = beforeHash.indexOf('?');
        const pathname = queryIndex < 0 ? beforeHash : beforeHash.slice(0, queryIndex);
        const query = new URLSearchParams(queryIndex < 0 ? '' : beforeHash.slice(queryIndex + 1).replaceAll('&amp;', '&'));
        query.set('v', version);
        return attribute.replace(reference, `${pathname}?${query.toString().replaceAll('&', '&amp;')}${hash}`);
      });
      await writeFile(path.join(staging, file), versioned);
    }
    await writeFile(path.join(staging, '.nojekyll'), '');
    await rm(output, { recursive: true, force: true });
    await rename(staging, output);
  } finally {
    await rm(staging, { recursive: true, force: true });
  }
  return { pages: pages.length, assets: [...files].filter(file => file.startsWith('assets/')).length };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await buildSite();
  console.log(`Built ${result.pages} pages with ${result.assets} referenced assets in _site/`);
}
