import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  CORRELATION_HEADER,
  fetchSystemInfo,
  parseSystemInfo,
} from './systemInfo';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('systemInfo', () => {
  it('reads applicationId from a valid payload', () => {
    expect(
      parseSystemInfo({
        name: 'SegSense',
        version: '0.1.0',
        applicationId: 'SEGSENSE',
        operationalState: 'UP',
      }),
    ).toEqual({
      name: 'SegSense',
      version: '0.1.0',
      applicationId: 'SEGSENSE',
      operationalState: 'UP',
    });
  });

  it('rejects a payload without applicationId', () => {
    expect(() =>
      parseSystemInfo({
        name: 'SegSense',
        version: '0.1.0',
        operationalState: 'UP',
      }),
    ).toThrow('invalid payload');
  });

  it('sends a UUID in X-Correlation-ID for each technical call', async () => {
    let sentCorrelationId = '';
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      sentCorrelationId = headers.get(CORRELATION_HEADER) ?? '';
      return Promise.resolve(
        new Response(
          JSON.stringify({
            name: 'SegSense',
            version: '0.1.0',
            applicationId: 'SEGSENSE',
            operationalState: 'UP',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await fetchSystemInfo('http://127.0.0.1:8088');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(sentCorrelationId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
});
