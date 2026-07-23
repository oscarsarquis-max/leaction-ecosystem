/** Dados mock da Área Logada — design / retenção (sem API). */

export type RecentActivity = {
  id: string;
  title: string;
  detail: string;
  when: string;
};

export type QuickTip = {
  id: string;
  title: string;
  href: string;
};

export const MOCK_WORKSPACE = 'Minha Empresa';

export const MOCK_RECENT_ACTIVITIES: RecentActivity[] = [
  {
    id: 'a1',
    title: 'Diagnóstico Inove4us iniciado',
    detail: 'Mesa do Inovador · rascunho salvo',
    when: 'há 2 horas',
  },
  {
    id: 'a2',
    title: 'Acesso ao Marketplace',
    detail: 'Vitrine B2B · 3 itens visualizados',
    when: 'ontem',
  },
  {
    id: 'a3',
    title: 'Convite de workspace',
    detail: 'Equipe pedagógica adicionada',
    when: 'há 3 dias',
  },
  {
    id: 'a4',
    title: 'Plano Freemium ativo',
    detail: 'Cota de projetos renovada',
    when: 'semana passada',
  },
];

export const MOCK_QUICK_TIPS: QuickTip[] = [
  {
    id: 't1',
    title: 'Como dar os primeiros passos no Inove4us',
    href: 'https://inove4us.com.br',
  },
  {
    id: 't2',
    title: 'Boas práticas de inovação',
    href: 'https://inove4us.com.br',
  },
];

export const MOCK_PLAN = {
  name: 'Plano Freemium Ativo',
  used: 2,
  total: 3,
  unitLabel: 'Projetos Disponíveis',
};

export function resolveInove4usUrl(): string {
  const fromEnv = (process.env.NEXT_PUBLIC_INOVE4US_URL || '').trim().replace(/\/$/, '');
  return fromEnv || 'https://inove4us.com.br';
}
