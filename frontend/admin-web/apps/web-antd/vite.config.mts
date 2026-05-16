import path from 'node:path';

import { defineConfig } from '@vben/vite-config';

import { createSvgIconsPlugin } from 'vite-plugin-svg-icons';

export default defineConfig(async () => {
  return {
    application: {
      printInfoMap: {
        'FAN-CE API Docs': 'http://127.0.0.1:8002/docs',
      },
    },
    vite: {
      plugins: [
        // Shm jiti — Node.js runtime pulled into browser bundle transitively.
        // Must intercept at resolution time to prevent Rollup bundling failure.
        {
          name: 'fance:shim-jiti',
          enforce: 'pre',
          resolveId(id) {
            if (id === 'jiti' || id.startsWith('jiti/') || id.includes('/jiti/')) {
              return path.resolve(import.meta.dirname, 'stubs/jiti-stub.mjs');
            }
          },
        },
        createSvgIconsPlugin({
          // 指定需要缓存的图标文件夹
          // eslint-disable-next-line n/prefer-global/process
          iconDirs: [path.resolve(process.cwd(), 'src/assets/svg')],
          // 指定symbolId格式
          symbolId: 'icons-[name]',
        }),
      ],
      server: {
        port: 5666,
        strictPort: true,
        proxy: {
          '/api/v1': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api\/v1/, ''),
            // mock代理目标地址
            target: 'http://127.0.0.1:8002/api/v1',
            ws: true,
          },
          '/docs': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8002',
          },
          '/redoc': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8002',
          },
          '/openapi.json': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8002',
          },
          '/static/swagger-ui': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8002',
          },
          '/static/templates': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8002',
          },
        },
      },
    },
  };
});
