import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PhaseNode from './PhaseNode'
import PhaseDetailPanel from './PhaseDetailPanel'
import { getLayoutedElements } from '../../utils/dagreLayout'

const nodeTypes = { phaseNode: PhaseNode }

/** Normaliza status do backend → chave visual do PhaseNode. */
export function mapPhaseStatus(raw) {
  const s = String(raw || 'PENDING').toUpperCase()
  if (s === 'RUNNING') return 'running'
  if (s === 'APPROVED' || s === 'SUCCESS' || s === 'COMPLETED') return 'approved'
  if (s === 'FAILED' || s === 'ERROR') return 'error'
  if (s === 'AWAITING_APPROVAL') return 'awaiting'
  return 'pending'
}

function buildGraphElements(spec, phaseExecutions) {
  const phases =
    spec && typeof spec === 'object' && spec.phases && typeof spec.phases === 'object'
      ? spec.phases
      : {}

  const statusById = new Map()
  if (Array.isArray(phaseExecutions)) {
    for (const p of phaseExecutions) {
      if (p?.phase_id) statusById.set(p.phase_id, p.status)
    }
  }

  const nodes = Object.entries(phases).map(([id, cfg]) => {
    const config = cfg && typeof cfg === 'object' ? cfg : {}
    const status = mapPhaseStatus(statusById.get(id) || 'PENDING')
    return {
      id,
      type: 'phaseNode',
      position: { x: 0, y: 0 },
      data: {
        title: config.name || id,
        capability: config.type || id,
        status,
        order: Number(config.order) || 999,
      },
      style: { cursor: 'pointer' },
    }
  })

  const edges = []
  for (const [id, cfg] of Object.entries(phases)) {
    const config = cfg && typeof cfg === 'object' ? cfg : {}
    const deps = Array.isArray(config.depends_on) ? config.depends_on : []
    const targetStatus = mapPhaseStatus(statusById.get(id) || 'PENDING')
    for (const dep of deps) {
      if (!dep || !phases[dep]) continue
      edges.push({
        id: `e-${dep}-${id}`,
        source: String(dep),
        target: id,
        animated: targetStatus === 'running',
        style: {
          stroke:
            targetStatus === 'running'
              ? '#0ea5e9'
              : targetStatus === 'approved' || targetStatus === 'success'
                ? '#34d399'
                : '#94a3b8',
          strokeWidth: 2,
        },
      })
    }
  }

  return getLayoutedElements(nodes, edges, 'LR')
}

function PipelineGraphInner({
  spec,
  phases,
  onApprove,
  approvingToken = null,
  immutable = false,
  runId = null,
  apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8010',
}) {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)

  const layoutKey = useMemo(() => {
    const phaseIds = spec?.phases ? Object.keys(spec.phases).sort().join(',') : ''
    const statuses = Array.isArray(phases)
      ? phases.map((p) => `${p.phase_id}:${p.status}`).join('|')
      : ''
    return `${phaseIds}::${statuses}`
  }, [spec, phases])

  useEffect(() => {
    const { nodes: nextNodes, edges: nextEdges } = buildGraphElements(spec, phases)
    setNodes(nextNodes)
    setEdges(nextEdges)
  }, [layoutKey, spec, phases])

  const selectedExecution = useMemo(() => {
    if (!selectedNodeId || !Array.isArray(phases)) return null
    return phases.find((p) => p.phase_id === selectedNodeId) || null
  }, [selectedNodeId, phases])

  const selectedSpecCfg = useMemo(() => {
    if (!selectedNodeId || !spec?.phases) return null
    const cfg = spec.phases[selectedNodeId]
    return cfg && typeof cfg === 'object' ? cfg : null
  }, [selectedNodeId, spec])

  const phaseData = useMemo(() => {
    if (!selectedNodeId) return null
    return {
      name: selectedExecution?.name || selectedSpecCfg?.name || selectedNodeId,
      title: selectedExecution?.name || selectedSpecCfg?.name || selectedNodeId,
      status: selectedExecution?.status || 'PENDING',
      capability: selectedSpecCfg?.type || selectedNodeId,
      type: selectedSpecCfg?.type || selectedNodeId,
    }
  }, [selectedNodeId, selectedExecution, selectedSpecCfg])

  const handleNodeClick = useCallback((_, node) => {
    if (!node?.id) return
    setSelectedNodeId(node.id)
    setIsPanelOpen(true)
  }, [])

  const handleClosePanel = useCallback(() => {
    setIsPanelOpen(false)
  }, [])

  const phaseCount = spec?.phases ? Object.keys(spec.phases).length : 0
  const awaitingCount = Array.isArray(phases)
    ? phases.filter((p) => String(p?.status || '').toUpperCase() === 'AWAITING_APPROVAL')
        .length
    : 0

  if (!phaseCount) {
    return (
      <div className="flex h-[320px] w-full items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/80 text-sm text-slate-500">
        Nenhuma fase no Spec — gere o pipeline para ver o DAG.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {awaitingCount > 0 ? (
        <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-left text-xs text-amber-950">
          {awaitingCount === 1
            ? '1 fase aguarda aprovação — clique no nó âmbar para revisar e aprovar.'
            : `${awaitingCount} fases aguardam aprovação — clique nos nós âmbar para revisar e aprovar.`}
        </p>
      ) : (
        <p className="text-left text-xs text-slate-500">
          Clique em um nó para abrir o artefato da fase (Markdown/JSON).
        </p>
      )}

      <div className="h-[600px] w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-50/90">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.35}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
        >
          <Background gap={18} size={1} color="#cbd5e1" />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeStrokeWidth={2}
            className="!rounded-lg !border !border-slate-200 !bg-white/90"
            nodeColor={(node) => {
              const s = node?.data?.status
              if (s === 'running') return '#38bdf8'
              if (s === 'approved' || s === 'success') return '#34d399'
              if (s === 'error') return '#f87171'
              if (s === 'awaiting') return '#fbbf24'
              return '#cbd5e1'
            }}
          />
        </ReactFlow>
      </div>

      <PhaseDetailPanel
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
        phaseId={selectedNodeId}
        phaseData={phaseData}
        artifactData={selectedExecution?.artifact_data ?? null}
        taskToken={immutable ? null : selectedExecution?.task_token ?? null}
        approving={
          Boolean(approvingToken) &&
          approvingToken === selectedExecution?.task_token
        }
        onApprove={immutable ? undefined : onApprove}
        immutable={immutable}
        runId={runId}
        apiBase={apiBase}
      />
    </div>
  )
}

/**
 * Visualização topológica do pipeline (DAG) via React Flow + dagre.
 */
export default function PipelineGraph({
  spec,
  phases = [],
  onApprove,
  approvingToken = null,
  immutable = false,
  runId = null,
  apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8010',
}) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner
        spec={spec}
        phases={phases}
        onApprove={onApprove}
        approvingToken={approvingToken}
        immutable={immutable}
        runId={runId}
        apiBase={apiBase}
      />
    </ReactFlowProvider>
  )
}
