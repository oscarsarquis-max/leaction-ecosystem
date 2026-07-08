import { apiRequest } from './api';

export function fetchKaizenKanban() {
  return apiRequest('/kaizen/tickets?kanban=1');
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
