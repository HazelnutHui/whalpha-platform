import type { HealthResponse } from '../types/health';

type ApiState =
  | { kind: 'loading' }
  | { kind: 'available'; health: HealthResponse }
  | { kind: 'unavailable'; message: string };

interface SystemStatusProps {
  apiState: ApiState;
}

function apiStatusText(apiState: ApiState): string {
  if (apiState.kind === 'loading') {
    return 'Connecting';
  }
  if (apiState.kind === 'available') {
    return `Available (${apiState.health.version})`;
  }
  return 'Unavailable';
}

export function SystemStatus({ apiState }: SystemStatusProps): JSX.Element {
  return (
    <section className="status-panel" aria-labelledby="system-status-title">
      <div className="section-heading">
        <p className="eyebrow">System Status</p>
        <h2 id="system-status-title">Development scaffold</h2>
      </div>

      <dl className="status-grid">
        <div className="status-item status-ready">
          <dt>Frontend</dt>
          <dd>Ready</dd>
        </div>
        <div className={`status-item status-${apiState.kind}`}>
          <dt>API</dt>
          <dd>{apiStatusText(apiState)}</dd>
        </div>
        <div className="status-item status-muted">
          <dt>Data Provider</dt>
          <dd>Not Configured</dd>
        </div>
        <div className="status-item status-muted">
          <dt>Market Data</dt>
          <dd>Not Loaded</dd>
        </div>
        <div className="status-item status-local">
          <dt>Deployment</dt>
          <dd>Local Development</dd>
        </div>
      </dl>

      {apiState.kind === 'unavailable' ? (
        <p className="status-note" role="status">
          API check failed: {apiState.message}
        </p>
      ) : null}
    </section>
  );
}
