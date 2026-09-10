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

const bundleBudgets = {
  entryJavaScriptBytes: 350 * 1024,
  asyncJavaScriptBytes: 550 * 1024,
  stylesheetBytes: 130 * 1024,
} as const;

function enforceFrontendBundleBudgets(): Plugin {
  return {
    name: 'enforce-frontend-bundle-budgets',
    apply: 'build',
    generateBundle(_options, bundle) {
      for (const fileName in bundle) {
        const output = bundle[fileName];
        if (output.type === 'chunk') {
          const byteLength = new TextEncoder().encode(output.code).byteLength;
          const budget = output.isEntry
            ? bundleBudgets.entryJavaScriptBytes
            : bundleBudgets.asyncJavaScriptBytes;
          if (byteLength > budget) {
            this.error(`Bundle ${output.fileName} is ${byteLength} bytes; budget is ${budget}`);
          }
          continue;
        }
        if (output.fileName.slice(-4) !== '.css') continue;
        const byteLength = typeof output.source === 'string' ? new TextEncoder().encode(output.source).byteLength : output.source.byteLength;
        if (byteLength > bundleBudgets.stylesheetBytes) {
          this.error(`Stylesheet ${output.fileName} is ${byteLength} bytes; budget is ${bundleBudgets.stylesheetBytes}`);
        }
      }
    },
  };
}

export default defineConfig({
  base: runtime.process?.env?.VITE_DASHBOARD_BASE ?? '/',
  plugins: [react(), rejectBundledDashboardDemoData(), enforceFrontendBundleBudgets()],
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
