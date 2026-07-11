import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@ant-design/pro-components': '@ant-design/pro-components/es/index.js',
    },
  },
  test: {
    environment: 'jsdom',
    maxWorkers: 4,
    minWorkers: 1,
    setupFiles: './tests/setup.ts',
  },
});
