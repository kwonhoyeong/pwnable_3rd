import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://query-api:8004',
        changeOrigin: true,
        secure: false,
        proxyTimeout: 120000, // 2 minutes
      },
    },
  },
});
