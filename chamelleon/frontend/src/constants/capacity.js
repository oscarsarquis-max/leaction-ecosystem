/** Capacity Planning — papéis do Pool de Talentos. */

export const PROFESSIONAL_ROLES = [
  { value: 'PO', label: 'Product Owner (PO)' },
  { value: 'Scrum_Master', label: 'Scrum Master' },
  { value: 'Dev', label: 'Dev' },
  { value: 'QA', label: 'QA' },
  { value: 'Analista_TI', label: 'Analista de TI' },
  { value: 'Analista_Negocio', label: 'Analista de Negócio' },
  { value: 'Gerente_Projeto', label: 'Gerente de Projeto' },
  { value: 'Outro', label: 'Outro' },
];

export const ROLE_PO = 'PO';
export const ROLE_SM = 'Scrum_Master';

export const SQUAD_MAX_SPECIALISTS = 6;
export const SQUAD_MAX_TOTAL = 8;

export function professionalRoleLabel(role) {
  return PROFESSIONAL_ROLES.find((r) => r.value === role)?.label || role || '—';
}

export function hasValidSquad(sprintOrSquad) {
  const squad = sprintOrSquad?.squad || sprintOrSquad;
  return Boolean(squad?.po_id && squad?.sm_id);
}
