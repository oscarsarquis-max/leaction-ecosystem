import { useCallback, useEffect, useState } from 'react'
import {
  Check,
  FileText,
  GitBranch,
  Loader2,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react'

function formatWhen(value) {
  if (!value) return '—'
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return String(value)
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(value)
  }
}

/**
 * Busca projetos aceitos (imutáveis) e oferece retorno / evolução.
 * No retorno, ao final: resumo da melhoria Phanton + Aceitar/Rejeitar.
 */
export default function AcceptedProjectsPanel({
  apiBase,
  onSubstituteCreated,
  onError,
}) {
  const [query, setQuery] = useState('')
  const [version, setVersion] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)
  const [mode, setMode] = useState(null) // 'retorno' | 'evolucao'
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [phantonProposal, setPhantonProposal] = useState(null)
  const [deciding, setDeciding] = useState(false)

  const search = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: 40 }
      if (query.trim()) params.q = query.trim()
      if (version.trim()) params.version = version.trim()
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(`${apiBase}/api/projects/search?${qs}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setItems(data.items || [])
    } catch (err) {
      onError?.(err.message || 'Falha na busca de projetos')
    } finally {
      setLoading(false)
    }
  }, [apiBase, query, version, onError])

  useEffect(() => {
    search()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps -- carga inicial

  const openMode = (item, nextMode) => {
    setSelected(item)
    setMode(nextMode)
    setText('')
    setPhantonProposal(null)
  }

  const cancelMode = () => {
    setMode(null)
    setText('')
  }

  const submit = async () => {
    if (!selected || !mode) return
    const trimmed = text.trim()
    if (trimmed.length < 20) {
      onError?.('Descreva com pelo menos 20 caracteres para a reanálise.')
      return
    }
    setSubmitting(true)
    try {
      const path =
        mode === 'retorno'
          ? `${apiBase}/api/pipeline/${selected.run_id}/retorno`
          : `${apiBase}/api/pipeline/${selected.run_id}/evolve`
      const body =
        mode === 'retorno' ? { content: trimmed } : { request: trimmed }
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail || `HTTP ${res.status}`),
        )
      }
      const wasRetorno = mode === 'retorno'
      cancelMode()
      if (wasRetorno && data.phanton_improvement) {
        setPhantonProposal(data.phanton_improvement)
      } else {
        setPhantonProposal(null)
      }
      onSubstituteCreated?.(data)
      await search()
    } catch (err) {
      onError?.(err.message || 'Falha ao criar pipeline substituto')
    } finally {
      setSubmitting(false)
    }
  }

  const decideImprovement = async (decision) => {
    if (!phantonProposal?.id) return
    setDeciding(true)
    try {
      const res = await fetch(
        `${apiBase}/api/phanton-improvements/${phantonProposal.id}/decide`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision }),
        },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail || `HTTP ${res.status}`),
        )
      }
      setPhantonProposal((prev) =>
        prev
          ? {
              ...prev,
              status: data.status,
              decided_at: data.decided_at,
            }
          : null,
      )
    } catch (err) {
      onError?.(err.message || 'Falha ao registrar a decisão')
    } finally {
      setDeciding(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-left">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Pós-aceitação
          </p>
          <h2 className="font-display mt-1 text-xl font-semibold text-slate-950">
            Projetos aceitos
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Busque por projeto e versão. A versão aceita é imutável — retorno ou
            evolução geram um pipeline substituto com nova versão (reanálise). No
            retorno, melhorias do Phanton pedem aceitação ou rejeição explícita.
          </p>
        </div>
        <ShieldCheck className="h-5 w-5 text-emerald-600" />
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="min-w-0 flex-1 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
          Projeto
          <div className="relative mt-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="nome ou chave…"
              className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
            />
          </div>
        </label>
        <label className="w-full text-left text-xs font-semibold uppercase tracking-wider text-slate-500 sm:w-36">
          Versão
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="ex. 1.0"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
          />
        </label>
        <button
          type="button"
          onClick={search}
          disabled={loading}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Buscar
        </button>
      </div>

      {!loading && !items.length ? (
        <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          Nenhum projeto aceito encontrado. Conclua um pipeline e use Aceitar
          projeto para liberar retorno e evolução.
        </p>
      ) : null}

      {items.length ? (
        <ul className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1">
          {items.map((item) => {
            const active = selected && String(selected.run_id) === String(item.run_id)
            return (
              <li
                key={item.run_id}
                className={`rounded-xl border px-4 py-3 ${
                  active
                    ? 'border-emerald-400 bg-emerald-50/80'
                    : 'border-slate-200 bg-white'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 text-left">
                    <p className="truncate font-display text-sm font-semibold text-slate-900">
                      {item.project_name}
                    </p>
                    <p className="mt-0.5 font-mono text-[11px] text-slate-500">
                      {item.project_key} · v{item.version}
                      <span className="mx-1.5 text-slate-300">·</span>
                      aceito {formatWhen(item.accepted_at)}
                    </p>
                  </div>
                  <span className="inline-flex rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800">
                    imutável
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openMode(item, 'retorno')}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition hover:border-indigo-300 hover:bg-indigo-50"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Retorno do implementador
                  </button>
                  <button
                    type="button"
                    onClick={() => openMode(item, 'evolucao')}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 transition hover:border-amber-300 hover:bg-amber-50"
                  >
                    <GitBranch className="h-3.5 w-3.5" />
                    Manutenção / evolução
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      ) : null}

      {mode && selected ? (
        <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 text-left">
          <p className="font-display text-sm font-semibold text-slate-900">
            {mode === 'retorno'
              ? 'Arquivo de retorno (reanálise)'
              : 'Pedido de evolução (reanálise)'}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {selected.project_name} · v{selected.version} → nova versão substituta.
            A versão aceita não será alterada.
            {mode === 'retorno'
              ? ' Use seções ## Retorno — pipeline e ## Retorno — Phanton.'
              : ''}
          </p>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder={
              mode === 'retorno'
                ? '## Retorno — pipeline\n…desvios / o que mudou na construção…\n\n## Retorno — Phanton\n…melhorias na ferramenta…'
                : 'Descreva a evolução ou manutenção desejada…'
            }
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-200"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={submit}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
            >
              {submitting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : null}
              Reanalisar e criar pipeline substituto
            </button>
            <button
              type="button"
              onClick={cancelMode}
              disabled={submitting}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      ) : null}

      {phantonProposal ? (
        <div className="mt-4 rounded-xl border border-violet-300 bg-violet-50/80 p-4 text-left shadow-[0_0_0_1px_rgba(139,92,246,0.2)]">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.18em] text-violet-700">
            Melhoria proposta no Phanton
          </p>
          <h3 className="font-display mt-1 text-base font-semibold text-slate-950">
            {phantonProposal.title}
          </h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {phantonProposal.summary}
          </p>
          {Array.isArray(phantonProposal.items) && phantonProposal.items.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-700">
              {phantonProposal.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}

          {phantonProposal.status === 'pending' ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={deciding}
                onClick={() => decideImprovement('aceitar')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
              >
                {deciding ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Check className="h-3.5 w-3.5" />
                )}
                Aceitar melhoria no Phanton
              </button>
              <button
                type="button"
                disabled={deciding}
                onClick={() => decideImprovement('rejeitar')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-4 py-2 text-xs font-semibold text-red-800 transition hover:bg-red-50 disabled:opacity-60"
              >
                <X className="h-3.5 w-3.5" />
                Rejeitar
              </button>
            </div>
          ) : (
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-600">
              Decisão:{' '}
              {phantonProposal.status === 'accepted' ? 'aceita' : 'rejeitada'}
            </p>
          )}
        </div>
      ) : null}
    </section>
  )
}
