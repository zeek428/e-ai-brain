#!/usr/bin/env node
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import net from 'node:net';

const DEFAULT_ROUTES = [
  '/welcome',
  '/delivery/requirements',
  '/delivery/versions',
  '/delivery/bugs',
  '/tasks/management',
  '/governance/insights',
  '/governance/devops',
  '/system/roles',
];

const ACCESS_TOKEN_STORAGE_KEY = 'ai_brain_access_token';
const CURRENT_USER_STORAGE_KEY = 'ai_brain_current_user';

function normalizeRoutePath(route) {
  const value = String(route || '').trim();
  if (!value) {
    return '/';
  }
  return value.startsWith('/') ? value : `/${value}`;
}

function parseExpectedText(value) {
  const separatorIndex = value.indexOf('=');
  if (separatorIndex <= 0 || separatorIndex === value.length - 1) {
    throw new Error('--expect-text must use ROUTE=TEXT, for example /system/roles=系统管理员');
  }
  return {
    route: normalizeRoutePath(value.slice(0, separatorIndex)),
    text: value.slice(separatorIndex + 1),
  };
}

function parseArgs(argv) {
  const options = {
    apiBaseUrl: process.env.READINESS_API_BASE_URL || 'http://localhost:8000',
    bearerToken: process.env.READINESS_BEARER_TOKEN || '',
    chromePath: process.env.READINESS_CHROME_PATH || '',
    headed: false,
    expectedTextByRoute: {},
    password: process.env.READINESS_PASSWORD || '',
    routes: [],
    timeoutMs: Number(process.env.READINESS_WEB_SMOKE_TIMEOUT_MS || 20000),
    username: process.env.READINESS_USERNAME || '',
    webBaseUrl: process.env.READINESS_WEB_BASE_URL || 'http://localhost:5173',
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = () => {
      index += 1;
      if (index >= argv.length) {
        throw new Error(`${arg} requires a value`);
      }
      return argv[index];
    };
    if (arg === '--api-base-url') {
      options.apiBaseUrl = next();
    } else if (arg === '--bearer-token') {
      options.bearerToken = next();
    } else if (arg === '--chrome-path') {
      options.chromePath = next();
    } else if (arg === '--headed') {
      options.headed = true;
    } else if (arg === '--expect-text') {
      const expected = parseExpectedText(next());
      options.expectedTextByRoute[expected.route] = [
        ...(options.expectedTextByRoute[expected.route] || []),
        expected.text,
      ];
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--password') {
      options.password = next();
    } else if (arg === '--route') {
      options.routes.push(next());
    } else if (arg === '--timeout-ms') {
      options.timeoutMs = Number(next());
    } else if (arg === '--username') {
      options.username = next();
    } else if (arg === '--web-base-url') {
      options.webBaseUrl = next();
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  if (!options.routes.length) {
    options.routes = DEFAULT_ROUTES;
  }
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) {
    throw new Error('--timeout-ms must be a positive number');
  }
  return options;
}

function printHelp() {
  console.log(`AI Brain web page smoke

Usage:
  node scripts/web_page_smoke.mjs --web-base-url http://localhost:5173 --api-base-url http://localhost:8000

Options:
  --web-base-url URL      Web app base URL. Defaults to READINESS_WEB_BASE_URL or http://localhost:5173.
  --api-base-url URL      API base URL. Defaults to READINESS_API_BASE_URL or http://localhost:8000.
  --username USER         Login username. Defaults to READINESS_USERNAME.
  --password PASSWORD     Login password. Defaults to READINESS_PASSWORD.
  --bearer-token TOKEN    Existing bearer token. Defaults to READINESS_BEARER_TOKEN.
  --chrome-path PATH      Chrome/Chromium executable path. Defaults to READINESS_CHROME_PATH or auto-detect.
  --route PATH            Route to check. Can be provided multiple times.
  --expect-text ROUTE=TEXT
                          Require TEXT to appear after ROUTE renders. Can be provided multiple times.
  --timeout-ms MS         Per-route wait timeout. Defaults to 20000.
  --headed                Run Chrome with a visible window instead of headless mode.
`);
}

function normalizeBaseUrl(value) {
  return String(value || '').replace(/\/+$/, '');
}

async function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

function detectChromePath(explicitPath) {
  if (explicitPath) {
    if (existsSync(explicitPath)) {
      return explicitPath;
    }
    throw new Error(`Chrome executable not found: ${explicitPath}`);
  }
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  for (const command of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    const result = spawnSync('sh', ['-lc', `command -v ${command}`], { encoding: 'utf8' });
    const resolved = result.stdout.trim();
    if (result.status === 0 && resolved) {
      return resolved;
    }
  }
  throw new Error('Chrome/Chromium executable not found. Set READINESS_CHROME_PATH.');
}

function removeDirectoryBestEffort(directory) {
  try {
    rmSync(directory, {
      force: true,
      maxRetries: 5,
      recursive: true,
      retryDelay: 100,
    });
  } catch (error) {
    console.warn(`Warning: unable to remove temporary Chrome profile ${directory}: ${error.message}`);
  }
}

async function retryUntil(fn, timeoutMs, label) {
  const startedAt = Date.now();
  let lastError;
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const result = await fn();
      if (result) {
        return result;
      }
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`${label} timed out${lastError ? `: ${lastError.message}` : ''}`);
}

async function fetchJson(url, init) {
  const response = await fetch(url, init);
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return payload;
}

async function login(options) {
  if (options.bearerToken) {
    const user = await fetchJson(`${normalizeBaseUrl(options.apiBaseUrl)}/api/auth/me`, {
      headers: { Authorization: `Bearer ${options.bearerToken}` },
    });
    return { token: options.bearerToken, user: user.data };
  }
  if (!options.username || !options.password) {
    throw new Error('Provide READINESS_BEARER_TOKEN or READINESS_USERNAME/READINESS_PASSWORD.');
  }
  const payload = await fetchJson(`${normalizeBaseUrl(options.apiBaseUrl)}/api/auth/login`, {
    body: JSON.stringify({ username: options.username, password: options.password }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  const token = payload?.data?.access_token;
  const user = payload?.data?.user;
  if (!token || !user) {
    throw new Error('Login response is missing data.access_token or data.user.');
  }
  return { token, user };
}

class CdpClient {
  constructor(webSocketUrl) {
    this.id = 0;
    this.pending = new Map();
    this.eventHandlers = new Set();
    this.webSocketUrl = webSocketUrl;
  }

  connect(timeoutMs) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.webSocketUrl);
      const timer = setTimeout(() => {
        reject(new Error('CDP WebSocket connection timed out'));
      }, timeoutMs);
      ws.addEventListener('open', () => {
        clearTimeout(timer);
        this.ws = ws;
        resolve();
      });
      ws.addEventListener('message', (event) => this.handleMessage(event.data));
      ws.addEventListener('error', () => {
        reject(new Error('CDP WebSocket connection failed'));
      });
      ws.addEventListener('close', () => {
        for (const { reject: rejectPending } of this.pending.values()) {
          rejectPending(new Error('CDP WebSocket closed'));
        }
        this.pending.clear();
      });
    });
  }

  handleMessage(rawMessage) {
    const message = JSON.parse(rawMessage);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message || JSON.stringify(message.error)));
      } else {
        resolve(message.result);
      }
      return;
    }
    if (message.method) {
      for (const handler of this.eventHandlers) {
        handler(message);
      }
    }
  }

  onEvent(handler) {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }

  send(method, params = {}, sessionId) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('CDP WebSocket is not open');
    }
    const id = (this.id += 1);
    const message = { id, method, params };
    if (sessionId) {
      message.sessionId = sessionId;
    }
    this.ws.send(JSON.stringify(message));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }
}

async function launchChrome(options) {
  const port = await getFreePort();
  const userDataDir = mkdtempSync(path.join(tmpdir(), 'e-ai-brain-web-smoke-'));
  const chromePath = detectChromePath(options.chromePath);
  const args = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-gpu',
    '--window-size=1440,1000',
    'about:blank',
  ];
  if (!options.headed) {
    args.unshift('--headless=new');
  }
  const child = spawn(chromePath, args, { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  child.stderr.on('data', (chunk) => {
    stderr += String(chunk);
  });
  child.once('exit', (code) => {
    if (code !== 0 && stderr) {
      console.error(stderr.trim());
    }
  });
  const version = await retryUntil(
    () => fetchJson(`http://127.0.0.1:${port}/json/version`),
    options.timeoutMs,
    'Chrome DevTools endpoint',
  );
  return {
    browserWSEndpoint: version.webSocketDebuggerUrl,
    cleanup: () => {
      child.kill('SIGTERM');
      removeDirectoryBestEffort(userDataDir);
    },
    port,
  };
}

function routeUrl(webBaseUrl, route) {
  const base = normalizeBaseUrl(webBaseUrl);
  const normalizedRoute = route.startsWith('/') ? route : `/${route}`;
  return `${base}${normalizedRoute}`;
}

function collectRelevantErrors(messages) {
  return messages.filter((message) => {
    if (message.type === 'warning') {
      return false;
    }
    const text = `${message.type}: ${message.text}`;
    if (/favicon\.ico/i.test(text)) {
      return false;
    }
    return true;
  });
}

function collectRelevantNetworkFailures(responses) {
  return responses.filter((response) => {
    if (!response || response.status < 400) {
      return false;
    }
    if (/favicon\.ico/i.test(response.url)) {
      return false;
    }
    return true;
  });
}

async function evaluate(client, sessionId, expression) {
  const result = await client.send(
    'Runtime.evaluate',
    {
      awaitPromise: true,
      expression,
      returnByValue: true,
    },
    sessionId,
  );
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed');
  }
  return result.result?.value;
}

async function checkRoute(client, sessionId, route, options, messages, networkResponses) {
  messages.length = 0;
  networkResponses.length = 0;
  await client.send('Page.navigate', { url: routeUrl(options.webBaseUrl, route) }, sessionId);
  const expectedTexts = options.expectedTextByRoute[normalizeRoutePath(route)] || [];
  const state = await retryUntil(
    async () => {
      const value = await evaluate(
        client,
        sessionId,
        `(() => {
          const root = document.querySelector('#root');
          const bodyText = document.body ? document.body.innerText.trim() : '';
          const rootText = root ? root.innerText.trim() : '';
          const expectedTexts = ${JSON.stringify(expectedTexts)};
          return {
            bodyTextLength: bodyText.length,
            bodyTextSample: bodyText.slice(0, 240),
            missingExpectedTexts: expectedTexts.filter((text) => !bodyText.includes(text)),
            hasRoot: Boolean(root),
            locationPath: window.location.pathname,
            locationSearch: window.location.search,
            readyState: document.readyState,
            rootTextLength: rootText.length,
            title: document.title
          };
        })()`,
      );
      if (
        value.readyState === 'complete'
        && value.hasRoot
        && value.rootTextLength > 20
        && value.missingExpectedTexts.length === 0
      ) {
        return value;
      }
      return null;
    },
    options.timeoutMs,
    `Route ${route}`,
  );
  const relevantErrors = collectRelevantErrors(messages);
  const relevantNetworkFailures = collectRelevantNetworkFailures(networkResponses);
  const overlayText = `${state.bodyTextSample}`.toLowerCase();
  const overlayMarkers = [
    'failed to compile',
    'runtime error',
    'unhandled runtime error',
    'webpack compiled with',
    'vite',
  ];
  const overlay = overlayMarkers.find((marker) => overlayText.includes(marker));
  const failures = [];
  if (state.locationPath === '/login') {
    failures.push('redirected to login');
  }
  if (state.bodyTextLength <= 20 || state.rootTextLength <= 20) {
    failures.push('rendered content is blank or too short');
  }
  if (state.missingExpectedTexts.length) {
    failures.push(`missing expected text: ${state.missingExpectedTexts.join(', ')}`);
  }
  if (overlay) {
    failures.push(`framework overlay marker detected: ${overlay}`);
  }
  if (relevantErrors.length) {
    failures.push(
      `console/runtime errors: ${relevantErrors.map((item) => item.text).join(' | ')}`,
    );
  }
  if (relevantNetworkFailures.length) {
    failures.push(
      `network errors: ${relevantNetworkFailures
        .map((item) => `${item.status} ${item.url}`)
        .join(' | ')}`,
    );
  }
  return {
    failures,
    path: state.locationPath,
    route,
    sample: state.bodyTextSample.replace(/\s+/g, ' ').trim(),
    title: state.title,
  };
}

async function runSmoke(options) {
  const auth = await login(options);
  const chrome = await launchChrome(options);
  let client;
  try {
    client = new CdpClient(chrome.browserWSEndpoint);
    await client.connect(options.timeoutMs);
    const target = await client.send('Target.createTarget', { url: 'about:blank' });
    const attached = await client.send('Target.attachToTarget', {
      flatten: true,
      targetId: target.targetId,
    });
    const sessionId = attached.sessionId;
    const messages = [];
    const networkResponses = [];
    client.onEvent((message) => {
      if (message.sessionId !== sessionId) {
        return;
      }
      if (message.method === 'Runtime.consoleAPICalled') {
        const type = message.params?.type || 'console';
        if (type === 'error' || type === 'warning') {
          messages.push({
            text: (message.params?.args || [])
              .map((arg) => arg.value || arg.description || '')
              .join(' ')
              .trim(),
            type,
          });
        }
      } else if (message.method === 'Runtime.exceptionThrown') {
        messages.push({
          text:
            message.params?.exceptionDetails?.exception?.description ||
            message.params?.exceptionDetails?.text ||
            'Runtime exception',
          type: 'exception',
        });
      } else if (message.method === 'Log.entryAdded') {
        const entry = message.params?.entry || {};
        messages.push({
          text: entry.text || entry.url || 'Log entry',
          type: entry.level || 'log',
        });
      } else if (message.method === 'Network.responseReceived') {
        const response = message.params?.response || {};
        networkResponses.push({
          status: Number(response.status || 0),
          url: response.url || '',
        });
      }
    });
    await client.send('Page.enable', {}, sessionId);
    await client.send('Runtime.enable', {}, sessionId);
    await client.send('Log.enable', {}, sessionId);
    await client.send('Network.enable', {}, sessionId);
    await client.send(
      'Page.addScriptToEvaluateOnNewDocument',
      {
        source: `
          localStorage.setItem(${JSON.stringify(ACCESS_TOKEN_STORAGE_KEY)}, ${JSON.stringify(auth.token)});
          localStorage.setItem(${JSON.stringify(CURRENT_USER_STORAGE_KEY)}, ${JSON.stringify(JSON.stringify(auth.user))});
        `,
      },
      sessionId,
    );
    const results = [];
    for (const route of options.routes) {
      results.push(await checkRoute(client, sessionId, route, options, messages, networkResponses));
    }
    const failed = results.filter((result) => result.failures.length);
    for (const result of results) {
      const prefix = result.failures.length ? 'FAIL' : 'OK';
      console.log(
        `[${prefix}] ${result.route} -> ${result.path} · ${result.title || '-'} · ${result.sample}`,
      );
      for (const failure of result.failures) {
        console.log(`  - ${failure}`);
      }
    }
    if (failed.length) {
      throw new Error(`${failed.length} route(s) failed web smoke.`);
    }
    console.log(`Web page smoke passed for ${results.length} route(s).`);
  } finally {
    if (client) {
      client.close();
    }
    chrome.cleanup();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  await runSmoke(options);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
