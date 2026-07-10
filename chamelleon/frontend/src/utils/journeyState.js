import {
  KAIZEN_NAV_ITEM,
  OPERATIONAL_AREA_NAV,
  ORGANIZATION_NAV_ITEM,
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

export function buildLeadNavItems(journeyFlags, journey) {
  const submissionId = journey?.latest_submission_id || null;
  const base = [
    { to: '/', label: 'Painel de Maturidade', end: true },
  ];

  if (submissionId) {
    base.push({
      to: `/relatorio/${submissionId}`,
      label: 'Relatório de Diagnóstico',
    });
  }

  base.push(
    { to: '/my-assessment', label: 'Minha Avaliação' },
    { to: '/meus-dados', label: 'Meus Dados' },
  );

  base.push(KAIZEN_NAV_ITEM);
  base.push(TD_AREA_NAV);
  base.push(ORGANIZATION_NAV_ITEM);
  base.push(OPERATIONAL_AREA_NAV);

  if (journeyFlags.mostrarPlanoKanban) {
    // Prefere o módulo TD; mantém links legado se alguém ainda usar essas rotas.
    base.push(
      { to: '/td/plan', label: 'Plano Diretor TD', highlight: true },
      { to: '/td/kanban', label: 'Kanban TD' },
    );
  }

  return base;
}
