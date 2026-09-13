import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ACCESS_DENIED,
  AUTHENTICATION_REQUIRED,
  parseApiError,
  readApiError,
} from './errors';
import { fetchSystemInfo } from './systemInfo';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('api errors', () => {
  it('distinguishes 401 from 403 using a real-shaped payload', () => {
    const unauthorized = parseApiError(401, {
      code: AUTHENTICATION_REQUIRED,
      message: 'Autenticação necessária.',
      timestamp: '2026-09-04T12:00:00Z',
      correlationId: '11111111-1111-4111-8111-111111111111',
    });
    expect(unauthorized.authenticationRequired).toBe(true);
    expect(unauthorized.accessDenied).toBe(false);
    expect(unauthorized.correlationId).toBe('11111111-1111-4111-8111-111111111111');

    const forbidden = parseApiError(403, {
      code: ACCESS_DENIED,
      message: 'Acesso não autorizado para esta operação.',
      timestamp: '2026-09-04T12:00:00Z',
      correlationId: '22222222-2222-4222-8222-222222222222',
    });
    expect(forbidden.accessDenied).toBe(true);
    expect(forbidden.authenticationRequired).toBe(false);
  });

  it('surfaces 401 from fetchSystemInfo without storing a token', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              code: AUTHENTICATION_REQUIRED,
              message: 'Autenticação necessária.',
              timestamp: '2026-09-04T12:00:00Z',
              correlationId: '33333333-3333-4333-8333-333333333333',
            }),
            { status: 401, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );

    await expect(fetchSystemInfo('http://127.0.0.1:8088')).rejects.toMatchObject({
      status: 401,
      code: AUTHENTICATION_REQUIRED,
      authenticationRequired: true,
    });
  });

  it('reads 403 bodies through readApiError', async () => {
    const error = await readApiError(
      new Response(
        JSON.stringify({
          code: ACCESS_DENIED,
          message: 'Acesso não autorizado para esta operação.',
          timestamp: '2026-09-04T12:00:00Z',
          correlationId: '44444444-4444-4444-8444-444444444444',
        }),
        { status: 403, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    expect(error.accessDenied).toBe(true);
    expect(error.code).toBe(ACCESS_DENIED);
  });
});
