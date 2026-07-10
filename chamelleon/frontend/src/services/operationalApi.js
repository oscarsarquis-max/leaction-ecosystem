import { apiRequest } from './api';

export function listOperationalSites() {
  return apiRequest('/operational/sites');
}

export function createOperationalSite(payload) {
  return apiRequest('/operational/sites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateOperationalSite(siteId, payload) {
  return apiRequest(`/operational/sites/${siteId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function deleteOperationalSite(siteId) {
  return apiRequest(`/operational/sites/${siteId}`, { method: 'DELETE' });
}

export function syncOperationalSiteSatellite(siteId) {
  return apiRequest(`/operational/sites/${siteId}/sync-satellite`, { method: 'POST' });
}

export function listOperationalUsers() {
  return apiRequest('/operational/users');
}

export function createOperationalUser(payload) {
  return apiRequest('/operational/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateOperationalUser(userId, payload) {
  return apiRequest(`/operational/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function regenerateOperationalUserCode(userId) {
  return apiRequest(`/operational/users/${userId}/regenerate-code`, { method: 'POST' });
}

export function getPlanningWeekDates(referenceDate) {
  const query = referenceDate ? `?date=${encodeURIComponent(referenceDate)}` : '';
  return apiRequest(`/operational/planning/week-dates${query}`);
}

export function pushWeeklyGoals(payload) {
  return apiRequest('/operational/planning/weekly-goals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function listOperationalReports(date) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiRequest(`/operational/reports${query}`);
}

export function getOperationalReportsSummary({ startDate, endDate, siteId } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  if (siteId) params.set('site_id', siteId);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/operational/reports/summary${query}`);
}

export function reopenOperationalDay({ siteId, date }) {
  return apiRequest('/operational/reports/reopen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ site_id: siteId, date }),
  });
}
