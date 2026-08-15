export class ApiClientError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'ApiClientError';
  }
}

const DEFAULT_TIMEOUT_MS = 45_000;

function combineSignals(primary: AbortSignal, secondary?: AbortSignal): AbortSignal {
  if (!secondary) {
    return primary;
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (primary.aborted || secondary.aborted) {
    controller.abort();
  } else {
    primary.addEventListener('abort', abort, { once: true });
    secondary.addEventListener('abort', abort, { once: true });
  }
  return controller.signal;
}

export async function fetchJson<T>(path: string, signal?: AbortSignal, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  if (!path.startsWith('/api/') && !path.startsWith('/private-data/')) {
    throw new ApiClientError('Invalid API path');
  }

  const timeout = new AbortController();
  const timer = window.setTimeout(() => timeout.abort(), timeoutMs);

  try {
    const response = await fetch(path, {
      headers: { Accept: 'application/json' },
      signal: combineSignals(timeout.signal, signal),
    });

    if (!response.ok) {
      throw new ApiClientError(`Request failed with status ${response.status}`, response.status);
    }

    const payload: unknown = await response.json();
    return payload as T;
  } catch (error: unknown) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiClientError('Request timed out or was cancelled');
    }
    throw new ApiClientError('Market data request failed');
  } finally {
    window.clearTimeout(timer);
  }
}
