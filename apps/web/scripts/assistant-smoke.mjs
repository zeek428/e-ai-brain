/* global WebSocket, console, fetch, process, setTimeout */
import fs from 'node:fs';
import os from 'node:os';
import { spawn } from 'node:child_process';

const apiUrl = process.env.AI_BRAIN_API_URL ?? 'http://localhost:8000';
const webUrl = process.env.AI_BRAIN_WEB_URL ?? 'http://localhost:5173';
const username = process.env.AI_BRAIN_E2E_USERNAME ?? 'admin@example.com';
const password = process.env.AI_BRAIN_E2E_PASSWORD ?? 'admin123';
const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = Number(process.env.CHROME_REMOTE_DEBUGGING_PORT ?? 9400 + Math.floor(Math.random() * 400));
const userDataDir = fs.mkdtempSync(`${os.tmpdir()}/e-ai-brain-assistant-smoke-`);
const assistantViewports = [
  { height: 900, label: 'desktop', mobile: false, width: 1440 },
  { height: 900, label: 'tablet-narrow', mobile: false, width: 768 },
  { height: 844, label: 'mobile', mobile: true, width: 390 },
];

const sleep = (ms) => new Promise((resolve) => {
  setTimeout(resolve, ms);
});

async function waitFor(label, fn, timeout = 15000, interval = 150) {
  const startedAt = Date.now();
  let lastError;
  while (Date.now() - startedAt < timeout) {
    try {
      const value = await fn();
      if (value) {
        return value;
      }
    } catch (error) {
      lastError = error;
    }
    await sleep(interval);
  }
  throw lastError ?? new Error(`Timeout waiting for ${label}`);
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${url}`);
  }
  return response.json();
}

class CdpClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.handlers = new Map();
    this.opened = new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', (event) => {
      const message = JSON.parse(event.data.toString());
      if (message.id && this.pending.has(message.id)) {
        const { reject, resolve } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(`${message.error.code}: ${message.error.message}`));
        } else {
          resolve(message.result ?? {});
        }
        return;
      }
      const listeners = this.handlers.get(message.method) ?? [];
      listeners.forEach((listener) => listener(message.params ?? {}));
    });
  }

  async send(method, params = {}) {
    await this.opened;
    const id = this.nextId;
    this.nextId += 1;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { reject, resolve });
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }

  on(method, listener) {
    const listeners = this.handlers.get(method) ?? [];
    listeners.push(listener);
    this.handlers.set(method, listeners);
  }

  close() {
    this.ws.close();
  }
}

async function loginToken() {
  const response = await getJson(`${apiUrl}/api/auth/login`, {
    body: JSON.stringify({ password, username }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  return response.data.access_token;
}

async function main() {
  const token = await loginToken();
  const chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'ignore'] });

  let client;
  try {
    await waitFor('Chrome DevTools', () => getJson(`http://127.0.0.1:${port}/json/version`).catch(() => null), 20000);
    const target = await getJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' });
    client = new CdpClient(target.webSocketDebuggerUrl);
    const consoleIssues = [];
    const httpIssues = [];

    client.on('Runtime.consoleAPICalled', (params) => {
      if (!['error', 'warning'].includes(params.type)) {
        return;
      }
      const text = (params.args ?? []).map((arg) => arg.value ?? arg.description ?? '').join(' ').slice(0, 220);
      if (!text.includes('Static function can not consume context')) {
        consoleIssues.push({ text, type: params.type });
      }
    });
    client.on('Network.responseReceived', ({ response }) => {
      if (response?.url.includes('/api/') && response.status >= 400) {
        httpIssues.push({ status: response.status, url: response.url.replace(/\?.*/, '') });
      }
    });

    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Network.enable');
    const setViewport = (viewport) => client.send('Emulation.setDeviceMetricsOverride', {
      deviceScaleFactor: 1,
      height: viewport.height,
      mobile: viewport.mobile,
      width: viewport.width,
    });
    await setViewport(assistantViewports[0]);

    const evaluate = async (expression) => {
      const result = await client.send('Runtime.evaluate', {
        awaitPromise: true,
        expression,
        returnByValue: true,
      });
      return result.result.value;
    };
    const hasText = (text) => evaluate(`document.body.innerText.includes(${JSON.stringify(text)})`);
    const clickButton = (predicateSource) => evaluate(`
      (() => {
        const button = [...document.querySelectorAll('button')].find((el) => (${predicateSource})(el));
        if (!button) return false;
        button.click();
        return true;
      })()
    `);
    const focusComposer = () => evaluate(`
      (() => {
        const input = document.querySelector('textarea');
        if (!input) return false;
        input.focus();
        return true;
      })()
    `);
    const clearComposer = () => evaluate(`
      (() => {
        const input = document.querySelector('textarea');
        if (!input) return false;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(input, '');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      })()
    `);
    const assertAssistantLayout = async (viewport) => {
      await setViewport(viewport);
      await client.send('Page.navigate', { url: `${webUrl}/assistant` });
      await waitFor(`assistant page ${viewport.label}`, async () => (
        (await hasText('研发助手')) && (await hasText('最近对话'))
      ), 20000);
      await waitFor(`assistant composer visible ${viewport.label}`, () => evaluate(`
        (() => {
          const input = document.querySelector('textarea');
          if (!input) return false;
          const rect = input.getBoundingClientRect();
          return rect.width > 160
            && rect.height > 40
            && rect.top >= 0
            && rect.left >= 0
            && rect.bottom <= window.innerHeight
            && rect.right <= window.innerWidth;
        })()
      `), 10000);
      const layout = await evaluate(`
        (() => {
          const all = [...document.querySelectorAll('body *')];
          const visibleTextElement = (text) => all
            .filter((el) => {
              if (!el.innerText || !el.innerText.includes(text)) return false;
              const rect = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              return rect.width > 0
                && rect.height > 0
                && style.visibility !== 'hidden'
                && style.display !== 'none';
            })
            .sort((left, right) => left.innerText.length - right.innerText.length)[0];
          const recent = visibleTextElement('最近对话');
          const recentRect = recent?.getBoundingClientRect();
          return {
            horizontalOverflow: Math.max(
              document.body.scrollWidth,
              document.documentElement.scrollWidth,
            ) > window.innerWidth + 4,
            recentVisible: Boolean(recentRect)
              && recentRect.top >= 0
              && recentRect.bottom <= window.innerHeight,
          };
        })()
      `);
      if (layout.horizontalOverflow || !layout.recentVisible) {
        throw new Error(`Assistant layout failed on ${viewport.label}: ${JSON.stringify(layout)}`);
      }
      await clickButton('(el) => el.getAttribute("aria-label") === "添加 @ 能力"');
      await waitFor(`+ action menu layout ${viewport.label}`, () => evaluate(`
        (() => {
          const all = [...document.querySelectorAll('body *')];
          const visibleTextElement = (text) => all
            .filter((el) => {
              if (!el.innerText || !el.innerText.includes(text)) return false;
              const rect = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              return rect.width > 0
                && rect.height > 0
                && style.visibility !== 'hidden'
                && style.display !== 'none';
            })
            .sort((left, right) => left.innerText.length - right.innerText.length)[0];
          const first = visibleTextElement('新建需求');
          const last = visibleTextElement('运行诊断');
          const firstRect = first?.getBoundingClientRect();
          const lastRect = last?.getBoundingClientRect();
          return Boolean(firstRect && lastRect)
            && firstRect.top >= 0
            && lastRect.bottom <= window.innerHeight
            && firstRect.left >= 0
            && lastRect.right <= window.innerWidth;
        })()
      `), 10000);
      await client.send('Input.dispatchKeyEvent', { key: 'Escape', type: 'keyDown' });
    };

    await client.send('Page.navigate', { url: `${webUrl}/login` });
    await waitFor('login page', () => evaluate('document.readyState === "complete"'));
    await evaluate(`
      localStorage.setItem('ai_brain_access_token', ${JSON.stringify(token)});
      localStorage.setItem('ai_brain_current_user', ${JSON.stringify(JSON.stringify({
        display_name: 'AI Brain Admin',
        id: 'user_admin',
        role: 'admin',
        roles: ['admin'],
        username,
      }))});
      true;
    `);
    await client.send('Page.navigate', { url: `${webUrl}/assistant` });
    await waitFor('assistant page', async () => (await hasText('研发助手')) && (await hasText('AI 助手')), 20000);
    await waitFor('runtime status diagnostics hidden', () => evaluate(`
      !document.body.innerText.includes('规则能力模式')
        && !document.body.innerText.includes('model_gateway')
        && !document.body.innerText.includes('embedding_gateway')
        && !document.body.innerText.includes('long_memory')
    `), 10000);

    await focusComposer();
    await client.send('Input.insertText', { text: '@反馈' });
    await waitFor('@ scheduled job candidate search', () => evaluate(`
      Boolean([...document.querySelectorAll('[aria-label="引用候选"] button')].find((el) => (
        el.querySelector('.assistant-reference-candidate-chips')?.textContent.includes('定时作业')
      )))
    `), 10000);
    const scheduledJobCandidateTitle = await evaluate(`
      (() => {
        const button = [...document.querySelectorAll('[aria-label="引用候选"] button')].find((el) => (
          el.querySelector('.assistant-reference-candidate-chips')?.textContent.includes('定时作业')
        ));
        const title = button?.querySelector('.assistant-reference-candidate-title')?.textContent.trim() || '';
        button?.click();
        return title;
      })()
    `);
    await waitFor('@ scheduled job command inserted', () => evaluate(`
      (() => {
        const textarea = document.querySelector('textarea[aria-label="发送给 AI 助手"]');
        return Boolean(textarea)
          && textarea.value.startsWith('@')
          && textarea.value.includes(${JSON.stringify(scheduledJobCandidateTitle)});
      })()
    `), 10000);
    await client.send('Input.dispatchKeyEvent', { key: 'Escape', type: 'keyDown' });
    await clearComposer();

    await clickButton('(el) => el.getAttribute("aria-label") === "添加 @ 能力"');
    await waitFor('+ action menu', async () => (await hasText('新建需求')) && (await hasText('运行诊断')), 10000);
    await client.send('Input.dispatchKeyEvent', { key: 'Escape', type: 'keyDown' });

    await focusComposer();
    await client.send('Input.insertText', { text: '停止' });
    await waitFor('stop command enabled', () => evaluate(`
      Boolean([...document.querySelectorAll('button')].find((el) => el.getAttribute('aria-label') === '发送' && !el.disabled))
    `), 10000);
    await clearComposer();

    await clickButton('(el) => el.innerText.includes("效果指标") || el.innerText.includes("查看指标")');
    await waitFor('metric card', () => evaluate(`
      Boolean([...document.querySelectorAll('button')].find((el) => el.getAttribute('aria-label') === '指标 草案生成数'))
    `), 20000);
    await clickButton('(el) => el.getAttribute("aria-label") === "指标 草案生成数"');
    await waitFor('metric details', async () => (
      (await hasText('草案生成'))
        && ((await hasText('查看来源')) || (await hasText('点击上方指标查看对应草案、运行或引用明细。')))
    ), 10000);
    await client.send('Input.dispatchKeyEvent', { key: 'Escape', type: 'keyDown' });

    const duplicateButtonVisible = await evaluate(`
      Boolean([...document.querySelectorAll('button')].find((el) => el.innerText.includes('展开重复') || el.innerText.includes('收起重复')))
    `);
    if (duplicateButtonVisible) {
      await clickButton('(el) => el.innerText.includes("展开重复") || el.innerText.includes("收起重复")');
      await waitFor('duplicate toggle', () => hasText('最近对话'), 5000);
    }

    await client.send('Page.navigate', { url: `${webUrl}/system/assistant-action-references` });
    await waitFor('@ ability config page', async () => (
      (await hasText('AI助手 @ 能力配置')) && (await hasText('新增能力'))
    ), 20000);
    await waitFor('@ ability config rows', async () => (
      (await hasText('新建需求')) || (await hasText('能力'))
    ), 10000);

    for (const viewport of assistantViewports) {
      await assertAssistantLayout(viewport);
    }

    if (consoleIssues.length || httpIssues.length) {
      throw new Error(JSON.stringify({ consoleIssues, httpIssues }, null, 2));
    }
    console.log(JSON.stringify({
      checks: {
        actionReferenceAdmin: true,
        actionMenu: true,
        atSearch: true,
        duplicateToggle: duplicateButtonVisible,
        layoutViewports: assistantViewports.map((viewport) => viewport.label),
        metricsDrilldown: true,
        runtimeStatus: true,
        stopCommand: true,
      },
      pageTitle: await evaluate('document.title'),
    }, null, 2));
  } finally {
    try {
      client?.close();
    } catch {
      // ignore cleanup failures
    }
    chrome.kill('SIGTERM');
    await sleep(200);
    fs.rmSync(userDataDir, { force: true, recursive: true });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack : error);
  process.exit(1);
});
