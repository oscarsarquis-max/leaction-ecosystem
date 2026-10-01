import { describe, expect, it } from 'vitest';
import { monitorEnvironmentBadge } from './monitorEnvironmentBadge';

describe('monitorEnvironmentBadge', () => {
  it('does not label a FORWARD list as MOCK or production', () => {
    const badge = monitorEnvironmentBadge({
      transaction: { origin: 'actionfinance', kind: 'SATELLITE' },
      events: [
        { eventType: 'CAPABILITY_DISPATCHED', metadata: { reasonCode: 'LIST_PAYMENT_TRANSACTIONS', environment: 'HOMOLOG' } },
        { eventType: 'OUTBOUND_REQUEST_STARTED', metadata: { providerId: 'actionhub-pay', edgeMode: 'FORWARD' } },
        { eventType: 'PROVIDER_RESULT_RECEIVED', metadata: { providerId: 'actionhub-pay', environment: 'HOMOLOG' } },
      ],
    });
    expect(badge.mock).toBe(false);
    expect(badge.label).toContain('DADOS HOMOLOG');
    expect(badge.label).toContain('PROVIDER FORWARD');
    expect(badge.label).not.toContain('MOCK');
    expect(badge.label).not.toMatch(/PRODU[CÇ][AÃ]O/i);
  });

  it('keeps MOCK only for canonical simulation', () => {
    const badge = monitorEnvironmentBadge({ transaction: { kind: 'CANONICAL' }, events: [] });
    expect(badge).toEqual({ label: 'AMBIENTE MOCK', mock: true });
  });
});
