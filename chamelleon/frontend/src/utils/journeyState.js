import {
  CONTEXT_ORG_NAV,
  filterNavItems,
  GERENCIAL_NAV_ITEM,
  KAIZEN_NAV_ITEM,
  OPERATIONAL_AREA_NAV,
  ORGANIZATION_NAV_ITEM,
  ROLE_LED,
  TD_AREA_NAV,
} from '../config/rbac';

/** Máquina de estados da jornada — espelho PanelDX index.ejs */

export const JOURNEY_STATUS = {
  AGUARDANDO_CONTEXTO: 'AGUARDANDO CONTEXTO',
  PRESURVEY_OK: 'PRESURVEY OK',
  PROJETO_OK: 'PROJETO OK',
  CONTEXTO_OK: 'CONTEXTO OK',
  AVALIACAO_OK: 'AVALIACAO OK',
  PENDENTE: 'PENDENTE',
  PROCESSANDO: 'PROCESSANDO',
  CONCLUIDO: 'CONCLUIDO',
  ERRO_IA: 'ERRO_IA',
};

export function resolveJourneyFlags(journey) {
  const flags = journey?.flags || {};
  const statusIa = (journey?.status_ia || '').toUpperCase();

  return {
    statusIa,
    ...flags,
    isAguardandoContexto: flags.is_aguardando_contexto ?? statusIa === JOURNEY_STATUS.AGUARDANDO_CONTEXTO,
    isProjetoOk: flags.is_projeto_ok ?? false,
    isContextoOk: flags.is_contexto_ok ?? false,
    isAvaliacaoOk: flags.is_avaliacao_ok ?? false,
    isEmProcessamento: flags.is_em_processamento ?? false,
    isPlanoConcluido: flags.is_plano_concluido ?? statusIa === JOURNEY_STATUS.CONCLUIDO,
    isErroIa: flags.is_erro_ia ?? statusIa === JOURNEY_STATUS.ERRO_IA,
    podeGerarPlano: flags.pode_gerar_plano ?? false,
    podeAtualizarPlano: flags.pode_atualizar_plano ?? false,
    mostrarPlanoKanban: flags.mostrar_plano_kanban ?? false,
    mostrarBotaoGenese: flags.mostrar_botao_genese ?? false,
    planoAtivado: flags.plano_ativado ?? false,
    steps: journey?.steps || [],
    kanbanColumns: journey?.kanban_columns || [],
  };
}

function withFilteredChildren(group, systemRole) {
  const role = systemRole || ROLE_LED;
  const filtered = filterNavItems([group], role)[0];
  if (!filtered?.children?.length) return null;
  return filtered;
}

/**
 * Sidebar do Lead/Consultor — hierarquia acordada de navegação.
 *
 * 1. Painel Gerencial
 * 2. Melhoria Contínua
 * 3. Configurações da Organização
 * 4. Contexto Organizacional
 * 5. Gestão Operacional
 * 6. Estratégia e Transformação Digital
 *    - Estratégia e OKRs
 *    - Backlog / Kanban TD
 */
export function buildLeadNavItems(journeyFlags, journey, systemRole = ROLE_LED) {
  const submissionId = journey?.latest_submission_id || null;

  const contextChildren = [...(CONTEXT_ORG_NAV.children || [])];
  if (submissionId) {
    contextChildren.unshift({
      to: `/relatorio/${submissionId}`,
      label: 'Relatório de Diagnóstico',
    });
  }

  const contextGroup = withFilteredChildren(
    { ...CONTEXT_ORG_NAV, children: contextChildren },
    systemRole,
  );

  const operationalGroup = withFilteredChildren(OPERATIONAL_AREA_NAV, systemRole);
  const tdGroup = withFilteredChildren(TD_AREA_NAV, systemRole);

  const base = [
    { ...GERENCIAL_NAV_ITEM },
    { ...KAIZEN_NAV_ITEM },
    { ...ORGANIZATION_NAV_ITEM },
  ];

  if (contextGroup) base.push(contextGroup);
  if (operationalGroup) base.push(operationalGroup);
  if (tdGroup) base.push(tdGroup);

  return base;
}
