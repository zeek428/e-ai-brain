import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

const projectRoot = join(__dirname, '..');

function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, 'utf8')) as T;
}

describe('Ant Design Pro framework guard', () => {
  it('keeps apps/web on Umi Max and ProComponents instead of a Vite shell', () => {
    const packageJson = readJson<{
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
      scripts?: Record<string, string>;
    }>(join(projectRoot, 'package.json'));

    expect({
      ...packageJson.dependencies,
      ...packageJson.devDependencies,
    }).toHaveProperty('@umijs/max');
    expect(packageJson.dependencies).toHaveProperty('@ant-design/pro-components');
    expect(packageJson.scripts?.dev).toContain('max dev');
    expect(packageJson.scripts?.build).toContain('max build');
    expect(packageJson.devDependencies).not.toHaveProperty('vite');
    expect(existsSync(join(projectRoot, '.umirc.ts'))).toBe(true);
    expect(existsSync(join(projectRoot, 'src', 'app.tsx'))).toBe(true);
    expect(existsSync(join(projectRoot, 'vite.config.ts'))).toBe(false);

    const appRuntime = readFileSync(join(projectRoot, 'src', 'app.tsx'), 'utf8');
    expect(appRuntime).toContain("layout: 'mix'");
    expect(appRuntime).toContain('navTheme: \'light\'');
    expect(appRuntime).toContain('siderWidth: 256');
    expect(appRuntime).toContain('splitMenus: false');
  });
});
