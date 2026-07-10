import { apiRequest } from './api';

export function getTdPlan() {
  return apiRequest('/td/plan');
}

export function saveTdPlan(payload) {
  return apiRequest('/td/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function listTdSprints(kanbanStage) {
  const query = kanbanStage
    ? `?kanban_stage=${encodeURIComponent(kanbanStage)}`
    : '';
  return apiRequest(`/td/sprints${query}`);
}

export function fetchTdKanban() {
  return apiRequest('/td/sprints?board=1');
}

export function createTdSprint(payload) {
  return apiRequest('/td/sprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateTdSprint(sprintId, payload) {
  return apiRequest(`/td/sprints/${encodeURIComponent(sprintId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function promoteTdSprintToPlanning(sprintId) {
  return apiRequest(`/td/sprints/${encodeURIComponent(sprintId)}/promote-planning`, {
    method: 'POST',
  });
}

export function generateTdPlan(payload = {}) {
  return apiRequest('/td/plan/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getTdReadinessStatus() {
  return apiRequest('/td/readiness-status');
}

export function getTdGenesisStatus() {
  return apiRequest('/td/genesis-status');
}
