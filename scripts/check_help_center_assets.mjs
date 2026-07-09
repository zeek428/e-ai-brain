#!/usr/bin/env node
import { existsSync, statSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const helpContentPath = path.join(repoRoot, 'apps/web/src/pages/Help/helpContent.ts');
const routesPath = path.join(repoRoot, 'apps/web/config/routes.ts');
const maxAgeDays = Number(process.env.HELP_SCREENSHOT_REFRESH_DAYS || 30);

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
  return path.join(repoRoot, 'docs/08-help/assets/screenshots', filename);
}

function daysSince(mtimeMs) {
  return Math.floor((Date.now() - mtimeMs) / 86400000);
}

function main() {
  const helpContent = readFileSync(helpContentPath, 'utf8');
  const routesContent = readFileSync(routesPath, 'utf8');
  const declaredRoutes = new Set(extractStringValues(routesContent, 'path').map(normalizeRoute));
  const helpRoutes = extractStringValues(helpContent, 'route').map(normalizeRoute);
  const screenshots = extractStringValues(helpContent, 'src');
  const failures = [];
  const warnings = [];

  for (const route of helpRoutes) {
    if (!declaredRoutes.has(route)) {
      failures.push(`帮助文档引用了未注册路由：${route}`);
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
    const newestMtime = Math.max(statSync(publicPath).mtimeMs, statSync(docsPath).mtimeMs);
    const ageDays = daysSince(newestMtime);
    if (ageDays > maxAgeDays) {
      warnings.push(
        `截图可能过期：${path.basename(src)} 已 ${ageDays} 天未刷新，阈值 ${maxAgeDays} 天`,
      );
    }
  }

  for (const warning of warnings) {
    console.warn(`WARN ${warning}`);
  }
  if (failures.length) {
    for (const failure of failures) {
      console.error(`FAIL ${failure}`);
    }
    process.exit(1);
  }
  console.log(
    `OK 帮助中心检查通过：${helpRoutes.length} 个路由、${screenshots.length} 张截图，过期提醒 ${warnings.length} 条。`,
  );
}

main();
