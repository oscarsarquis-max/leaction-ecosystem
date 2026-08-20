import { apiRequest } from './api';

export function listOrganizationalUnits() {
  return apiRequest('/organization/units');
}

export function createOrganizationalUnit(payload) {
  return apiRequest('/organization/units', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateOrganizationalUnit(unitId, payload) {
  return apiRequest(`/organization/units/${encodeURIComponent(unitId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteOrganizationalUnit(unitId) {
  return apiRequest(`/organization/units/${encodeURIComponent(unitId)}`, {
    method: 'DELETE',
  });
}
