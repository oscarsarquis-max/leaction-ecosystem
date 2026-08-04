import { useMemo, useState } from 'react'

const INITIAL_TEAM = [
  {
    id: '1',
    email: 'maria.silva@horizonte.edu.br',
    status: 'Ativo',
    convidadoEm: '2026-07-12',
  },
  {
    id: '2',
    email: 'joao.souza@horizonte.edu.br',
    status: 'Ativo',
    convidadoEm: '2026-07-18',
  },
  {
    id: '3',
    email: 'carla.mendes@horizonte.edu.br',
    status: 'Pendente',
    convidadoEm: '2026-08-01',
  },
  {
    id: '4',
    email: 'rafael.costa@horizonte.edu.br',
    status: 'Pendente',
    convidadoEm: '2026-08-02',
  },
]

function formatDate(iso) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function StatusBadge({ status }) {
  const active = status === 'Ativo'
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
        active ? 'bg-school-50 text-school-700' : 'bg-amber-50 text-amber-800',
      ].join(' ')}
    >
      {status}
    </span>
  )
}

export default function TeamManagement() {
  const [email, setEmail] = useState('')
  const [team, setTeam] = useState(INITIAL_TEAM)
  const [feedback, setFeedback] = useState('')

  const ordered = useMemo(
    () =>
      [...team].sort((a, b) => {
        if (a.status !== b.status) return a.status === 'Pendente' ? -1 : 1
        return b.convidadoEm.localeCompare(a.convidadoEm)
      }),
    [team],
  )

  function handleInvite(e) {
    e.preventDefault()
    const value = email.trim().toLowerCase()
    if (!value || !value.includes('@')) {
      setFeedback('Informe um e-mail válido.')
      return
    }
    if (team.some((t) => t.email.toLowerCase() === value)) {
      setFeedback('Este professor já está na lista.')
      return
    }
    const today = new Date()
    const iso = today.toISOString().slice(0, 10)
    setTeam((prev) => [
      {
        id: String(Date.now()),
        email: value,
        status: 'Pendente',
        convidadoEm: iso,
      },
      ...prev,
    ])
    setEmail('')
    setFeedback(`Convite simulado enviado para ${value}.`)
  }

  function handleRevoke(id) {
    const row = team.find((t) => t.id === id)
    if (!row) return
    if (!window.confirm(`Revogar vínculo de ${row.email}?`)) return
    setTeam((prev) => prev.filter((t) => t.id !== id))
    setFeedback(`Vínculo de ${row.email} removido (mock).`)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Minha Equipe</h1>
        <p className="mt-1 text-sm text-muted">
          Convide professores por e-mail e acompanhe o status do vínculo com o B2C.
        </p>
      </div>

      <form
        onSubmit={handleInvite}
        className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:flex-row sm:items-end"
      >
        <label className="min-w-0 flex-1">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            E-mail do Professor
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="professor@escola.edu.br"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
          />
        </label>
        <button
          type="submit"
          className="shrink-0 rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600"
        >
          Convidar Professor
        </button>
      </form>

      {feedback ? (
        <p className="text-sm text-school-700" role="status">
          {feedback}
        </p>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">E-mail</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Data do Convite</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {ordered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted">
                    Nenhum professor vinculado ainda.
                  </td>
                </tr>
              ) : (
                ordered.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-3 font-medium text-ink">{row.email}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="px-4 py-3 tabular-nums text-muted">
                      {formatDate(row.convidadoEm)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        title="Revogar vínculo"
                        onClick={() => handleRevoke(row.id)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-muted transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"
                      >
                        <TrashIcon />
                        Revogar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
