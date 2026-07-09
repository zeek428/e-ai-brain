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

function main() {
  const helpContent = readFileSync(helpContentPath, 'utf8');
  const routesContent = readFileSync(routesPath, 'utf8');
  const declaredRoutes = new Set(extractStringValues(routesContent, 'path').map(normalizeRoute));
  const helpRoutes = extractStringValues(helpContent, 'route').map(normalizeRoute);
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
    if (ageDays > maxAgeDays) {
      warnings.push(
        `截图可能过期：${path.basename(src)} 已 ${ageDays} 天未刷新，阈值 ${maxAgeDays} 天`,
      );
    }
    if (!markdownScreenshotFilenames.has(path.basename(src))) {
      warnings.push(`前端截图未被 Markdown 手册引用：${path.basename(src)}`);
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
    `OK 帮助中心检查通过：${helpRoutes.length} 个路由、${screenshots.length} 张前端截图、${markdownScreenshotRefs.length} 张 Markdown 截图，提醒 ${warnings.length} 条。`,
  );
}

main();
