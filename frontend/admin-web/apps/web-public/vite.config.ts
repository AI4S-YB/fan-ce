import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  server: {
    host: '127.0.0.1',
    port: 5677,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
});
