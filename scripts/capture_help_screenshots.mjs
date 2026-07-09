#!/usr/bin/env node
import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const helpContentPath = path.join(repoRoot, 'apps/web/src/pages/Help/helpContent.ts');

const FALLBACK_TARGETS = [
  {
    name: 'system-health-overview',
    route: '/system/health',
  },
  {
    name: 'assets-products-onboarding',
    route: '/assets/products',
  },
];

function uniqueTargets(targets) {
  const seen = new Set();
  const unique = [];
  for (const target of targets) {
    const key = `${target.route}:${target.name}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(target);
  }
  return unique;
}

function targetsFromHelpContent() {
  const source = readFileSync(helpContentPath, 'utf8');
  const targets = [];
  let currentRoute = '';
  for (const line of source.split(/\r?\n/)) {
    const routeMatch = /route:\s*'([^']+)'/.exec(line);
    if (routeMatch) {
      currentRoute = routeMatch[1];
    }
    const screenshotMatch = /src:\s*'\/help\/screenshots\/([^']+\.png)'/.exec(line);
    if (screenshotMatch && currentRoute) {
      targets.push({
        name: path.basename(screenshotMatch[1], '.png'),
        route: currentRoute,
      });
    }
  }
  return uniqueTargets(targets);
}

function parseArgs(argv) {
  const options = {
    apiBaseUrl: process.env.READINESS_API_BASE_URL || 'http://localhost:8000',
    bearerToken: process.env.READINESS_BEARER_TOKEN || '',
    listTargets: false,
    password: process.env.READINESS_PASSWORD || '',
    targets: [],
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
    } else if (arg === '--list-targets') {
      options.listTargets = true;
    } else if (arg === '--password') {
      options.password = next();
    } else if (arg === '--route') {
      const [route, name] = next().split('=');
      if (!route || !name) {
        throw new Error('--route must use /path=name');
      }
      options.targets.push({ name, route });
    } else if (arg === '--username') {
      options.username = next();
    } else if (arg === '--web-base-url') {
      options.webBaseUrl = next();
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  if (!options.targets.length) {
    options.targets = targetsFromHelpContent();
  }
  if (!options.targets.length) {
    options.targets = FALLBACK_TARGETS;
  }
  return options;
}

function printHelp() {
  console.log(`Capture AI Brain help screenshots

Usage:
  node scripts/capture_help_screenshots.mjs --web-base-url http://localhost:5173 --api-base-url http://localhost:8000

Options:
  --route /path=name       Capture an extra route to name.png. Can be repeated.
  --bearer-token TOKEN     Seed localStorage with an existing API token. Defaults to READINESS_BEARER_TOKEN.
  --list-targets           Print derived screenshot targets without launching Playwright.
  --username USER          Login username. Defaults to READINESS_USERNAME.
  --password PASSWORD      Login password. Defaults to READINESS_PASSWORD.
`);
}

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch (error) {
    throw new Error(
      'Playwright is required for screenshot capture. Install it in the web workspace before running this script.',
    );
  }
}

async function loginIfNeeded(page, options) {
  if (options.bearerToken) {
    return;
  }
  await page.goto(`${options.webBaseUrl}/login`, { waitUntil: 'networkidle' });
  if (!options.username || !options.password) {
    return;
  }
  const username = page.locator('input').first();
  const password = page.locator('input[type="password"]').first();
  if ((await username.count()) > 0 && (await password.count()) > 0) {
    await username.fill(options.username);
    await password.fill(options.password);
    const challenge = page.locator('input').filter({ hasText: /\d+/ }).last();
    if ((await challenge.count()) > 0) {
      await challenge.fill('0');
    }
    await page.getByRole('button').filter({ hasText: /登录|Sign in/i }).first().click();
    await page.waitForLoadState('networkidle');
  }
}

async function seedBearerToken(page, token) {
  if (!token) {
    return;
  }
  await page.addInitScript((accessToken) => {
    window.localStorage.setItem('ai_brain_access_token', accessToken);
    window.localStorage.setItem(
      'ai_brain_current_user',
      JSON.stringify({
        id: 'help_screenshot_admin',
        roles: ['admin'],
        username: 'help-screenshot-admin',
      }),
    );
  }, token);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  if (options.listTargets) {
    for (const target of options.targets) {
      console.log(`${target.route}=${target.name}`);
    }
    return;
  }
  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { height: 1000, width: 1440 } });
  await seedBearerToken(page, options.bearerToken);
  await loginIfNeeded(page, options);
  const publicDir = path.join(repoRoot, 'apps/web/public/help/screenshots');
  const docsDir = path.join(repoRoot, 'docs/08-help/assets/screenshots');
  mkdirSync(publicDir, { recursive: true });
  mkdirSync(docsDir, { recursive: true });
  for (const target of options.targets) {
    const fileName = `${target.name}.png`;
    const publicPath = path.join(publicDir, fileName);
    const docsPath = path.join(docsDir, fileName);
    await page.goto(`${options.webBaseUrl}${target.route}`, { waitUntil: 'networkidle' });
    if (new URL(page.url()).pathname.startsWith('/login')) {
      throw new Error(
        `Route ${target.route} redirected to login. Provide --bearer-token or READINESS_BEARER_TOKEN.`,
      );
    }
    await page.screenshot({ fullPage: true, path: publicPath });
    copyFileSync(publicPath, docsPath);
    console.log(`Captured ${target.route} -> ${path.relative(repoRoot, publicPath)}`);
  }
  await browser.close();
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
