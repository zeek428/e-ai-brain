import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@ant-design/pro-components': '@ant-design/pro-components/es/index.js',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
  },
});
