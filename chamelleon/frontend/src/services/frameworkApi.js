import { apiRequest } from './api';
import { getSession } from './session';

export async function listFrameworks() {
  const data = await apiRequest('/framework');
  return data.frameworks || [];
}

export async function getFramework(frameworkId) {
  const data = await apiRequest(`/framework/${encodeURIComponent(frameworkId)}`);
  return data.proposal;
}

export async function buildFrameworkProposal(
  sector,
  { strategicGuidelines = '', operationalGemba = '', frameworkName = '' } = {},
) {
  const body = { sector };
  const strategic = (strategicGuidelines || '').trim();
  const gemba = (operationalGemba || '').trim();
  const name = (frameworkName || '').trim();
  if (strategic) body.strategic_guidelines = strategic;
  if (gemba) body.operational_gemba = gemba;
  if (name) body.framework_name = name;
  const data = await apiRequest('/framework/build-proposal', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return data.proposal;
}

export async function getFrameworkTaxonomy(frameworkId) {
  const data = await apiRequest(
    `/framework/${encodeURIComponent(frameworkId)}/taxonomy`,
  );
  return data.taxonomy;
}

export async function getFrameworkMethodology(frameworkId) {
  const data = await apiRequest(
    `/framework/${encodeURIComponent(frameworkId)}/methodology-document`,
  );
  return data.methodology_structure;
}

export async function fetchMethodologyStructure(operationalDimension, frameworkId) {
  if (frameworkId) {
    return getFrameworkMethodology(frameworkId);
  }
  const data = await apiRequest('/framework/methodology-document', {
    method: 'POST',
    body: JSON.stringify({ operational_dimension: operationalDimension }),
  });
  return data.methodology_structure;
}

export async function publishFramework(proposal, { replace = false } = {}) {
  return apiRequest('/framework/publish', {
    method: 'POST',
    body: JSON.stringify({ proposal, replace }),
  });
}

export async function updateFramework(frameworkId, proposal) {
  return apiRequest(`/framework/${encodeURIComponent(frameworkId)}`, {
    method: 'PUT',
    body: JSON.stringify({ proposal }),
  });
}

export async function deleteFramework(frameworkId) {
  return apiRequest(`/framework/${encodeURIComponent(frameworkId)}`, {
    method: 'DELETE',
  });
}

export async function importFrameworkQuestionsJson(frameworkId, file) {
  const formData = new FormData();
  formData.append('file', file);

  const session = getSession();
  const headers = new Headers();
  if (session?.tenantId) headers.set('X-Tenant-ID', session.tenantId);
  if (session?.userId) headers.set('X-User-ID', session.userId);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
  const response = await fetch(
    `${API_BASE_URL}/framework/${encodeURIComponent(frameworkId)}/questions/import-json`,
    {
      method: 'POST',
      body: formData,
      headers,
    },
  );

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || `Erro HTTP ${response.status}`);
  }
  return data;
}
