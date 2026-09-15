import { afterEach, describe, expect, it, vi } from 'vitest';

import { recordGuestWorkspaceEntry } from './visitorCount';

describe('guest visitor count client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('records the protected workspace entry through the same-origin endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        metric: 'cumulative_guest_entries',
        count: 1051,
        counted: true,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(recordGuestWorkspaceEntry()).resolves.toEqual({
      metric: 'cumulative_guest_entries',
      count: 1051,
      counted: true,
    });
    expect(fetchMock).toHaveBeenCalledWith('/auth/visit', expect.objectContaining({
      method: 'POST',
      credentials: 'same-origin',
    }));
  });

  it('rejects a malformed or below-baseline response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        metric: 'cumulative_guest_entries',
        count: 1049,
        counted: true,
      }),
    }));

    await expect(recordGuestWorkspaceEntry()).rejects.toThrow('response is invalid');
  });
});
