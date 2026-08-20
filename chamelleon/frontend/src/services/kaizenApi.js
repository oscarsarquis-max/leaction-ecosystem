import { apiRequest } from './api';

export function fetchKaizenKanban({ operationalSiteId } = {}) {
  const params = new URLSearchParams({ kanban: '1' });
  if (operationalSiteId) params.set('operational_site_id', operationalSiteId);
  return apiRequest(`/kaizen/tickets?${params.toString()}`);
}

export function fetchKaizenTicket(ticketId) {
  return apiRequest(`/kaizen/tickets/${encodeURIComponent(ticketId)}`);
}

export function updateKaizenTicket(ticketId, payload) {
  return apiRequest(`/kaizen/tickets/${encodeURIComponent(ticketId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function saveKaizenFiveWhys(ticketId, payload) {
  return apiRequest(`/kaizen/tickets/${encodeURIComponent(ticketId)}/five-whys`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function escalateKaizenTicket(ticketId, payload) {
  return apiRequest(`/kaizen/tickets/${encodeURIComponent(ticketId)}/escalate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
