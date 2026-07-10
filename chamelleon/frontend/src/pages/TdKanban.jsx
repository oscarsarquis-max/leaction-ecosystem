import { useCallback, useEffect, useState } from 'react';
import KaizenOriginModal from '../components/kaizen/KaizenOriginModal';
import TdSprintModal from '../components/td/TdSprintModal';
import {
  emptyTdKanbanBoard,
  formatSprintBlockLabel,
  isEmergentSprint,
  TD_KANBAN_COLUMNS,
  TD_STAGE,
} from '../constants/td';
import { fetchTdKanban, updateTdSprint } from '../services/tdApi';

function SprintCard({ sprint, isDragging, onDragStart, onDragEnd, onOpen, onOpenOrigin }) {
  const emergent = isEmergentSprint(sprint);
  const block = formatSprintBlockLabel(sprint);
  const showOriginLink =
    sprint.origin_ref_id &&
    (sprint.kanban_stage === TD_STAGE.KAIZEN_ENTRADA || emergent);

  return (
    <article
      draggable
      onDragStart={(event) => onDragStart(event, sprint)}
      onDragEnd={onDragEnd}
      onDoubleClick={() => onOpen(sprint)}
      className={`cursor-grab rounded-xl border bg-white p-3 shadow-sm active:cursor-grabbing ${
        emergent ? 'border-red-300 ring-1 ring-red-200' : 'border-slate-200'
      } ${isDragging ? 'opacity-50' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          className="text-left text-sm font-semibold text-slate-900 hover:underline"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(sprint);
          }}
        >
          {sprint.title}
        </button>
        {emergent && (
          <span className="shrink-0 rounded-md bg-red-600 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            Emergente
          </span>
        )}
      </div>
      <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {block?.pair || sprint.paneldx_domain}
      </p>
      {block?.dimBlock && (
        <p className="mt-1 text-xs font-medium text-violet-800">{block.dimBlock}</p>
      )}
      {block?.meta?.deliverableName && (
        <p className="mt-0.5 text-[11px] text-slate-500">
          Entregável: {block.meta.deliverableName}
        </p>
      )}
      {sprint.description && (
        <p className="mt-2 line-clamp-2 text-xs text-slate-600">{sprint.description}</p>
      )}
      {showOriginLink && (
        <button
          type="button"
          className="mt-2 text-left text-[11px] font-semibold text-orange-700 hover:text-orange-900 hover:underline"
          onClick={(event) => {
            event.stopPropagation();
            onOpenOrigin(sprint.origin_ref_id);
          }}
        >
          Ver origem no Gemba
        </button>
      )}
      {!emergent && sprint.origin_type === 'baseline' && (
        <p className="mt-2 text-[10px] font-medium text-slate-400">Baseline</p>
      )}
    </article>
  );
}

export default function TdKanban() {
  const [board, setBoard] = useState(emptyTdKanbanBoard);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [draggingId, setDraggingId] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const [selected, setSelected] = useState(null);
  const [originTicketId, setOriginTicketId] = useState(null);
  const [savingModal, setSavingModal] = useState(false);

  const loadBoard = useCallback(async () => {
    setError('');
    try {
      const response = await fetchTdKanban();
      setBoard({ ...emptyTdKanbanBoard(), ...(response.kanban || {}) });
    } catch (err) {
      setError(err.message || 'Não foi possível carregar o Kanban de TD.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  function findSprintStage(sprintId) {
    return TD_KANBAN_COLUMNS.find((col) =>
      (board[col.id] || []).some((sprint) => sprint.id === sprintId),
    )?.id;
  }

  function moveSprintLocally(sprintId, fromStage, toStage) {
    if (fromStage === toStage) return;
    setBoard((prev) => {
      const next = { ...prev };
      const sprint = (next[fromStage] || []).find((item) => item.id === sprintId);
      if (!sprint) return prev;
      next[fromStage] = (next[fromStage] || []).filter((item) => item.id !== sprintId);
      next[toStage] = [
        { ...sprint, kanban_stage: toStage },
        ...(next[toStage] || []),
      ];
      return next;
    });
  }

  function handleDragStart(event, sprint) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', sprint.id);
    setDraggingId(sprint.id);
  }

  function handleDragEnd() {
    setDraggingId(null);
    setDropTarget(null);
  }

  function handleDragOverColumn(event, stageId) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setDropTarget(stageId);
  }

  async function handleDropOnColumn(event, targetStage) {
    event.preventDefault();
    const sprintId = event.dataTransfer.getData('text/plain');
    setDropTarget(null);
    setDraggingId(null);
    if (!sprintId) return;

    const fromStage = findSprintStage(sprintId);
    if (!fromStage || fromStage === targetStage) return;

    moveSprintLocally(sprintId, fromStage, targetStage);

    try {
      await updateTdSprint(sprintId, { kanban_stage: targetStage });
    } catch (err) {
      setError(err.message || 'Falha ao atualizar o estágio da sprint.');
      moveSprintLocally(sprintId, targetStage, fromStage);
    }
  }

  async function handleSaveSprint(payload) {
    if (!selected?.id) return;
    setSavingModal(true);
    setError('');
    try {
      const res = await updateTdSprint(selected.id, payload);
      const updated = res.sprint;
      setSelected(updated);
      setBoard((prev) => {
        const next = { ...prev };
        for (const col of TD_KANBAN_COLUMNS) {
          next[col.id] = (next[col.id] || []).map((item) =>
            item.id === updated.id ? updated : item,
          );
        }
        return next;
      });
    } catch (err) {
      setError(err.message || 'Falha ao salvar a sprint.');
    } finally {
      setSavingModal(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transformação Digital
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Kanban de Implementação</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Arraste sprints entre colunas. Clique no título para abrir o painel de execução (padrão
          PanelDX). Entradas Kaizen emergem do Gemba com badge vermelho.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando quadro…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {TD_KANBAN_COLUMNS.map((column) => {
            const items = board[column.id] || [];
            const isTarget = dropTarget === column.id;
            return (
              <section
                key={column.id}
                className={`flex min-h-[420px] flex-col rounded-2xl border bg-slate-50/80 ${
                  isTarget ? 'border-slate-400 ring-2 ring-slate-300' : 'border-slate-200'
                }`}
                onDragOver={(event) => handleDragOverColumn(event, column.id)}
                onDragLeave={() => setDropTarget(null)}
                onDrop={(event) => handleDropOnColumn(event, column.id)}
              >
                <header className="border-b border-slate-200 px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-sm font-semibold text-slate-900">{column.label}</h2>
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600">
                      {items.length}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{column.hint}</p>
                </header>
                <div className="flex flex-1 flex-col gap-3 p-3">
                  {items.length === 0 && (
                    <p className="px-1 py-6 text-center text-xs text-slate-400">
                      Solte sprints aqui
                    </p>
                  )}
                  {items.map((sprint) => (
                    <SprintCard
                      key={sprint.id}
                      sprint={sprint}
                      isDragging={draggingId === sprint.id}
                      onDragStart={handleDragStart}
                      onDragEnd={handleDragEnd}
                      onOpen={setSelected}
                      onOpenOrigin={setOriginTicketId}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <TdSprintModal
        sprint={selected}
        onClose={() => setSelected(null)}
        onSave={selected?.kanban_stage === TD_STAGE.EXECUCAO ? handleSaveSprint : undefined}
        saving={savingModal}
      />
      <KaizenOriginModal ticketId={originTicketId} onClose={() => setOriginTicketId(null)} />
    </div>
  );
}
