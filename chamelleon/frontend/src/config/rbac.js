/** Papéis RBAC do Chamelleon. */

export const ROLE_SYSADMIN = 'sysadmin';
export const ROLE_LED = 'led';
export const ROLE_CONSULTOR = 'consultor';
export const ROLE_EXECUTOR = 'executor';
export const ROLE_SQUAD_MEMBER = 'squad_member';

export const ROLE_LABELS = {
  [ROLE_SYSADMIN]: 'Administrador',
  [ROLE_LED]: 'Lead (Gestor)',
  [ROLE_CONSULTOR]: 'Consultor',
  [ROLE_EXECUTOR]: 'Executor',
  [ROLE_SQUAD_MEMBER]: 'Membro de Squad',
};

/** Utilizadores padrão de desenvolvimento (referência). */
export const DEV_STANDARD_USERS = {
  sysadmin: {
    email: 'sysadmin@leaction.com.br',
    password: 'LeAction1!',
    role: ROLE_SYSADMIN,
  },
  leadTest: {
    email: 'engenharia@paneldx.com.br',
    accessCode: 'LA-ENG1',
    role: ROLE_LED,
  },
  executor: {
    email: 'executor@paneldx.com.br',
    password: 'PanelDX1!',
    role: ROLE_EXECUTOR,
  },
};

/** Rotas e papéis permitidos (sem bypass automático de sysadmin no menu). */
export const ROUTE_PERMISSIONS = {
  '/': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR, ROLE_EXECUTOR],
  '/meus-dados': [ROLE_LED, ROLE_CONSULTOR],
  '/plano-geral': [ROLE_LED],
  '/kanban': [ROLE_LED],
  '/avaliacoes': [ROLE_SYSADMIN, ROLE_CONSULTOR],
  '/my-assessment': [ROLE_SYSADMIN, ROLE_CONSULTOR, ROLE_LED],
  '/usuarios': [ROLE_SYSADMIN],
  '/questoes': [ROLE_SYSADMIN],
  '/diagnostico': [ROLE_LED],
  '/builder': [ROLE_SYSADMIN],
  '/kaizen': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/settings/organization': [ROLE_SYSADMIN, ROLE_LED],
  '/operational/sites': [ROLE_SYSADMIN, ROLE_LED],
  '/operational/planning': [ROLE_SYSADMIN, ROLE_LED],
  '/operational/reports': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/professionals-manager': [ROLE_SYSADMIN, ROLE_LED],
  '/td/plan': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/td/kanban': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/strategic-planning': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  // Compatibilidade com rotas antigas
  '/operational-planning': [ROLE_SYSADMIN, ROLE_LED],
  '/operational-reports': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/portal': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR, ROLE_EXECUTOR],
};

export const OKR_NAV_ITEM = {
  to: '/strategic-planning',
  label: 'Planejamento Estratégico (OKR)',
  roles: ROUTE_PERMISSIONS['/strategic-planning'],
};

export const GERENCIAL_NAV_ITEM = {
  to: '/',
  label: 'Painel Gerencial',
  end: true,
  roles: ROUTE_PERMISSIONS['/'],
};

export const KAIZEN_NAV_ITEM = {
  to: '/kaizen',
  label: 'Melhoria Contínua',
  roles: ROUTE_PERMISSIONS['/kaizen'],
};

export const ORGANIZATION_NAV_ITEM = {
  to: '/settings/organization',
  label: 'Configurações da Organização',
  roles: ROUTE_PERMISSIONS['/settings/organization'],
};

/** Diagnóstico e dados do contexto do cliente. */
export const CONTEXT_ORG_NAV = {
  label: 'Contexto Organizacional',
  roles: [
    ...new Set([
      ...ROUTE_PERMISSIONS['/'],
      ...ROUTE_PERMISSIONS['/my-assessment'],
      ...ROUTE_PERMISSIONS['/meus-dados'],
    ]),
  ],
  children: [
    {
      to: '/my-assessment',
      label: 'Minha Avaliação',
      roles: ROUTE_PERMISSIONS['/my-assessment'],
    },
    {
      to: '/meus-dados',
      label: 'Meus Dados',
      roles: ROUTE_PERMISSIONS['/meus-dados'],
    },
  ],
};

/** Unidades, planejamento semanal, RDO e pool. */
export const OPERATIONAL_AREA_NAV = {
  label: 'Gestão Operacional',
  roles: [
    ...new Set([
      ...ROUTE_PERMISSIONS['/operational/sites'],
      ...ROUTE_PERMISSIONS['/operational/planning'],
      ...ROUTE_PERMISSIONS['/operational/reports'],
      ...ROUTE_PERMISSIONS['/professionals-manager'],
    ]),
  ],
  children: [
    {
      to: '/operational/sites',
      label: 'Gestão de Unidades',
      roles: ROUTE_PERMISSIONS['/operational/sites'],
    },
    {
      to: '/operational/planning',
      label: 'Planejamento Semanal',
      roles: ROUTE_PERMISSIONS['/operational/planning'],
    },
    {
      to: '/operational/reports',
      label: 'Relatórios de Execução (RDO)',
      roles: ROUTE_PERMISSIONS['/operational/reports'],
    },
    {
      to: '/professionals-manager',
      label: 'Pool de Talentos',
      roles: ROUTE_PERMISSIONS['/professionals-manager'],
    },
  ],
};

/** @deprecated Prefer OPERATIONAL_AREA_NAV */
export const OPERATIONAL_PANEL_NAV = OPERATIONAL_AREA_NAV;

/** Estratégia OKR + backlog TD + kanban de implementação. */
export const TD_AREA_NAV = {
  label: 'Estratégia e Transformação Digital',
  roles: [
    ...new Set([
      ...ROUTE_PERMISSIONS['/strategic-planning'],
      ...ROUTE_PERMISSIONS['/td/plan'],
      ...ROUTE_PERMISSIONS['/td/kanban'],
    ]),
  ],
  children: [
    OKR_NAV_ITEM,
    {
      to: '/td/plan',
      label: 'Backlog de Transformação Digital',
      roles: ROUTE_PERMISSIONS['/td/plan'],
    },
    {
      to: '/td/kanban',
      label: 'Kanban de Implementação',
      roles: ROUTE_PERMISSIONS['/td/kanban'],
    },
  ],
};

/** Menu simplificado para lead — diagnóstico + resultado (sem listagem administrativa). */
export const LEAD_NAV_ITEMS = [
  { to: '/', label: 'Painel Gerencial', end: true },
  { to: '/my-assessment', label: 'Minha Avaliação' },
  { to: '/meus-dados', label: 'Meus Dados' },
];

export const NAV_ITEMS = [
  GERENCIAL_NAV_ITEM,
  KAIZEN_NAV_ITEM,
  ORGANIZATION_NAV_ITEM,
  CONTEXT_ORG_NAV,
  OPERATIONAL_AREA_NAV,
  TD_AREA_NAV,
  { to: '/usuarios', label: 'Utilizadores', roles: ROUTE_PERMISSIONS['/usuarios'] },
  { to: '/questoes', label: 'Questões', roles: ROUTE_PERMISSIONS['/questoes'] },
  { to: '/builder', label: 'Frameworks (Builder)', roles: ROUTE_PERMISSIONS['/builder'] },
];

export function hasRole(userRole, allowedRoles) {
  if (!userRole || !allowedRoles?.length) return false;
  return allowedRoles.includes(userRole);
}

export function canAccessRoute(userRole, path) {
  let key = path.split('/').slice(0, 2).join('/') || '/';
  if (path.startsWith('/avaliacoes/')) key = '/avaliacoes';
  if (path.startsWith('/my-assessment')) key = '/my-assessment';
  if (path.startsWith('/settings/')) key = '/settings/organization';
  if (path.startsWith('/operational/')) {
    if (path.startsWith('/operational/reports')) key = '/operational/reports';
    else if (path.startsWith('/operational/planning')) key = '/operational/planning';
    else if (path.startsWith('/operational/sites')) key = '/operational/sites';
    else key = '/operational/sites';
  }
  if (path.startsWith('/professionals-manager')) key = '/professionals-manager';
  if (path.startsWith('/strategic-planning')) key = '/strategic-planning';
  if (path.startsWith('/td/')) {
    if (path.startsWith('/td/kanban')) key = '/td/kanban';
    else key = '/td/plan';
  }
  // Redirects legados
  if (path.startsWith('/operational-reports')) key = '/operational/reports';
  if (path.startsWith('/operational-planning')) key = '/operational/planning';
  const allowed = ROUTE_PERMISSIONS[key] || ROUTE_PERMISSIONS['/'];
  return hasRole(userRole, allowed);
}

export function filterNavItems(items, userRole) {
  return (items || [])
    .map((item) => {
      if (item.children?.length) {
        const children = item.children.filter((child) => hasRole(userRole, child.roles));
        if (!children.length) return null;
        return { ...item, children };
      }
      if (!hasRole(userRole, item.roles)) return null;
      return item;
    })
    .filter(Boolean);
}
