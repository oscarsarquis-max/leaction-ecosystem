import { useEffect, useState } from 'react'
import { useInstituicaoId } from '../lib/auth'
import { BTN_PRIMARY } from '../lib/buttons'

/**
 * Quadro de Avisos — cria avisos curtos fixados na Mesa do Professor (Inove).
 */
export default function RadarAvisosPanel() {
  const INSTITUICAO_ID = useInstituicaoId()
  const [avisos, setAvisos] = useState([])
  const [turmas, setTurmas] = useState([])
  const [disciplinas, setDisciplinas] = useState([])
  const [texto, setTexto] = useState('')
  const [turmaId, setTurmaId] = useState('')
  const [disciplinaId, setDisciplinaId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')

  async function load() {
    if (!INSTITUICAO_ID) return
    setError('')
    try {
      const [rA, rO] = await Promise.all([
        fetch(`/api/instituicoes/${INSTITUICAO_ID}/avisos-mesa?ativos=1`, {
          credentials: 'include',
        }),
        fetch(`/api/instituicoes/${INSTITUICAO_ID}/avisos-mesa/opcoes`, {
          credentials: 'include',
        }),
      ])
      const jA = await rA.json().catch(() => [])
      const jO = await rO.json().catch(() => ({}))
      if (!rA.ok) throw new Error(jA.error || 'Falha ao carregar avisos')
      setAvisos(Array.isArray(jA) ? jA : [])
      if (rO.ok) {
        setTurmas(jO.turmas || [])
        setDisciplinas(jO.disciplinas || [])
      }
    } catch (err) {
      setError(err.message || 'Erro ao carregar avisos')
    }
  }

  useEffect(() => {
    load()
  }, [INSTITUICAO_ID])

  async function handleCreate(e) {
    e.preventDefault()
    if (!INSTITUICAO_ID) return
    setBusy(true)
    setError('')
    setOk('')
    try {
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/avisos-mesa`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texto: texto.trim(),
          turma_id: turmaId || null,
          disciplina_id: disciplinaId || null,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível publicar o aviso')
      setTexto('')
      setTurmaId('')
      setDisciplinaId('')
      setOk(
        body.b2c_push?.ok
          ? 'Aviso publicado e enviado à Mesa do Professor.'
          : 'Aviso salvo. Sync Inove pendente (verifique a ponte S2S).',
      )
      await load()
    } catch (err) {
      setError(err.message || 'Erro ao criar aviso')
    } finally {
      setBusy(false)
    }
  }

  async function desativar(id) {
    setBusy(true)
    setError('')
    try {
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/avisos-mesa/${id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativo: false }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao desativar')
      await load()
    } catch (err) {
      setError(err.message || 'Erro')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4 p-4 sm:p-5">
      <div>
        <h3 className="text-sm font-semibold text-ink">Quadro de Avisos</h3>
        <p className="mt-1 text-xs text-muted">
          Texto curto fixado no topo dos cards da Mesa do Professor (Inove). Vincule a uma
          turma/disciplina ou publique para todos.
        </p>
      </div>

      <form
        onSubmit={handleCreate}
        className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3"
      >
        <label className="block">
          <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
            Aviso
          </span>
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={3}
            maxLength={500}
            required
            placeholder="Ex.: Nesta semana, priorize a rotina de fechamento com os alunos…"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
          />
          <span className="mt-0.5 block text-right text-[10px] text-muted">
            {texto.length}/500
          </span>
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Disciplina (opcional)
            </span>
            <select
              value={disciplinaId}
              onChange={(e) => setDisciplinaId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-school-500"
            >
              <option value="">Todas</option>
              {disciplinas.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Turma (opcional)
            </span>
            <select
              value={turmaId}
              onChange={(e) => setTurmaId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-school-500"
            >
              <option value="">Todas</option>
              {turmas.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label || t.nome}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button type="submit" disabled={busy || !texto.trim()} className={BTN_PRIMARY}>
          {busy ? 'Publicando…' : 'Publicar aviso'}
        </button>
      </form>

      {ok ? <p className="text-sm text-school-700">{ok}</p> : null}
      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
        {avisos.length === 0 ? (
          <li className="px-4 py-6 text-center text-sm text-muted">
            Nenhum aviso ativo.
          </li>
        ) : (
          avisos.map((a) => (
            <li
              key={a.id}
              className="flex flex-wrap items-start justify-between gap-3 px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink">{a.texto}</p>
                <p className="mt-1 text-[11px] text-muted">{a.publico_label}</p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => desativar(a.id)}
                className="shrink-0 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-semibold text-muted hover:border-red-200 hover:bg-red-50 hover:text-red-700"
              >
                Desativar
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
