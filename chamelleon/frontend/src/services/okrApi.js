import { apiRequest } from './api';

export function fetchOkrDashboard() {
  return apiRequest('/okr/dashboard');
}

export function seedOkrs() {
  return apiRequest('/okr/seed', { method: 'POST' });
}

export function createOkrDriver(payload) {
  return apiRequest('/okr/drivers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function createOkrObjective(payload) {
  return apiRequest('/okr/objectives', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function createOkrKeyResult(payload) {
  return apiRequest('/okr/key-results', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateOkrKeyResult(krId, payload) {
  return apiRequest(`/okr/key-results/${encodeURIComponent(krId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function createOkrKpi(payload) {
  return apiRequest('/okr/kpis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateOkrKpi(kpiId, payload) {
  return apiRequest(`/okr/kpis/${encodeURIComponent(kpiId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
