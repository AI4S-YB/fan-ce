import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      // Force JBrowse 2 to use our React instance (prevent dual-React hook errors)
      'react': resolve(__dirname, 'node_modules/react'),
      'react-dom': resolve(__dirname, 'node_modules/react-dom'),
      'react-dom/server': resolve(__dirname, 'src/shim/react-dom-server.js'),
    },
  },
  server: {
    port: 5677,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
});
