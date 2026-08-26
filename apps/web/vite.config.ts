import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

const runtime = globalThis as unknown as { process?: { env?: Record<string, string | undefined> } };

const forbiddenProductionDemoMarkers = [
  'synthetic_demo_fixture',
  'synthetic_demo',
  'demoDashboardData',
] as const;

function rejectBundledDashboardDemoData(): Plugin {
  return {
    name: 'reject-bundled-dashboard-demo-data',
    apply: 'build',
    generateBundle(_options, bundle) {
      for (const fileName in bundle) {
        const output = bundle[fileName];
        const content = output.type === 'chunk'
          ? output.code
          : typeof output.source === 'string'
            ? output.source
            : new TextDecoder().decode(output.source);
        for (const marker of forbiddenProductionDemoMarkers) {
          if (content.indexOf(marker) !== -1) {
            this.error(`Production bundle artifact ${fileName} contains forbidden Dashboard demo marker ${marker}`);
          }
        }
      }
    },
  };
}

export default defineConfig({
  base: runtime.process?.env?.VITE_DASHBOARD_BASE ?? '/',
  plugins: [react(), rejectBundledDashboardDemoData()],
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
