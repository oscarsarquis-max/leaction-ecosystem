import { apiRequest } from './api';

export function listTrainingRecords(professionalId) {
  const q = new URLSearchParams({ professional_id: professionalId });
  return apiRequest(`/compliance/training-records?${q}`);
}

export function createTrainingRecord(payload) {
  return apiRequest('/compliance/training-records', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateTrainingRecord(id, payload) {
  return apiRequest(`/compliance/training-records/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteTrainingRecord(id) {
  return apiRequest(`/compliance/training-records/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function listHealthRecords(professionalId) {
  const q = new URLSearchParams({ professional_id: professionalId });
  return apiRequest(`/compliance/health-records?${q}`);
}

export function createHealthRecord(payload) {
  return apiRequest('/compliance/health-records', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateHealthRecord(id, payload) {
  return apiRequest(`/compliance/health-records/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteHealthRecord(id) {
  return apiRequest(`/compliance/health-records/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function getSiteComplianceStatus(siteId) {
  return apiRequest(`/compliance/sites/${encodeURIComponent(siteId)}/status`);
}

export function listNonConformities({ operationalSiteId, status } = {}) {
  const params = new URLSearchParams();
  if (operationalSiteId) params.set('operational_site_id', operationalSiteId);
  if (status) params.set('status', status);
  const q = params.toString();
  return apiRequest(`/compliance/non-conformities${q ? `?${q}` : ''}`);
}

export function updateNonConformity(id, payload) {
  return apiRequest(`/compliance/non-conformities/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function assignNonConformity(id, payload) {
  return apiRequest(`/compliance/non-conformities/${encodeURIComponent(id)}/assign`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function listRecurrenceSignals({ operationalSiteId, status } = {}) {
  const params = new URLSearchParams();
  if (operationalSiteId) params.set('operational_site_id', operationalSiteId);
  if (status) params.set('status', status);
  const q = params.toString();
  return apiRequest(`/compliance/recurrence-signals${q ? `?${q}` : ''}`);
}

export function markRecurrenceSignalSeen(id) {
  return apiRequest(`/compliance/recurrence-signals/${encodeURIComponent(id)}/mark-seen`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function dismissRecurrenceSignal(id) {
  return apiRequest(`/compliance/recurrence-signals/${encodeURIComponent(id)}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function convertRecurrenceSignal(id, payload) {
  return apiRequest(`/compliance/recurrence-signals/${encodeURIComponent(id)}/convert`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listCorrectiveActionProjects() {
  return apiRequest('/compliance/corrective-action-projects');
}

export function getCorrectiveActionProject(id) {
  return apiRequest(`/compliance/corrective-action-projects/${encodeURIComponent(id)}`);
}

export function updateCorrectiveActionProject(id, payload) {
  return apiRequest(`/compliance/corrective-action-projects/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
