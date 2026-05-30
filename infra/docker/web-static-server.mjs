import { createReadStream, existsSync } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';

const host = '0.0.0.0';
const port = Number(process.env.PORT || 5173);
const distDir = join(process.cwd(), 'dist');
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://api:8000';

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
};

function collectRequestBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on('data', (chunk) => chunks.push(chunk));
    request.on('error', reject);
    request.on('end', () => resolve(Buffer.concat(chunks)));
  });
}

async function proxyApi(request, response) {
  const targetUrl = new URL(request.url || '/', apiProxyTarget);
  const body = ['GET', 'HEAD'].includes(request.method || 'GET')
    ? undefined
    : await collectRequestBody(request);
  const headers = new Headers();
  Object.entries(request.headers).forEach(([key, value]) => {
    if (key === 'host' || value === undefined) {
      return;
    }
    headers.set(key, Array.isArray(value) ? value.join(',') : value);
  });

  const proxyResponse = await fetch(targetUrl, {
    body,
    headers,
    method: request.method,
  });

  response.statusCode = proxyResponse.status;
  proxyResponse.headers.forEach((value, key) => {
    if (!['content-encoding', 'content-length', 'transfer-encoding'].includes(key)) {
      response.setHeader(key, value);
    }
  });
  response.end(Buffer.from(await proxyResponse.arrayBuffer()));
}

function resolveStaticPath(requestUrl) {
  const url = new URL(requestUrl || '/', `http://${host}:${port}`);
  const pathname = decodeURIComponent(url.pathname);
  const normalized = normalize(pathname).replace(/^(\.\.[/\\])+/, '');
  return join(distDir, normalized === '/' ? 'index.html' : normalized);
}

async function serveStatic(request, response) {
  let filePath = resolveStaticPath(request.url);
  if (!existsSync(filePath) || !(await stat(filePath)).isFile()) {
    filePath = join(distDir, 'index.html');
  }

  response.setHeader('Content-Type', contentTypes[extname(filePath)] || 'application/octet-stream');
  createReadStream(filePath)
    .on('error', async () => {
      response.statusCode = 500;
      response.end(await readFile(join(distDir, 'index.html')));
    })
    .pipe(response);
}

createServer(async (request, response) => {
  try {
    if (request.url?.startsWith('/api/')) {
      await proxyApi(request, response);
      return;
    }
    await serveStatic(request, response);
  } catch (error) {
    console.error(error);
    response.statusCode = 502;
    response.end('Bad Gateway');
  }
}).listen(port, host, () => {
  console.log(`AI Brain web listening on http://${host}:${port}`);
});
