#!/usr/bin/env node
import { mkdirSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const DEFAULT_TARGETS = [
  {
    name: 'system-health-overview',
    route: '/system/health',
  },
  {
    name: 'assets-products-onboarding',
    route: '/assets/products',
  },
];

function parseArgs(argv) {
  const options = {
    apiBaseUrl: process.env.READINESS_API_BASE_URL || 'http://localhost:8000',
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
    options.targets = DEFAULT_TARGETS;
  }
  return options;
}

function printHelp() {
  console.log(`Capture AI Brain help screenshots

Usage:
  node scripts/capture_help_screenshots.mjs --web-base-url http://localhost:5173 --api-base-url http://localhost:8000

Options:
  --route /path=name       Capture an extra route to name.png. Can be repeated.
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

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { height: 1000, width: 1440 } });
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
