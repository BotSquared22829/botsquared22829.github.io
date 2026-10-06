import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtemp, mkdir, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { buildSite } from '../build-site.mjs';
import { createPreviewServer } from '../../server.mjs';

async function fixture(t, files) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'botsquared-tooling-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  for (const [name, content] of Object.entries(files)) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), content);
  }
  return root;
}

async function request(server, url, { method = 'GET', headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    http.request({ host: '127.0.0.1', port: server.address().port, path: url, method, headers }, response => {
      const chunks = [];
      response.on('data', chunk => chunks.push(chunk));
      response.on('end', () => resolve({ status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks).toString() }));
    }).on('error', reject).end();
  });
}

async function preview(t, files) {
  const root = await fixture(t, files);
  const server = await createPreviewServer(root);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  return { root, server };
}

test('build includes all pages and follows actual HTML, CSS, srcset and runtime assets', async t => {
  const root = await fixture(t, {
    'index.html': `<link href='style.css?theme=dark#top'><script src=app.js></script><img src='assets/a.png?v=1' srcset="assets/a.png 1x, assets/b.png 2x"><img srcset="data:image/png;base64,abc 1x, assets/c.png 2x"><img srcset="assets/d.png, assets/e.png" data-src="not-loaded.png"><a href='/other.html#story'>Next</a>`,
    'other.html': '<main id="story">Story</main>',
    'style.css': `@import "assets/nested.css"; .hero { background: url('assets/a.png?v=2'); }`,
    'assets/nested.css': '.nested { background: url("b.png"); }',
    'app.js': 'const image = "assets/c.png";',
    'assets/a.png': 'a', 'assets/b.png': 'b', 'assets/c.png': 'c',
    'assets/d.png': 'd', 'assets/e.png': 'e',
    'assets/unused.png': 'unused', 'server.mjs': 'local tool',
  });
  assert.deepEqual(await buildSite(root), { pages: 2, assets: 6 });
  const html = await readFile(path.join(root, '_site/index.html'), 'utf8');
  assert.match(html, /style\.css\?theme=dark&amp;v=[a-f0-9]{12}#top/);
  assert.match(html, /src=app\.js\?v=[a-f0-9]{12}/);
  assert.deepEqual((await readdir(path.join(root, '_site/assets'))).sort(), ['a.png', 'b.png', 'c.png', 'd.png', 'e.png', 'nested.css']);
  assert(!(await readdir(path.join(root, '_site'))).includes('server.mjs'));
});

test('missing references fail without replacing the previous successful build', async t => {
  const root = await fixture(t, { 'index.html': '<img src="assets/missing.png">', '_site/index.html': 'previous build' });
  await assert.rejects(buildSite(root), /ENOENT/);
  assert.equal(await readFile(path.join(root, '_site/index.html'), 'utf8'), 'previous build');
});

test('build rejects traversal and symlink escapes', async t => {
  const root = await fixture(t, { 'index.html': '<img src="../private.png">', 'private.png': 'private', 'assets/ok.png': 'ok' });
  await assert.rejects(buildSite(root), /Unsafe local reference/);
  await writeFile(path.join(root, 'index.html'), '<img src="assets/link.png">');
  await symlink(os.tmpdir(), path.join(root, 'assets/link.png'));
  await assert.rejects(buildSite(root), /Asset escapes the public root/);
});

test('preview preserves byte-range seeking, suffixes, HEAD and empty responses', async t => {
  const { server } = await preview(t, { 'index.html': 'home', 'movie.mp4': '0123456789', 'empty.txt': '' });
  const partial = await request(server, '/movie.mp4', { headers: { Range: 'bytes=2-5' } });
  assert.equal(partial.status, 206);
  assert.equal(partial.body, '2345');
  assert.equal(partial.headers['content-range'], 'bytes 2-5/10');
  assert.equal((await request(server, '/movie.mp4', { headers: { Range: 'bytes=-3' } })).body, '789');
  const head = await request(server, '/movie.mp4', { method: 'HEAD', headers: { Range: 'bytes=2-5' } });
  assert.equal(head.status, 200);
  assert.equal(head.headers['content-length'], '10');
  assert.equal(head.body, '');
  assert.equal((await request(server, '/empty.txt')).body, '');
  for (const range of ['bytes=10-', 'bytes=-0', 'bytes=5-2', 'bytes=0-1,3-4']) {
    const invalid = await request(server, '/movie.mp4', { headers: { Range: range } });
    assert.equal(invalid.status, 416);
    assert.equal(invalid.headers['content-range'], 'bytes */10');
  }
});

test('preview rejects malformed paths, unsupported methods and private symlink targets', async t => {
  const { root, server } = await preview(t, { 'index.html': 'home', '.secret': 'private' });
  await symlink(path.join(root, '.secret'), path.join(root, 'secret.txt'));
  await symlink(path.dirname(root), path.join(root, 'outside'));
  assert.equal((await request(server, '/')).body, 'home');
  assert.equal((await request(server, '/%E0%A4%A')).status, 400);
  assert.equal((await request(server, '/%00')).status, 400);
  assert.equal((await request(server, '/.secret')).status, 403);
  assert.equal((await request(server, '/secret.txt')).status, 403);
  assert.equal((await request(server, `/outside/${path.basename(root)}/index.html`)).status, 200);
  assert.equal((await request(server, '/outside')).status, 403);
  assert.equal((await request(server, '/', { method: 'POST' })).status, 405);
  assert.equal((await request(server, '/missing')).status, 404);
});
