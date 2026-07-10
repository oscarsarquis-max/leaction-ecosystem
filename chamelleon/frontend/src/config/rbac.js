/** Papéis RBAC do Chamelleon. */

export const ROLE_SYSADMIN = 'sysadmin';
export const ROLE_LED = 'led';
export const ROLE_CONSULTOR = 'consultor';
export const ROLE_EXECUTOR = 'executor';

export const ROLE_LABELS = {
  [ROLE_SYSADMIN]: 'Administrador',
  [ROLE_LED]: 'Lead (Gestor)',
  [ROLE_CONSULTOR]: 'Consultor',
  [ROLE_EXECUTOR]: 'Executor',
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
  '/td/plan': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/td/kanban': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  // Compatibilidade com rotas antigas
  '/operational-planning': [ROLE_SYSADMIN, ROLE_LED],
  '/operational-reports': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR],
  '/portal': [ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR, ROLE_EXECUTOR],
};

export const KAIZEN_NAV_ITEM = {
  to: '/kaizen',
  label: 'Melhoria Contínua',
  roles: ROUTE_PERMISSIONS['/kaizen'],
  icon: 'gear',
};

export const ORGANIZATION_NAV_ITEM = {
  to: '/settings/organization',
  label: 'Configurações da Organização',
  roles: ROUTE_PERMISSIONS['/settings/organization'],
};

/** Grupo coeso: unidades + planejamento + relatórios. */
export const OPERATIONAL_AREA_NAV = {
  label: 'Área Operacional',
  roles: [
    ...new Set([
      ...ROUTE_PERMISSIONS['/operational/sites'],
      ...ROUTE_PERMISSIONS['/operational/planning'],
      ...ROUTE_PERMISSIONS['/operational/reports'],
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
      label: 'Relatórios',
      roles: ROUTE_PERMISSIONS['/operational/reports'],
    },
  ],
};

/** @deprecated Prefer OPERATIONAL_AREA_NAV */
export const OPERATIONAL_PANEL_NAV = OPERATIONAL_AREA_NAV;

/** Grupo: Plano Diretor (Backlog) + Kanban de Implementação. */
export const TD_AREA_NAV = {
  label: 'Transformação Digital (TD)',
  roles: [
    ...new Set([
      ...ROUTE_PERMISSIONS['/td/plan'],
      ...ROUTE_PERMISSIONS['/td/kanban'],
    ]),
  ],
  children: [
    {
      to: '/td/plan',
      label: 'Plano Diretor e Backlog',
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
  { to: '/', label: 'Meu Resultado', end: true },
  { to: '/my-assessment', label: 'Minha Avaliação' },
  { to: '/meus-dados', label: 'Meus Dados' },
];

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true, roles: ROUTE_PERMISSIONS['/'] },
  KAIZEN_NAV_ITEM,
  TD_AREA_NAV,
  OPERATIONAL_AREA_NAV,
  ORGANIZATION_NAV_ITEM,
  { to: '/my-assessment', label: 'Minha Avaliação', roles: ROUTE_PERMISSIONS['/my-assessment'] },
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
