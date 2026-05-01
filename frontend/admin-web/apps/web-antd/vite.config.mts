import path from 'node:path';

import { defineConfig } from '@vben/vite-config';

import { createSvgIconsPlugin } from 'vite-plugin-svg-icons';

export default defineConfig(async () => {
  return {
    application: {
      printInfoMap: {
        'FAN-CE API Docs': 'http://127.0.0.1:8001/docs',
      },
    },
    vite: {
      plugins: [
        createSvgIconsPlugin({
          // 指定需要缓存的图标文件夹
          // eslint-disable-next-line n/prefer-global/process
          iconDirs: [path.resolve(process.cwd(), 'src/assets/svg')],
          // 指定symbolId格式
          symbolId: 'icons-[name]',
        }),
      ],
      server: {
        host: '127.0.0.1',
        port: 5666,
        strictPort: true,
        proxy: {
          '/api/v1': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api\/v1/, ''),
            // mock代理目标地址
            target: 'http://127.0.0.1:8001/api/v1',
            ws: true,
          },
          '/docs': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8001',
          },
          '/redoc': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8001',
          },
          '/openapi.json': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8001',
          },
          '/static/swagger-ui': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8001',
          },
          '/static/templates': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8001',
          },
        },
      },
    },
  };
});
