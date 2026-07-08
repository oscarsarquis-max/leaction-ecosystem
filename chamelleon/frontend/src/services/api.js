/**
 * Cliente HTTP — sessão real (login LA-*) ou headers de desenvolvimento.
 */

import { getSession } from './session';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const hasPayload = Boolean(data.error || data.message);
    if (!hasPayload && response.status >= 500) {
      const offline = new Error(
        'Servidor indisponível. Inicie o backend Chamelleon na porta 5010 (ex.: .\\start-local.ps1).'
      );
      offline.code = 'BACKEND_UNAVAILABLE';
      offline.status = response.status;
      throw offline;
    }
    const message = data.error || data.message || `Erro HTTP ${response.status}`;
    const err = new Error(message);
    err.code = data.code;
    err.status = response.status;
    throw err;
  }
  return data;
}

async function requestJson(url, options = {}) {
  try {
    const response = await fetch(url, options);
    return parseResponse(response);
  } catch (err) {
    if (err instanceof TypeError || err.message === 'Failed to fetch') {
      const offline = new Error(
        'Servidor indisponível. Verifique se o backend está em execução (porta 5010).'
      );
      offline.code = 'NETWORK_ERROR';
      throw offline;
    }
    throw err;
  }
}

function authHeaders() {
  const headers = new Headers();
  const session = getSession();
  if (session?.tenantId) headers.set('X-Tenant-ID', session.tenantId);
  if (session?.userId) headers.set('X-User-ID', session.userId);
  return headers;
}

export async function publicApiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await requestJson(`${API_BASE_URL}${path}`, { ...options, headers });
  return response;
}

export async function apiRequest(path, options = {}) {
  const headers = authHeaders();
  new Headers(options.headers || {}).forEach((value, key) => headers.set(key, value));

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await requestJson(`${API_BASE_URL}${path}`, { ...options, headers });
  return response;
}

export function listSectors() {
  return publicApiRequest('/auth/sectors');
}

export function registerLead(payload) {
  return publicApiRequest('/auth/register-lead', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function resendAccessCode(email) {
  return publicApiRequest('/auth/resend-code', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function resetLeadRegistration(email) {
  return publicApiRequest('/auth/reset-lead', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function checkEmail(email) {
  return publicApiRequest('/auth/check-email', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function login(email, credential) {
  return publicApiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, credential, codigo: credential }),
  });
}

export function getAuthMe() {
  return apiRequest('/auth/me');
}

export function getClientJourney() {
  return apiRequest('/client/journey');
}

export function saveClientContext(payload) {
  return apiRequest('/client/context', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function activateClientProject() {
  return apiRequest('/client/activate-project', { method: 'POST' });
}

export function getTenantUsers() {
  return apiRequest('/auth/users');
}

export function getAssessmentQuestions() {
  return apiRequest('/assessment/questions');
}

export function getMyLatestResult() {
  return apiRequest('/assessment/my-result');
}

export function listSurveys(search = '') {
  const params = search ? `?q=${encodeURIComponent(search)}` : '';
  return apiRequest(`/assessment/surveys${params}`);
}

export function getSurvey(submissionId) {
  return apiRequest(`/assessment/surveys/${encodeURIComponent(submissionId)}`);
}

export function getAssessmentDraft() {
  return apiRequest('/assessment/draft');
}

export function saveAssessmentDraft(payload) {
  return apiRequest('/assessment/draft', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function resetAssessmentDraft() {
  return apiRequest('/assessment/draft', { method: 'DELETE' });
}

export function updatePresentAssessment(payload) {
  return apiRequest('/assessment/update-present', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function submitAssessment(payload) {
  return apiRequest('/assessment/submit', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getDiagnosticReport(submissionId) {
  return apiRequest(`/assessment/diagnostic-report/${encodeURIComponent(submissionId)}`);
}

export function getActionPlan(actionPlanId) {
  return apiRequest(`/assessment/action-plan/${encodeURIComponent(actionPlanId)}`);
}

export function listQuestions() {
  return apiRequest('/questions');
}

export function listQuestionsAdminCatalog() {
  return apiRequest('/questions/admin-catalog');
}

export function createQuestion(payload) {
  return apiRequest('/questions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateQuestion(questionId, payload) {
  return apiRequest(`/questions/${encodeURIComponent(questionId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteQuestion(questionId) {
  return apiRequest(`/questions/${encodeURIComponent(questionId)}`, {
    method: 'DELETE',
  });
}

export function seedMvpContext() {
  return apiRequest('/seed/mvp', { method: 'POST' });
}

export function listAdminUsers(query = '') {
  const suffix = query ? `?${query}` : '';
  return apiRequest(`/admin/users${suffix}`);
}

export function listAdminTenantOptions() {
  return apiRequest('/admin/users/tenant-options');
}

export function getAdminUserAccess(userId) {
  return apiRequest(`/admin/users/${encodeURIComponent(userId)}/access`);
}

export function createAdminUser(payload) {
  return apiRequest('/admin/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateAdminUser(userId, payload) {
  return apiRequest(`/admin/users/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deactivateAdminUser(userId) {
  return apiRequest(`/admin/users/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

export function regenerateAdminUserCode(userId) {
  return apiRequest(`/admin/users/${encodeURIComponent(userId)}/regenerate-code`, {
    method: 'POST',
  });
}
