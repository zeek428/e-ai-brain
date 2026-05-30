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
  request: {},
  routes,
  title: 'AI Brain',
});
