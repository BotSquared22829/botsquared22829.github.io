import http from 'node:http';
import { realpath, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.webp': 'image/webp', '.avif': 'image/avif', '.gif': 'image/gif', '.woff2': 'font/woff2' };
const forbiddenPath = (relative) => path.isAbsolute(relative) || relative.split(path.sep).some((part) => part.startsWith('.'));

export async function createPreviewServer(directory = root) {
 const documentRoot = await realpath(directory);
 return http.createServer(async (request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end('Method not allowed');
    return;
  }
  try {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      if (pathname.includes('\0')) throw new URIError('Invalid path');
    } catch {
      response.writeHead(400).end('Bad request');
      return;
    }
    let file = path.resolve(documentRoot, `.${pathname === '/' ? '/index.html' : pathname}`);
    if (forbiddenPath(path.relative(documentRoot, file))) {
      response.writeHead(403).end('Forbidden');
      return;
    }
    // Check the resolved target too: a public-looking symlink can escape the root.
    file = await realpath(file);
    if (forbiddenPath(path.relative(documentRoot, file))) {
      response.writeHead(403).end('Forbidden');
      return;
    }
    const info = await stat(file);
    if (!info.isFile()) {
      response.writeHead(404).end('Not found');
      return;
    }
    const headers = { 'Content-Type': types[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-cache', 'Accept-Ranges': 'bytes', 'X-Content-Type-Options': 'nosniff' };
    let start = 0;
    let end = info.size - 1;
    let status = 200;
    if (request.method === 'GET' && request.headers.range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(request.headers.range);
      if (!match || (!match[1] && !match[2])) {
        response.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end();
        return;
      }
      if (!match[1]) start = Math.max(0, info.size - Number(match[2]));
      else {
        start = Number(match[1]);
        if (match[2]) end = Math.min(end, Number(match[2]));
      }
      if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || start > end || start >= info.size) {
        response.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end();
        return;
      }
      status = 206;
      headers['Content-Range'] = `bytes ${start}-${end}/${info.size}`;
    }
    headers['Content-Length'] = Math.max(0, end - start + 1);
    response.writeHead(status, headers);
    if (request.method === 'HEAD' || info.size === 0) response.end();
    else {
      const stream = createReadStream(file, { start, end });
      response.on('close', () => stream.destroy());
      stream.on('error', () => response.destroy()).pipe(response);
    }
  } catch {
    response.writeHead(404).end('Not found');
  }
 });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 5173);
  const server = await createPreviewServer();
  server.listen(port, '127.0.0.1', () => console.log(`BotSquared preview: http://127.0.0.1:${server.address().port}`));
}
