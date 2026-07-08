/** Estágios Lean do workflow Kaizen (espelho do backend). */

export const KAIZEN_STAGES = [
  {
    id: 'Alerta',
    label: 'Alertas (Andon)',
    shortLabel: 'Alertas',
    headerClass: 'border-orange-200 bg-gradient-to-r from-red-50 to-orange-50',
    titleClass: 'text-orange-900',
    columnClass: 'border-orange-100 bg-orange-50/30',
    accentClass: 'ring-orange-200',
  },
  {
    id: 'Contencao',
    label: 'Contenção',
    shortLabel: 'Contenção',
    headerClass: 'border-amber-200 bg-amber-50',
    titleClass: 'text-amber-900',
    columnClass: 'border-amber-100 bg-amber-50/30',
    accentClass: 'ring-amber-200',
  },
  {
    id: 'Cinco_Porques',
    label: '5 Porquês (Causa Raiz)',
    shortLabel: '5 Porquês',
    headerClass: 'border-sky-200 bg-sky-50',
    titleClass: 'text-sky-900',
    columnClass: 'border-sky-100 bg-sky-50/30',
    accentClass: 'ring-sky-200',
  },
  {
    id: 'Padronizacao',
    label: 'Padronização',
    shortLabel: 'Padronização',
    headerClass: 'border-violet-200 bg-violet-50',
    titleClass: 'text-violet-900',
    columnClass: 'border-violet-100 bg-violet-50/30',
    accentClass: 'ring-violet-200',
  },
  {
    id: 'Concluido',
    label: 'Concluído',
    shortLabel: 'Concluído',
    headerClass: 'border-emerald-200 bg-emerald-50',
    titleClass: 'text-emerald-900',
    columnClass: 'border-emerald-100 bg-emerald-50/30',
    accentClass: 'ring-emerald-200',
  },
];

export const ANDON_BADGES = [
  {
    id: 'accident',
    label: 'Acidente',
    className: 'bg-red-100 text-red-800 ring-red-200',
    match: (ticket) =>
      /acidente/i.test(ticket.title || '') || /acidente/i.test(ticket.description || ''),
  },
  {
    id: 'rework',
    label: 'Retrabalho',
    className: 'bg-amber-100 text-amber-900 ring-amber-200',
    match: (ticket) => /retrabalho/i.test(ticket.title || ''),
  },
  {
    id: 'material',
    label: 'Falta de Material',
    className: 'bg-orange-100 text-orange-900 ring-orange-200',
    match: (ticket) =>
      /esperando material/i.test(ticket.title || '') ||
      /falta de material/i.test(ticket.title || ''),
  },
];
