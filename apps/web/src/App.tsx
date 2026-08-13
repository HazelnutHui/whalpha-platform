import { useEffect, useState } from 'react';

import { getHealth } from './api/health';
import { SystemStatus } from './components/SystemStatus';
import type { HealthResponse } from './types/health';

type ApiState =
  | { kind: 'loading' }
  | { kind: 'available'; health: HealthResponse }
  | { kind: 'unavailable'; message: string };

export default function App(): JSX.Element {
  const [apiState, setApiState] = useState<ApiState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((health) => {
        setApiState({ kind: 'available', health });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unknown API error';
        setApiState({ kind: 'unavailable', message });
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <div>
          <p className="brand">WH Alpha</p>
          <h1 id="page-title">Trading Intelligence Platform</h1>
          <p className="subtitle">Development Foundation</p>
        </div>
        <p className="summary">
          A workstation-driven market structure analysis platform for U.S. equities.
        </p>
      </section>

      <SystemStatus apiState={apiState} />

      <section className="boundary-panel" aria-labelledby="boundary-title">
        <p className="eyebrow">Current Boundary</p>
        <h2 id="boundary-title">Scaffold only</h2>
        <p>
          This page verifies the frontend boundary and the versioned Health API contract. Real market data,
          provider adapters, analytics pipelines, Dashboard V1 views, and production deployment are not yet implemented.
        </p>
      </section>
    </main>
  );
}
