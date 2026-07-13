import { expect, it } from 'vitest';

import { runnerDefaultPackageArch } from '../src/pages/Plugins/components/pluginRunnerHelpers';

it('recommends the correct package architecture for each Runner target system', () => {
  expect(runnerDefaultPackageArch('linux')).toBe('amd64');
  expect(runnerDefaultPackageArch('macos')).toBe('arm64');
  expect(runnerDefaultPackageArch('windows')).toBe('amd64');
  expect(runnerDefaultPackageArch('manual')).toBe('universal');
});
