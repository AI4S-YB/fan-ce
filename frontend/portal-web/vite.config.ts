import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
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
