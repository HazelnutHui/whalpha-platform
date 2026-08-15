import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const runtime = globalThis as unknown as { process?: { env?: Record<string, string | undefined> } };

export default defineConfig({
  base: runtime.process?.env?.VITE_DASHBOARD_BASE ?? '/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
});
