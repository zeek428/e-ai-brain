import { defineConfig } from '@umijs/max';

import routes from './config/routes';

export default defineConfig({
  antd: {},
  esbuildMinifyIIFE: true,
  hash: true,
  history: {
    type: 'browser',
  },
  initialState: {},
  layout: {
    locale: false,
  },
  model: {},
  npmClient: 'npm',
  proxy: {
    '/api': {
      changeOrigin: true,
      target: 'http://localhost:8000',
    },
  },
  request: {},
  routes,
  title: 'AI Brain',
});
