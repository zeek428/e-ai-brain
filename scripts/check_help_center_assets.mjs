#!/usr/bin/env node
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const helpContentPath = path.join(repoRoot, 'apps/web/src/pages/Help/helpContent.ts');
const routesPath = path.join(repoRoot, 'apps/web/config/routes.ts');
const docsHelpDir = path.join(repoRoot, 'docs/08-help');
const publicScreenshotsDir = path.join(repoRoot, 'apps/web/public/help/screenshots');
const docsScreenshotsDir = path.join(repoRoot, 'docs/08-help/assets/screenshots');

function envFlag(name) {
  return ['1', 'true', 'yes'].includes(String(process.env[name] || '').toLowerCase());
}

function parseArgs(argv) {
  const options = {
    json: false,
    maxAgeDays: Number(process.env.HELP_SCREENSHOT_REFRESH_DAYS || 30),
    strictScreenshots: envFlag('HELP_STRICT_SCREENSHOTS'),
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
    if (arg === '--json') {
      options.json = true;
    } else if (arg === '--strict-screenshots') {
      options.strictScreenshots = true;
    } else if (arg === '--max-age-days') {
      options.maxAgeDays = Number(next());
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  if (!Number.isFinite(options.maxAgeDays) || options.maxAgeDays < 0) {
    throw new Error('--max-age-days must be a non-negative number');
  }
  return options;
}

function printHelp() {
  console.log(`AI Brain help center asset check

Usage:
  node scripts/check_help_center_assets.mjs

Options:
  --strict-screenshots  Treat help routes without screenshot targets as failures.
                        Can also be enabled with HELP_STRICT_SCREENSHOTS=true.
  --max-age-days DAYS   Override screenshot staleness threshold. Defaults to
                        HELP_SCREENSHOT_REFRESH_DAYS or 30.
  --json                Print a machine-readable check report.
`);
}

function extractStringValues(source, key) {
  const pattern = new RegExp(`${key}:\\s*'([^']+)'`, 'g');
  const values = [];
  let match;
  while ((match = pattern.exec(source))) {
    values.push(match[1]);
  }
  return values;
}

function normalizeRoute(route) {
  const value = String(route || '').trim();
  if (!value) {
    return '/';
  }
  return value.startsWith('/') ? value : `/${value}`;
}

function screenshotPathFromSrc(src) {
  const normalized = String(src || '').replace(/^\/+/, '');
  return path.join(repoRoot, 'apps/web/public', normalized);
}

function docsScreenshotPathFromSrc(src) {
  const filename = path.basename(src);
  return path.join(docsScreenshotsDir, filename);
}

function daysSince(mtimeMs) {
  return Math.floor((Date.now() - mtimeMs) / 86400000);
}

function listMarkdownFiles(directory) {
  const entries = readdirSync(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'assets') {
        continue;
      }
      files.push(...listMarkdownFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      files.push(fullPath);
    }
  }
  return files;
}

function extractMarkdownScreenshotRefs() {
  const refs = [];
  const pattern = /!\[[^\]]*\]\((assets\/screenshots\/[^)\s]+)\)/g;
  for (const filePath of listMarkdownFiles(docsHelpDir)) {
    const source = readFileSync(filePath, 'utf8');
    let match;
    while ((match = pattern.exec(source))) {
      refs.push({
        filename: path.basename(match[1]),
        source: path.relative(repoRoot, filePath),
      });
    }
  }
  return refs;
}

function listPngFiles(directory) {
  if (!existsSync(directory)) {
    return [];
  }
  return readdirSync(directory)
    .filter((name) => name.endsWith('.png'))
    .sort();
}

function filesDiffer(leftPath, rightPath) {
  return readFileSync(leftPath).compare(readFileSync(rightPath)) !== 0;
}

function screenshotRoutesFromHelpContent(source) {
  const routes = new Set();
  let currentRoute = '';
  for (const line of source.split(/\r?\n/)) {
    const routeMatch = /route:\s*'([^']+)'/.exec(line);
    if (routeMatch) {
      currentRoute = normalizeRoute(routeMatch[1]);
    }
    const screenshotMatch = /src:\s*'\/help\/screenshots\/([^']+\.png)'/.exec(line);
    if (screenshotMatch && currentRoute) {
      routes.add(currentRoute);
    }
  }
  return routes;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  const helpContent = readFileSync(helpContentPath, 'utf8');
  const routesContent = readFileSync(routesPath, 'utf8');
  const declaredRoutes = new Set(extractStringValues(routesContent, 'path').map(normalizeRoute));
  const helpRoutes = extractStringValues(helpContent, 'route').map(normalizeRoute);
  const uniqueHelpRoutes = [...new Set(helpRoutes)];
  const screenshotRoutes = screenshotRoutesFromHelpContent(helpContent);
  const screenshots = extractStringValues(helpContent, 'src');
  const markdownScreenshotRefs = extractMarkdownScreenshotRefs();
  const markdownScreenshotFilenames = new Set(markdownScreenshotRefs.map((ref) => ref.filename));
  const frontendScreenshotFilenames = new Set(screenshots.map((src) => path.basename(src)));
  const referencedScreenshotFilenames = new Set([
    ...frontendScreenshotFilenames,
    ...markdownScreenshotFilenames,
  ]);
  const failures = [];
  const warnings = [];

  for (const route of helpRoutes) {
    if (!declaredRoutes.has(route)) {
      failures.push(`帮助文档引用了未注册路由：${route}`);
    }
  }

  const routesMissingScreenshots = uniqueHelpRoutes.filter((route) => !screenshotRoutes.has(route));
  for (const route of routesMissingScreenshots) {
    const message = `帮助路由未配置截图目标：${route}`;
    if (options.strictScreenshots) {
      failures.push(message);
    } else {
      warnings.push(message);
    }
  }

  for (const src of screenshots) {
    const publicPath = screenshotPathFromSrc(src);
    const docsPath = docsScreenshotPathFromSrc(src);
    if (!existsSync(publicPath)) {
      failures.push(`缺少前端帮助截图：${path.relative(repoRoot, publicPath)}`);
      continue;
    }
    if (!existsSync(docsPath)) {
      failures.push(`缺少文档帮助截图：${path.relative(repoRoot, docsPath)}`);
      continue;
    }
    if (filesDiffer(publicPath, docsPath)) {
      failures.push(`前端与文档帮助截图不一致：${path.basename(src)}`);
    }
    const newestMtime = Math.max(statSync(publicPath).mtimeMs, statSync(docsPath).mtimeMs);
    const ageDays = daysSince(newestMtime);
    if (ageDays > options.maxAgeDays) {
      warnings.push(
        `截图可能过期：${path.basename(src)} 已 ${ageDays} 天未刷新，阈值 ${options.maxAgeDays} 天`,
      );
    }
  }

  for (const ref of markdownScreenshotRefs) {
    const docsPath = path.join(docsScreenshotsDir, ref.filename);
    const publicPath = path.join(publicScreenshotsDir, ref.filename);
    if (!existsSync(docsPath)) {
      failures.push(`Markdown 引用了缺失截图：${ref.source} -> ${ref.filename}`);
    }
    if (!existsSync(publicPath)) {
      failures.push(`Markdown 截图缺少前端 public 副本：${ref.filename}`);
    }
    if (!frontendScreenshotFilenames.has(ref.filename)) {
      warnings.push(`Markdown 截图未在前端帮助中心展示：${ref.filename}`);
    }
  }

  for (const filename of new Set([...listPngFiles(publicScreenshotsDir), ...listPngFiles(docsScreenshotsDir)])) {
    if (!referencedScreenshotFilenames.has(filename)) {
      warnings.push(`帮助截图未被前端或 Markdown 引用：${filename}`);
    }
  }

  const report = {
    counts: {
      docs_screenshot_refs: markdownScreenshotRefs.length,
      frontend_screenshot_refs: screenshots.length,
      help_routes: uniqueHelpRoutes.length,
      help_routes_with_screenshots: screenshotRoutes.size,
      help_routes_without_screenshots: routesMissingScreenshots.length,
    },
    failures,
    options: {
      max_age_days: options.maxAgeDays,
      strict_screenshots: options.strictScreenshots,
    },
    routes_without_screenshots: routesMissingScreenshots,
    status: failures.length ? 'failed' : 'passed',
    warnings,
  };
  if (options.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    for (const warning of warnings) {
      console.warn(`WARN ${warning}`);
    }
  }
  if (failures.length) {
    if (!options.json) {
      for (const failure of failures) {
        console.error(`FAIL ${failure}`);
      }
    }
    process.exit(1);
  }
  if (!options.json) {
    console.log(
      `OK 帮助中心检查通过：${uniqueHelpRoutes.length} 个路由、${screenshots.length} 张前端截图、${markdownScreenshotRefs.length} 张 Markdown 截图，截图覆盖 ${screenshotRoutes.size}/${uniqueHelpRoutes.length}，提醒 ${warnings.length} 条。`,
    );
  }
}

main();
