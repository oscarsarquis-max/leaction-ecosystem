/**
 * Datas padrão do período letivo conforme o tipo.
 * Início padrão: 1º de janeiro do ano letivo.
 */
export function datasPadraoPeriodo(tipoPeriodo, anoLetivo) {
  const y = Number(anoLetivo) || new Date().getFullYear()
  const data_inicio = `${y}-01-01`
  switch (String(tipoPeriodo || '').toLowerCase()) {
    case 'quinzenal':
      return { data_inicio, data_fim: `${y}-01-15` }
    case 'mensal':
      return { data_inicio, data_fim: `${y}-01-31` }
    case 'trimestral':
      return { data_inicio, data_fim: `${y}-03-31` }
    case 'semestral':
      return { data_inicio, data_fim: `${y}-06-30` }
    case 'modular':
    case 'anual':
    default:
      return { data_inicio, data_fim: `${y}-12-31` }
  }
}

export const TIPOS_PERIODO_OPTS = [
  { value: 'anual', label: 'Anual' },
  { value: 'semestral', label: 'Semestral' },
  { value: 'trimestral', label: 'Trimestral' },
  { value: 'mensal', label: 'Mensal' },
  { value: 'quinzenal', label: 'Quinzenal' },
  { value: 'modular', label: 'Modular' },
]
