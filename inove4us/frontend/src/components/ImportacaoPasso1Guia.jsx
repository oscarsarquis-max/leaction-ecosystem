/**
 * Orientação do Passo 1 — campos esperados, exemplo e download do modelo.
 * Reaproveita os nomes do modelo amigável (import_friendly / COLUNAS_PADRAO).
 */

const CAMPOS_ESPERADOS = [
  {
    nome: 'Título da aula ou evento',
    obrigatorio: true,
    dica: null,
    icon: 'titulo',
  },
  {
    nome: 'Data',
    obrigatorio: true,
    dica: 'Use dia/mês/ano (ex.: 10/08/2026).',
    icon: 'data',
  },
  {
    nome: 'Horário de início e término',
    obrigatorio: false,
    dica: null,
    icon: 'horario',
  },
  {
    nome: 'Tipo: aula ou evento',
    obrigatorio: false,
    dica: null,
    icon: 'tipo',
  },
  {
    nome: 'Instituição, curso e disciplina',
    obrigatorio: false,
    dica: null,
    icon: 'vinculo',
  },
  {
    nome: 'Assunto',
    obrigatorio: false,
    dica: 'Agrupa aulas da mesma sequência.',
    icon: 'assunto',
  },
  {
    nome: 'Observações',
    obrigatorio: false,
    dica: null,
    icon: 'obs',
  },
]

/** Cabeçalhos canônicos do modelo amigável (mesma ordem do backend). */
export const MODELO_CABECALHOS = [
  'Título da aula ou evento',
  'Data',
  'Horário de início',
  'Horário de término',
  'É aula ou é evento?',
  'Instituição',
  'Curso',
  'Disciplina',
  'Assunto',
  'Observações',
]

const EXEMPLO_LINHAS = [
  {
    titulo: 'Abertura do módulo',
    data: '10/08/2026',
    inicio: '08:00',
    fim: '08:50',
    tipo: 'Aula',
    instituicao: 'Escola Horizonte',
    curso: '7º ano',
    disciplina: 'Ciências',
    assunto: 'Fotossíntese',
    obs: 'Primeiro encontro',
  },
  {
    titulo: 'Cadeias alimentares',
    data: '17/08/2026',
    inicio: '08:00',
    fim: '08:50',
    tipo: 'Aula',
    instituicao: 'Escola Horizonte',
    curso: '7º ano',
    disciplina: 'Ciências',
    assunto: 'Fotossíntese',
    obs: '',
  },
  {
    titulo: 'Reunião de pais',
    data: '30/08/2026',
    inicio: '',
    fim: '',
    tipo: 'Evento',
    instituicao: '',
    curso: '',
    disciplina: '',
    assunto: '',
    obs: 'Horário a combinar',
  },
]

function IconeCampo({ tipo }) {
  const common = 'h-4 w-4 shrink-0 text-bordo'
  switch (tipo) {
    case 'titulo':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 7h16M4 12h10M4 17h14"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      )
    case 'data':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <rect x="3" y="5" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" />
          <path d="M3 10h18M8 3v4M16 3v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      )
    case 'horario':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
          <path d="M12 8v5l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      )
    case 'tipo':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      )
    case 'vinculo':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M10 13a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07L11 5"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M14 11a5 5 0 0 0-7.07 0L4.8 13.12a5 5 0 0 0 7.07 7.07L13 19"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      )
    case 'assunto':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M7 7h10v4H7zM7 13h6v4H7z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      )
    default:
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M6 5h12v14H6zM9 9h6M9 13h6M9 17h4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      )
  }
}

export function baixarModeloPlanilha() {
  const linhas = [
    MODELO_CABECALHOS,
    [
      'Abertura do módulo',
      '10/08/2026',
      '08:00',
      '08:50',
      'Aula',
      'Escola Horizonte',
      '7º ano',
      'Ciências',
      'Fotossíntese',
      'Primeiro encontro',
    ],
    [
      'Cadeias alimentares',
      '17/08/2026',
      '08:00',
      '08:50',
      'Aula',
      'Escola Horizonte',
      '7º ano',
      'Ciências',
      'Fotossíntese',
      '',
    ],
    [
      'Reunião de pais',
      '30/08/2026',
      '',
      '',
      'Evento',
      '',
      '',
      '',
      '',
      'Horário a combinar',
    ],
  ]
  const texto = linhas.map((cols) => cols.join(';')).join('\r\n')
  const blob = new Blob([`\uFEFF${texto}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'modelo-planilha-planejamento.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function ImportacaoPasso1Guia() {
  return (
    <aside className="space-y-5 rounded-2xl border border-brand-100 bg-white px-4 py-5 sm:px-5">
      <div>
        <h2 className="font-display text-lg font-bold text-bordo-deep">
          O que sua planilha deve conter
        </h2>
        <p className="mt-1 text-xs text-bordo-soft">
          Só título e data são obrigatórios. O restante ajuda a organizar o planejamento.
        </p>
        <ul className="mt-4 space-y-3">
          {CAMPOS_ESPERADOS.map((campo) => (
            <li key={campo.nome} className="flex gap-3">
              <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50">
                <IconeCampo tipo={campo.icon} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-bordo-deep">
                  {campo.nome}{' '}
                  <span
                    className={`text-[11px] font-bold uppercase tracking-wide ${
                      campo.obrigatorio ? 'text-bordo' : 'text-bordo-soft'
                    }`}
                  >
                    {campo.obrigatorio ? 'obrigatório' : 'opcional'}
                  </span>
                </p>
                {campo.dica ? (
                  <p className="mt-0.5 text-xs text-bordo-soft">{campo.dica}</p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-sm font-bold text-bordo-deep">Exemplo de como a planilha deve ficar</h3>
        <p className="mt-1 text-xs text-bordo-soft">
          Duas aulas com o mesmo Assunto formam uma sequência; o evento mostra que nem tudo
          precisa de disciplina.
        </p>
        <div className="mt-3 overflow-x-auto rounded-xl border border-brand-100">
          <table className="min-w-full text-left text-[11px]">
            <thead className="bg-brand-50 text-bordo-deep">
              <tr>
                <th className="whitespace-nowrap px-2 py-2 font-bold">Título</th>
                <th className="whitespace-nowrap px-2 py-2 font-bold">Data</th>
                <th className="whitespace-nowrap px-2 py-2 font-bold">Tipo</th>
                <th className="whitespace-nowrap px-2 py-2 font-bold">Disciplina</th>
                <th className="whitespace-nowrap px-2 py-2 font-bold">Assunto</th>
              </tr>
            </thead>
            <tbody>
              {EXEMPLO_LINHAS.map((l) => (
                <tr key={`${l.titulo}-${l.data}`} className="border-t border-brand-50 text-bordo">
                  <td className="whitespace-nowrap px-2 py-1.5 font-medium">{l.titulo}</td>
                  <td className="whitespace-nowrap px-2 py-1.5">{l.data}</td>
                  <td className="whitespace-nowrap px-2 py-1.5">{l.tipo}</td>
                  <td className="whitespace-nowrap px-2 py-1.5 text-bordo-soft">
                    {l.disciplina || '—'}
                  </td>
                  <td className="whitespace-nowrap px-2 py-1.5">
                    {l.assunto ? (
                      <span className="rounded bg-brand-50 px-1.5 py-0.5 font-medium text-bordo">
                        {l.assunto}
                      </span>
                    ) : (
                      <span className="text-bordo-soft">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <button
        type="button"
        className="btn-ghost w-full !px-4 !py-2.5 text-sm sm:w-auto"
        onClick={baixarModeloPlanilha}
      >
        Baixar modelo de planilha
      </button>
    </aside>
  )
}
