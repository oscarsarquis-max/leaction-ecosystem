import { useCallback, useMemo, useState } from 'react'
import axios from 'axios'
import {
  AlertTriangle,
  GitBranch,
  Loader2,
  Sparkles,
  Wand2,
} from 'lucide-react'

/**
 * Crystal Ball — painel aditivo (não altera a visualização do pipeline).
 */
export default function CrystalBallPanel({ apiBase, activeRunId, onError }) {
  const [lineage, setLineage] = useState(null)
  const [loadingLineage, setLoadingLineage] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [shadowRunId, setShadowRunId] = useState(null)
  const [editJson, setEditJson] = useState('{\n  "nota": "edite o artefato aqui"\n}')
  const [busy, setBusy] = useState(null)
  const [compare, setCompare] = useState(null)
  const [previewText, setPreviewText] = useState('')
  const [previewResult, setPreviewResult] = useState(null)

  const loadLineage = useCallback(async () => {
    if (!activeRunId) {
      onError?.('Selecione um run oficial no histórico para ver a linhagem.')
      return
    }
    setLoadingLineage(true)
    setCompare(null)
    try {
      const { data } = await axios.get(
        `${apiBase}/api/crystal-ball/${activeRunId}/lineage`,
      )
      setLineage(data)
      setSelectedPhase(null)
      setShadowRunId(null)
    } catch (err) {
      onError?.(err.response?.data?.detail || err.message || 'Falha lineage')
    } finally {
      setLoadingLineage(false)
    }
  }, [activeRunId, apiBase, onError])

  const nodes = lineage?.nodes || []

  const handleFork = async () => {
    if (!activeRunId || !selectedPhase) return
    setBusy('fork')
    try {
      const { data } = await axios.post(
        `${apiBase}/api/crystal-ball/${activeRunId}/fork`,
        { fork_phase_id: selectedPhase },
      )
      setShadowRunId(data.shadow_run_id)
      setCompare(null)
    } catch (err) {
      onError?.(err.response?.data?.detail || err.message || 'Falha fork')
    } finally {
      setBusy(null)
    }
  }

  const handleEditAndRecalc = async () => {
    if (!shadowRunId || !selectedPhase) return
    setBusy('recalc')
    try {
      let artifact
      try {
        artifact = JSON.parse(editJson)
      } catch {
        onError?.('JSON de edição inválido')
        setBusy(null)
        return
      }
      await axios.post(
        `${apiBase}/api/crystal-ball/shadow/${shadowRunId}/edit`,
        { phase_id: selectedPhase, artifact_data: artifact },
      )
      const { data } = await axios.post(
        `${apiBase}/api/crystal-ball/shadow/${shadowRunId}/recalculate`,
      )
      setCompare(data)
    } catch (err) {
      onError?.(err.response?.data?.detail || err.message || 'Falha recalculate')
    } finally {
      setBusy(null)
    }
  }

  const handlePreview = async () => {
    setBusy('preview')
    try {
      const { data } = await axios.post(
        `${apiBase}/api/crystal-ball/quick-preview`,
        {
          text: previewText,
          link_source_run_id: activeRunId || undefined,
        },
      )
      setPreviewResult(data)
    } catch (err) {
      onError?.(err.response?.data?.detail || err.message || 'Falha preview')
    } finally {
      setBusy(null)
    }
  }

  const edgeHint = useMemo(() => {
    if (!lineage?.edges?.length) return 'Sem arestas (inputs_used / depends_on).'
    return `${lineage.edges.length} dependência(s) no grafo.`
  }, [lineage])

  return (
    <section
      className="rounded-2xl border border-violet-200 bg-violet-50/40 p-6 shadow-sm backdrop-blur"
      data-testid="crystal-ball-panel"
    >
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="text-left">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-violet-700">
            Crystal Ball
          </p>
          <h2 className="font-display mt-1 text-2xl font-semibold text-slate-950">
            Proveniência · What-if · Prévia
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Subsistema aditivo: simulações em shadow run — o pipeline oficial não é
            alterado. Prévia marcada como <code className="text-xs">is_preview</code>.
          </p>
        </div>
        <button
          type="button"
          onClick={loadLineage}
          disabled={loadingLineage || !activeRunId}
          className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
        >
          {loadingLineage ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <GitBranch className="h-4 w-4" />
          )}
          Carregar linhagem do run
        </button>
      </div>

      {!activeRunId ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Selecione um run no histórico para explorar a linhagem.
        </p>
      ) : null}

      {lineage ? (
        <div className="mt-4 space-y-4">
          <p className="text-xs text-slate-500">
            Run <span className="font-mono">{lineage.run_id}</span> · {edgeHint}
          </p>
          <div className="flex flex-wrap gap-2">
            {nodes.map((n) => (
              <button
                key={n.phase_id}
                type="button"
                onClick={() => setSelectedPhase(n.phase_id)}
                className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                  selectedPhase === n.phase_id
                    ? 'border-violet-500 bg-violet-100 ring-2 ring-violet-300'
                    : 'border-slate-200 bg-white hover:border-violet-300'
                }`}
              >
                <div className="font-semibold text-slate-800">{n.name}</div>
                <div className="font-mono text-[10px] text-slate-500">{n.phase_id}</div>
                <div className="mt-1 text-[10px] text-slate-500">
                  {n.status}
                  {n.quality_score != null ? ` · Q${n.quality_score}` : ''}
                </div>
                {n.inputs_used?.length ? (
                  <div className="mt-1 max-w-[12rem] truncate text-[10px] text-violet-700">
                    ← {n.inputs_used.join(', ')}
                  </div>
                ) : null}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={!selectedPhase || busy}
              onClick={handleFork}
              className="inline-flex items-center gap-2 rounded-lg border border-violet-400 bg-white px-3 py-2 text-sm text-violet-900 hover:bg-violet-50 disabled:opacity-50"
            >
              {busy === 'fork' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}
              Fork a partir da fase selecionada
            </button>
            {shadowRunId ? (
              <span className="font-mono text-xs text-slate-600">
                shadow={shadowRunId}
              </span>
            ) : null}
          </div>

          {shadowRunId ? (
            <div className="rounded-xl border border-violet-200 bg-white p-4">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Editar artefato do nó (JSON) e recalcular downstream
              </label>
              <textarea
                className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-xs"
                rows={8}
                value={editJson}
                onChange={(e) => setEditJson(e.target.value)}
              />
              <button
                type="button"
                disabled={busy}
                onClick={handleEditAndRecalc}
                className="mt-2 inline-flex items-center gap-2 rounded-lg bg-violet-700 px-3 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
              >
                {busy === 'recalc' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Editar e recalcular a partir daqui
              </button>
            </div>
          ) : null}

          {compare ? (
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Original Q={compare.original_quality_score ?? '—'}
                </p>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-700">
                  {compare.original_prompt || '(sem prompt_cursor)'}
                </pre>
              </div>
              <div className="rounded-xl border border-violet-300 bg-violet-50/50 p-3">
                <p className="text-xs font-semibold uppercase text-violet-800">
                  Fork Q={compare.predicted_quality_score ?? '—'} · simulação
                </p>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-700">
                  {compare.predicted_prompt || '(sem prompt previsto)'}
                </pre>
                <p className="mt-2 text-[11px] text-violet-800">
                  prompt_changed={String(compare.prompt_changed)} · status=
                  {compare.status}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="mt-6 border-t border-violet-200 pt-4">
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-slate-800">
              Prévia rápida (sem Spec / sem run oficial)
            </p>
            <p className="text-xs text-slate-500">
              Uma chamada reduzida — resultado efêmero com{' '}
              <code>is_preview: true</code>.
            </p>
            <textarea
              className="mt-2 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm"
              rows={4}
              placeholder="Descreva o que deseja construir…"
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
            />
            <button
              type="button"
              disabled={busy || !previewText.trim()}
              onClick={handlePreview}
              className="mt-2 inline-flex items-center gap-2 rounded-lg border border-amber-400 bg-amber-50 px-3 py-2 text-sm text-amber-950 hover:bg-amber-100 disabled:opacity-50"
            >
              {busy === 'preview' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Gerar prévia
            </button>
            {previewResult ? (
              <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3">
                <p className="text-[11px] font-semibold text-amber-900">
                  is_preview={String(previewResult.is_preview)} · confidence=
                  {previewResult.confidence}
                </p>
                <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap text-xs text-slate-800">
                  {previewResult.preview_prompt}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
