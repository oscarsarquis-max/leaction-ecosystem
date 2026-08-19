import { useCallback, useMemo, useState } from 'react'
import {
  AlertTriangle,
  Beaker,
  GitBranch,
  Loader2,
  Sparkles,
  Wand2,
} from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import { createAuthedAxios } from '../auth/AuthContext'
import { formatArtifactPlainText } from '../lib/artifactPlainText'

const SIM_PHASE_ORDER = [
  'context7_mativas',
  'methodology',
  'synthesize',
  'entrega_final',
]

const DEFAULT_SIM_PROMPT =
  'Sou professora do ensino médio. Desafio: os alunos não conseguem aplicar o que aprenderam em situações reais da comunidade. Quero um roteiro de aula presencial com Aprendizagem Baseada em Problemas (PBL), turmas de 1º ano, disciplina de Biologia, 2 aulas geminadas de 50 minutos.'

/**
 * Crystal Ball — painel aditivo com abas separadas:
 * Proveniência (runs reais) · Simulação (Mativas) · Prévia rápida
 *
 * mode="restricted" → só Simulação (testadores externos).
 */
export default function CrystalBallPanel({
  apiBase,
  activeRunId,
  onError,
  mode = 'full',
}) {
  const restricted = mode === 'restricted'
  const api = useMemo(() => createAuthedAxios(apiBase), [apiBase])
  const [tab, setTab] = useState(restricted ? 'simulacao' : 'proveniencia')

  // —— Proveniência (runs reais) ——
  const [lineage, setLineage] = useState(null)
  const [loadingLineage, setLoadingLineage] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [shadowRunId, setShadowRunId] = useState(null)
  const [editJson, setEditJson] = useState('{\n  "nota": "edite o artefato aqui"\n}')
  const [busy, setBusy] = useState(null)
  const [compare, setCompare] = useState(null)

  // —— Prévia ——
  const [previewText, setPreviewText] = useState('')
  const [previewResult, setPreviewResult] = useState(null)

  // —— Simulação Mativas ——
  const [simPrompt, setSimPrompt] = useState(DEFAULT_SIM_PROMPT)
  const [simMetodologia, setSimMetodologia] = useState(
    'Aprendizagem Baseada em Problemas',
  )
  const [simShadowId, setSimShadowId] = useState(null)
  const [simPhases, setSimPhases] = useState([])
  const [simSelected, setSimSelected] = useState('context7_mativas')
  const [simEditJson, setSimEditJson] = useState('')
  const [simComparison, setSimComparison] = useState(null)
  const [simStatus, setSimStatus] = useState(null)
  // —— Prompt Lab (corpus genérico / ciclos) ——
  const [simHistory, setSimHistory] = useState([]) // [{id, metodologia, nota}]
  const [labCorpusId, setLabCorpusId] = useState('mativas')
  const [labSugestaoMd, setLabSugestaoMd] = useState('')
  const [labCiclos, setLabCiclos] = useState([])
  const [labRealPayload, setLabRealPayload] = useState('')
  const [labRealChave, setLabRealChave] = useState(
    'Aprendizagem Baseada em Problemas',
  )
  const [labRealCiclo, setLabRealCiclo] = useState('')
  const [labRealResult, setLabRealResult] = useState(null)
  const [labPromptMestre, setLabPromptMestre] = useState('')

  const loadLineage = useCallback(async () => {
    if (!activeRunId) {
      onError?.('Selecione um run oficial no histórico para ver a linhagem.')
      return
    }
    setLoadingLineage(true)
    setCompare(null)
    try {
      const { data } = await api.get(
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
      const { data } = await api.post(
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
      await api.post(
        `${apiBase}/api/crystal-ball/shadow/${shadowRunId}/edit`,
        { phase_id: selectedPhase, artifact_data: artifact },
      )
      const { data } = await api.post(
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
      const { data } = await api.post(
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

  const applySimPhases = (phases, selectId) => {
    const list = Array.isArray(phases) ? phases : []
    setSimPhases(list)
    const pick =
      selectId ||
      simSelected ||
      list.find((p) => p.phase_id === 'context7_mativas')?.phase_id ||
      list[0]?.phase_id
    if (pick) {
      setSimSelected(pick)
      const row = list.find((p) => p.phase_id === pick)
      setSimEditJson(
        JSON.stringify(row?.artifact_data ?? { artifact_data: {} }, null, 2),
      )
    }
  }

  const hydrateSimFromShadow = async (shadowId, selectId) => {
    const { data } = await api.get(
      `${apiBase}/api/crystal-ball/shadow/${shadowId}`,
      { timeout: 60000 },
    )
    if (data?.status) setSimStatus(data.status)
    applySimPhases(data?.phases, selectId)
    return data
  }

  const phaseCardStatus = (p) => {
    const art = p?.artifact_data
    if (art?.status === 'error' || art?.artifact_data?.erro) return 'error'
    return p?.status || '—'
  }

  const handleSimRun = async () => {
    setBusy('sim-run')
    setSimComparison(null)
    try {
      const { data } = await api.post(
        `${apiBase}/api/crystal-ball/experimental-run`,
        { user_prompt: simPrompt, metodologia: simMetodologia },
        { timeout: 300000 },
      )
      setSimShadowId(data.shadow_run_id)
      setSimStatus(data.status)
      setSimComparison(data.comparison || null)
      if (data.shadow_run_id) {
        setSimHistory((prev) => {
          const next = [
            {
              id: data.shadow_run_id,
              metodologia: data.metodologia || simMetodologia,
              nota:
                data.comparison?.nota_agregada ??
                data.comparison?.identical_ratio ??
                null,
            },
            ...prev.filter((x) => x.id !== data.shadow_run_id),
          ]
          return next.slice(0, 20)
        })
      }
      if (Array.isArray(data.phases) && data.phases.length > 0) {
        applySimPhases(data.phases, 'context7_mativas')
      } else if (data.shadow_run_id) {
        // Fallback: POST sem phases (BE antigo) — hidrata do GET shadow
        await hydrateSimFromShadow(data.shadow_run_id, 'context7_mativas')
      }
      if (Array.isArray(data.errors) && data.errors.length) {
        onError?.(
          `Simulação parcial: ${data.errors.map((e) => e.error || e.phase_id).join('; ')}`,
        )
      }
    } catch (err) {
      onError?.(
        err.response?.data?.detail || err.message || 'Falha experimental-run',
      )
    } finally {
      setBusy(null)
    }
  }

  const handleLabSugestao = async () => {
    if (simHistory.length < 2) {
      onError?.('Rode pelo menos 2 simulações antes de gerar a sugestão.')
      return
    }
    setBusy('lab-sugestao')
    try {
      const { data } = await api.post(
        `${apiBase}/api/crystal-ball/corpus/${labCorpusId}/sugestao-prompt`,
        {
          shadow_run_ids: simHistory.slice(0, 8).map((x) => x.id),
          prompt_mestre: labPromptMestre || null,
        },
      )
      setLabSugestaoMd(data?.sugestao?.markdown || '')
      const { data: ciclos } = await api.get(
        `${apiBase}/api/crystal-ball/corpus/${labCorpusId}/ciclos`,
      )
      setLabCiclos(ciclos?.items || [])
    } catch (err) {
      onError?.(
        err.response?.data?.detail || err.message || 'Falha sugestão de prompt',
      )
    } finally {
      setBusy(null)
    }
  }

  const handleLabLoadCiclos = async () => {
    setBusy('lab-ciclos')
    try {
      const { data } = await api.get(
        `${apiBase}/api/crystal-ball/corpus/${labCorpusId}/ciclos`,
      )
      setLabCiclos(data?.items || [])
    } catch (err) {
      onError?.(err.response?.data?.detail || err.message || 'Falha ciclos')
    } finally {
      setBusy(null)
    }
  }

  const handleLabResultadoReal = async () => {
    setBusy('lab-real')
    setLabRealResult(null)
    try {
      let payload = labRealPayload
      try {
        payload = JSON.parse(labRealPayload)
      } catch {
        /* texto puro ok */
      }
      const body = {
        chave_valor: labRealChave,
        payload,
        desafio_texto: simPrompt,
      }
      if (labRealCiclo.trim()) {
        body.numero_ciclo = Number(labRealCiclo)
      }
      const { data } = await api.post(
        `${apiBase}/api/crystal-ball/corpus/${labCorpusId}/resultado-real`,
        body,
      )
      setLabRealResult(data)
      await handleLabLoadCiclos()
    } catch (err) {
      onError?.(
        err.response?.data?.detail || err.message || 'Falha resultado real',
      )
    } finally {
      setBusy(null)
    }
  }

  const handleSimReload = async () => {
    if (!simShadowId) return
    setBusy('sim-reload')
    try {
      await hydrateSimFromShadow(simShadowId, simSelected || 'context7_mativas')
    } catch (err) {
      onError?.(
        err.response?.data?.detail || err.message || 'Falha ao recarregar shadow',
      )
    } finally {
      setBusy(null)
    }
  }

  const handleSimSelectPhase = (phaseId) => {
    setSimSelected(phaseId)
    const row = simPhases.find((p) => p.phase_id === phaseId)
    setSimEditJson(
      JSON.stringify(row?.artifact_data ?? { artifact_data: {} }, null, 2),
    )
  }

  const handleSimEditRecalc = async () => {
    if (!simShadowId || !simSelected) return
    setBusy('sim-recalc')
    try {
      let artifact
      try {
        artifact = JSON.parse(simEditJson)
      } catch {
        onError?.('JSON de edição inválido na Simulação')
        setBusy(null)
        return
      }
      const { data } = await api.post(
        `${apiBase}/api/crystal-ball/experimental-run/${simShadowId}/recalculate`,
        { from_phase_id: simSelected, artifact_data: artifact },
        { timeout: 300000 },
      )
      setSimStatus(data.status)
      setSimComparison(data.comparison || null)
      applySimPhases(data.phases, simSelected)
    } catch (err) {
      onError?.(
        err.response?.data?.detail ||
          err.message ||
          'Falha experimental recalculate',
      )
    } finally {
      setBusy(null)
    }
  }

  const edgeHint = useMemo(() => {
    if (!lineage?.edges?.length) return 'Sem arestas (inputs_used / depends_on).'
    return `${lineage.edges.length} dependência(s) no grafo.`
  }, [lineage])

  const orderedSimPhases = useMemo(() => {
    const byId = Object.fromEntries(
      (simPhases || []).map((p) => [p.phase_id, p]),
    )
    return SIM_PHASE_ORDER.map(
      (id) =>
        byId[id] || {
          phase_id: id,
          status: '—',
          origin: null,
          quality_score: null,
        },
    )
  }, [simPhases])

  const simPlainText = useMemo(() => {
    try {
      return formatArtifactPlainText(JSON.parse(simEditJson))
    } catch {
      return ''
    }
  }, [simEditJson])

  const tabs = (
    restricted
      ? [{ id: 'simulacao', label: 'Simulação', icon: Beaker }]
      : [
          { id: 'proveniencia', label: 'Proveniência', icon: GitBranch },
          { id: 'simulacao', label: 'Simulação', icon: Beaker },
          { id: 'previa', label: 'Prévia rápida', icon: Sparkles },
        ]
  )

  return (
    <section
      className="rounded-2xl border border-violet-200 bg-violet-50/40 p-6 shadow-sm backdrop-blur"
      data-testid="crystal-ball-panel"
    >
      <div className="mb-4 text-left">
        <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-violet-700">
          Crystal Ball
        </p>
        <h2 className="font-display mt-1 text-2xl font-semibold text-slate-950">
          {restricted
            ? 'Simulação Mativas'
            : 'Proveniência · Simulação · Prévia'}
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          {restricted
            ? 'Experimento shadow-only com grounding Mativas. Sem acesso ao pipeline oficial.'
            : 'Subsistema aditivo. A aba Simulação é independente da Proveniência de runs reais — edições shadow não alteram o pipeline oficial.'}
        </p>
      </div>

      {!restricted ? (
      <div className="mb-4 flex flex-wrap gap-2 border-b border-violet-200 pb-3">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            data-testid={`crystal-tab-${id}`}
            onClick={() => setTab(id)}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
              tab === id
                ? 'bg-violet-700 text-white'
                : 'bg-white text-violet-900 border border-violet-200 hover:bg-violet-50'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>
      ) : null}

      {!restricted && tab === 'proveniencia' ? (
        <div data-testid="crystal-tab-proveniencia-panel">
          <div className="mb-3 flex flex-wrap items-center gap-2">
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
              Selecione um run no histórico para explorar a linhagem (auditoria
              de runs reais).
            </p>
          ) : null}

          {lineage ? (
            <div className="mt-4 space-y-4">
              <p className="text-xs text-slate-500">
                Run <span className="font-mono">{lineage.run_id}</span> ·{' '}
                {edgeHint}
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
                    <div className="font-mono text-[10px] text-slate-500">
                      {n.phase_id}
                    </div>
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
        </div>
      ) : null}

      {restricted || tab === 'simulacao' ? (
        <div data-testid="crystal-tab-simulacao-panel" className="space-y-4">
          <p className="text-sm text-slate-600">
            Experimento Mativas-grounded (shadow-only): lookup real → methodology →
            synthesize → entrega. Edite qualquer card e recalcule só o
            downstream — o corpus e os runs oficiais não são tocados.
          </p>

          <div className="grid gap-3 lg:grid-cols-2">
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Metodologia</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                value={simMetodologia}
                onChange={(e) => setSimMetodologia(e.target.value)}
              />
            </label>
            <div className="flex items-end">
              <button
                type="button"
                disabled={busy || !simPrompt.trim() || !simMetodologia.trim()}
                onClick={handleSimRun}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
              >
                {busy === 'sim-run' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Beaker className="h-4 w-4" />
                )}
                Rodar simulação Mativas
              </button>
            </div>
          </div>

          <label className="block text-sm">
            <span className="font-semibold text-slate-700">Pedido / desafio</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white p-2 text-sm"
              rows={4}
              value={simPrompt}
              onChange={(e) => setSimPrompt(e.target.value)}
            />
          </label>

          {simShadowId ? (
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <p>
                shadow experimental{' '}
                <span className="font-mono">{simShadowId}</span>
                {simStatus ? ` · ${simStatus}` : ''}
              </p>
              <button
                type="button"
                disabled={!!busy}
                onClick={handleSimReload}
                className="rounded-md border border-teal-300 bg-white px-2 py-1 text-teal-900 hover:bg-teal-50 disabled:opacity-50"
              >
                {busy === 'sim-reload' ? 'Recarregando…' : 'Recarregar fases'}
              </button>
            </div>
          ) : null}

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {orderedSimPhases.map((p) => {
              const st = phaseCardStatus(p)
              const isErr = st === 'error'
              return (
              <button
                key={p.phase_id}
                type="button"
                data-testid={`sim-phase-${p.phase_id}`}
                onClick={() => handleSimSelectPhase(p.phase_id)}
                className={`rounded-xl border px-3 py-3 text-left text-xs transition ${
                  simSelected === p.phase_id
                    ? 'border-teal-500 bg-teal-50 ring-2 ring-teal-300'
                    : isErr
                      ? 'border-rose-300 bg-rose-50 hover:border-rose-400'
                      : 'border-slate-200 bg-white hover:border-teal-300'
                }`}
              >
                <div className="font-semibold text-slate-800">{p.phase_id}</div>
                <div className={`mt-1 text-[10px] ${isErr ? 'text-rose-700' : 'text-slate-500'}`}>
                  {st}
                  {p.origin ? ` · ${p.origin}` : ''}
                  {p.quality_score != null ? ` · Q${p.quality_score}` : ''}
                </div>
              </button>
              )
            })}
          </div>

          {simShadowId ? (
            <div className="space-y-4 rounded-xl border border-teal-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Artefato · {simSelected}
              </p>

              <CopyableBlock label="Copiar texto" text={simPlainText || ''}>
                <div>
                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-teal-800">
                    Texto
                  </p>
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-teal-100 bg-teal-50/40 p-3 text-xs leading-relaxed text-slate-800">
                    {simPlainText ||
                      '(sem texto legível — confira o JSON ou rode a simulação)'}
                  </pre>
                </div>
              </CopyableBlock>

              <CopyableBlock label="Copiar JSON" text={simEditJson || ''}>
                <div>
                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    JSON (editável)
                  </p>
                  <textarea
                    className="max-h-96 w-full resize-y overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-xs leading-relaxed text-slate-800"
                    rows={12}
                    value={simEditJson}
                    onChange={(e) => setSimEditJson(e.target.value)}
                    aria-label={`JSON da fase ${simSelected}`}
                  />
                </div>
              </CopyableBlock>

              <button
                type="button"
                disabled={busy || !simSelected}
                onClick={handleSimEditRecalc}
                className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
              >
                {busy === 'sim-recalc' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )}
                Editar e recalcular a partir daqui
              </button>
              <p className="text-[11px] text-slate-500">
                Recalcula só as fases downstream. Editar{' '}
                <code>context7_mativas</code> não reexecuta o lookup. O texto
                acompanha o JSON quando este é válido.
              </p>
            </div>
          ) : null}

          {simComparison ? (
            <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-4">
              <p className="text-xs font-semibold uppercase text-teal-900">
                Comparação vs Biblioteca de Passos
              </p>
              <p className="mt-1 text-sm text-slate-700">
                idênticos {simComparison.identical_count ?? 0}/
                {simComparison.n_referencia ?? '—'} · títulos{' '}
                {simComparison.titulo_identical_count ?? 0} · descrições{' '}
                {simComparison.descricao_identical_count ?? 0} · fonte{' '}
                {simComparison.extracted_from || '—'}
              </p>
            </div>
          ) : null}

          <div
            className="space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4"
            data-testid="prompt-lab"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-900">
              Prompt Lab · corpus genérico
            </p>
            <p className="text-xs text-slate-600">
              Sugestão de template a partir de 2+ simulações. O texto é só para
              copiar — nunca escreve no Mativas nem em outro sistema.
            </p>
            <p className="text-xs text-slate-500">
              Simulações na sessão: {simHistory.length}
              {simHistory.length
                ? ` (${simHistory
                    .slice(0, 3)
                    .map((h) => h.metodologia)
                    .join('; ')})`
                : ''}
            </p>
            <label className="block text-xs text-slate-600">
              Corpus id/slug
              <input
                className="mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1 text-sm"
                value={labCorpusId}
                onChange={(e) => setLabCorpusId(e.target.value)}
              />
            </label>
            <label className="block text-xs text-slate-600">
              Prompt mestre de referência (opcional)
              <textarea
                className="mt-1 w-full rounded border border-slate-200 bg-white p-2 text-sm"
                rows={3}
                value={labPromptMestre}
                onChange={(e) => setLabPromptMestre(e.target.value)}
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || simHistory.length < 2}
                onClick={handleLabSugestao}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800 disabled:opacity-50"
                data-testid="btn-sugestao-prompt"
              >
                {busy === 'lab-sugestao' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Gerar sugestão de prompt geral
              </button>
              <button
                type="button"
                disabled={!!busy}
                onClick={handleLabLoadCiclos}
                className="rounded-lg border border-indigo-300 bg-white px-3 py-2 text-sm text-indigo-900 hover:bg-indigo-50 disabled:opacity-50"
              >
                Atualizar ciclos
              </button>
            </div>
            {labSugestaoMd ? (
              <CopyableBlock label="Copiar sugestão" text={labSugestaoMd}>
                <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-indigo-100 bg-white p-3 text-xs text-slate-800">
                  {labSugestaoMd}
                </pre>
              </CopyableBlock>
            ) : null}

            <div className="rounded-lg border border-indigo-100 bg-white p-3">
              <p className="text-xs font-semibold text-slate-700">
                Timeline de ciclos
              </p>
              {labCiclos.length === 0 ? (
                <p className="mt-1 text-xs text-slate-500">
                  Nenhum ciclo ainda. Gere uma sugestão após 2+ simulações.
                </p>
              ) : (
                <ul className="mt-2 space-y-1 text-xs text-slate-700">
                  {labCiclos.map((c) => (
                    <li key={c.id} className="flex flex-wrap gap-2 border-t border-slate-100 pt-1">
                      <span className="font-semibold">Ciclo {c.numero_ciclo}</span>
                      <span>
                        sim:{' '}
                        {c.nota_agregada_simulada != null
                          ? `${(c.nota_agregada_simulada * 100).toFixed(0)}%`
                          : '—'}
                      </span>
                      <span>
                        real:{' '}
                        {c.nota_agregada_real != null
                          ? `${(c.nota_agregada_real * 100).toFixed(0)}%`
                          : '—'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="space-y-2 rounded-lg border border-indigo-100 bg-white p-3">
              <p className="text-xs font-semibold text-slate-700">
                Colar resultado real (manual)
              </p>
              <p className="text-[11px] text-slate-500">
                Sem scraping/API do Mativas — só o que você colar aqui.
              </p>
              <input
                className="w-full rounded border border-slate-200 px-2 py-1 text-sm"
                value={labRealChave}
                onChange={(e) => setLabRealChave(e.target.value)}
                placeholder="Metodologia / chave"
              />
              <input
                className="w-full rounded border border-slate-200 px-2 py-1 text-sm"
                value={labRealCiclo}
                onChange={(e) => setLabRealCiclo(e.target.value)}
                placeholder="Nº ciclo (opcional)"
              />
              <textarea
                className="w-full rounded border border-slate-200 p-2 font-mono text-xs"
                rows={5}
                value={labRealPayload}
                onChange={(e) => setLabRealPayload(e.target.value)}
                placeholder='JSON {"passos":[...]} ou texto da entrega'
              />
              <button
                type="button"
                disabled={busy || !labRealPayload.trim()}
                onClick={handleLabResultadoReal}
                className="rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-2 text-sm text-indigo-950 hover:bg-indigo-100 disabled:opacity-50"
              >
                {busy === 'lab-real' ? 'Comparando…' : 'Comparar resultado real'}
              </button>
              {labRealResult?.comparison ? (
                <p className="text-xs text-slate-700">
                  Nota real:{' '}
                  {labRealResult.comparison.nota_agregada != null
                    ? `${(labRealResult.comparison.nota_agregada * 100).toFixed(0)}%`
                    : labRealResult.comparison.identical_ratio != null
                      ? `${(labRealResult.comparison.identical_ratio * 100).toFixed(0)}%`
                      : '—'}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {!restricted && tab === 'previa' ? (
        <div data-testid="crystal-tab-previa-panel">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-800">
                Prévia rápida (sem Spec / sem grounding Mativas)
              </p>
              <p className="text-xs text-slate-500">
                Uma chamada reduzida — resultado efêmero com{' '}
                <code>is_preview: true</code>. Não usa a Biblioteca de Passos.
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
      ) : null}
    </section>
  )
}
