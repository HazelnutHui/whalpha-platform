export type GuestVisitorCount = {
  metric: 'cumulative_guest_entries';
  count: number;
  counted: boolean;
};

export async function recordGuestWorkspaceEntry(
  signal?: AbortSignal,
): Promise<GuestVisitorCount> {
  const response = await fetch('/auth/visit', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) throw new Error('Guest visitor count is unavailable');
  const payload: unknown = await response.json();
  if (!isGuestVisitorCount(payload)) {
    throw new Error('Guest visitor count response is invalid');
  }
  return payload;
}

function isGuestVisitorCount(value: unknown): value is GuestVisitorCount {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  return (
    payload.metric === 'cumulative_guest_entries'
    && Number.isSafeInteger(payload.count)
    && Number(payload.count) >= 1050
    && typeof payload.counted === 'boolean'
  );
}
