export function monitorEnvironmentBadge({ events = [], transaction } = {}) {
  const list = Array.isArray(events) ? events : [];
  const outbound = [...list].reverse().find((event) => event?.eventType === 'OUTBOUND_REQUEST_STARTED');
  const provider = [...list].reverse().find((event) => event?.eventType === 'PROVIDER_RESULT_RECEIVED');
  const dispatched = [...list].reverse().find((event) => event?.eventType === 'CAPABILITY_DISPATCHED');
  const environment =
    provider?.metadata?.environment || outbound?.metadata?.environment || dispatched?.metadata?.environment;
  const providerId = provider?.metadata?.providerId || outbound?.metadata?.providerId;
  const mode = String(outbound?.metadata?.edgeMode || provider?.metadata?.edgeMode || outbound?.metadata?.mode || '').toUpperCase();
  const capability = dispatched?.metadata?.reasonCode;
  const observedForward = mode === 'FORWARD' || capability === 'LIST_PAYMENT_TRANSACTIONS' || providerId === 'actionhub-pay';
  if (observedForward) {
    const parts = [];
    if (environment) parts.push(`DADOS ${String(environment).toUpperCase()}`);
    parts.push(mode === 'SIMULATOR' ? 'PROVIDER SIMULADOR' : 'PROVIDER FORWARD');
    if (transaction?.origin) parts.push(`ORIGEM ${String(transaction.origin).toUpperCase()}`);
    return { label: parts.join(' · '), mock: false };
  }
  if (transaction?.kind === 'CANONICAL') {
    return { label: 'AMBIENTE MOCK', mock: true };
  }
  return { label: 'AMBIENTE NÃO AFIRMADO', mock: false };
}
