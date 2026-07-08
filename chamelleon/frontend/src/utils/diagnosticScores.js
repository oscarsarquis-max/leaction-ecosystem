/** Helpers para tabela comparativa P/F/Gap — espelho PanelDX diagnosticos.ejs */

export const DIMENSION_ROWS = [
  { id: 1, name: 'Visão Compartilhada (SV)' },
  { id: 2, name: 'Coração e Conexão (HC)' },
  { id: 3, name: 'Estrutura Fluida (FS)' },
  { id: 4, name: 'Aprendizagem em Ação (LA)' },
  { id: 5, name: 'Arquitetura Digital (DA)' },
];

export const DOMAIN_ROWS = [
  { id: 1, key: 'ds', name: 'Estratégia Digital (ds)', shortName: 'Estratégia Digital', sigla: 'ds' },
  { id: 2, key: 'bm', name: 'Modelo de Negócio Digital (bm)', shortName: 'Modelo de Negócio Digital', sigla: 'bm' },
  { id: 3, key: 'ic', name: 'Cultura de Inovação (ic)', shortName: 'Cultura de Inovação', sigla: 'ic' },
  { id: 4, key: 'dc', name: 'Cultura de Dados (dc)', shortName: 'Cultura de Dados', sigla: 'dc' },
  { id: 5, key: 'cc', name: 'Cultura de Colaboração (cc)', shortName: 'Cultura de Colaboração', sigla: 'cc' },
  { id: 6, key: 'dg', name: 'Governança Digital (dg)', shortName: 'Governança Digital', sigla: 'dg' },
  { id: 7, key: 'dp', name: 'Plataformas Digitais (dp)', shortName: 'Plataformas Digitais', sigla: 'dp' },
  { id: 8, key: 'cap', name: 'Capacidades Digitais (cap)', shortName: 'Capacidades Digitais', sigla: 'cap' },
  { id: 9, key: 'dm', name: 'Métricas Digitais (dm)', shortName: 'Métricas Digitais', sigla: 'dm' },
];

export const DIM_SHORT = { 1: 'SV', 2: 'HC', 3: 'FS', 4: 'LA', 5: 'DA' };

export function getNumericScore(score) {
  const num = parseFloat(score);
  return Number.isNaN(num) ? 0 : num;
}

export function sectorDimShort(sectorDimensionLabel) {
  if (!sectorDimensionLabel) return DIM_SHORT[4];
  const match = sectorDimensionLabel.match(/\(([A-Z]{2,})\)\s*$/);
  return match ? match[1] : DIM_SHORT[4];
}

export function buildSectorLegendLabel(sector, sectorDimensionLabel) {
  if (sector) {
    const label = String(sector).trim();
    return label.toLowerCase().startsWith('setor') ? label : `Setor ${label}`;
  }
  if (sectorDimensionLabel) {
    return `Setor ${sectorDimShort(sectorDimensionLabel)}`;
  }
  return 'Setorial';
}

export function extractSetorialPresente(source = {}) {
  const sectorPresente =
    source.scores_setorial_presente ||
    source.scores_detalhe?.sector?.presente ||
    {};
  return {
    pdom_scores: sectorPresente.pdom || sectorPresente.pdom_scores || {},
    pdim_scores: sectorPresente.pdim || sectorPresente.pdim_scores || {},
  };
}

export function formatScore(scores, id) {
  const value = scores?.[String(id)];
  const num = parseFloat(value);
  if (Number.isNaN(num) || num === 0) return '0.00';
  return num.toFixed(2);
}

export function getClientStage(score) {
  const num = parseFloat(score);
  if (Number.isNaN(num)) return 'N/A';
  if (num <= 2.0) return 'Iniciação';
  if (num <= 3.5) return 'Escalabilidade';
  return 'Evolução';
}

export function buildDimensionRows(sectorDimensionLabel) {
  return DIMENSION_ROWS.map((row) =>
    row.id === 4 && sectorDimensionLabel
      ? { ...row, name: sectorDimensionLabel }
      : row,
  );
}

export function buildDomainRows(domainLabels = {}) {
  return DOMAIN_ROWS.map((row) => {
    const key = domainLabels[String(row.id)] || row.key;
    const fromKey = DOMAIN_ROWS.find((d) => d.key === key);
    return {
      ...row,
      name: fromKey?.name || row.name,
    };
  });
}
