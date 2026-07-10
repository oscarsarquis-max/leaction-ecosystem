import { useCallback, useEffect, useState } from 'react';
import { KAIZEN_STAGES } from '../constants/kaizen';
import { fetchKaizenKanban, updateKaizenTicket } from '../services/kaizenApi';
import { emptyKanbanBoard } from '../utils/kaizenTicketMeta';
import { TdToast } from './td/TdSprintModal';
import FiveWhysModal from './kaizen/FiveWhysModal';
import KaizenStageTransitionModal from './kaizen/KaizenStageTransitionModal';
import KaizenTicketCard from './kaizen/KaizenTicketCard';

const GATED_STAGES = new Set(['Contencao', 'Cinco_Porques', 'Padronizacao', 'Concluido']);

export default function KaizenBoard() {
  const [board, setBoard] = useState(emptyKanbanBoard);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [draggingId, setDraggingId] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const [investigationTicket, setInvestigationTicket] = useState(null);
  const [pendingTransition, setPendingTransition] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  const loadBoard = useCallback(async () => {
    setError('');
    try {
      const response = await fetchKaizenKanban();
      setBoard({ ...emptyKanbanBoard(), ...(response.kanban || {}) });
    } catch (err) {
      setError(err.message || 'Não foi possível carregar o quadro Kaizen.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  function findTicketById(ticketId) {
    for (const stage of KAIZEN_STAGES) {
      const found = (board[stage.id] || []).find((ticket) => ticket.id === ticketId);
      if (found) return found;
    }
    return null;
  }

  function findTicketStage(ticketId) {
    return KAIZEN_STAGES.find((stage) =>
      (board[stage.id] || []).some((ticket) => ticket.id === ticketId),
    )?.id;
  }

  function moveTicketLocally(ticketId, fromStage, toStage, patch = {}) {
    if (fromStage === toStage) return;
    setBoard((prev) => {
      const next = { ...prev };
      const ticket = (next[fromStage] || []).find((item) => item.id === ticketId);
      if (!ticket) return prev;
      next[fromStage] = (next[fromStage] || []).filter((item) => item.id !== ticketId);
      next[toStage] = [
        { ...ticket, ...patch, workflow_stage: toStage },
        ...(next[toStage] || []),
      ];
      return next;
    });
  }

  function handleDragStart(event, ticket) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', ticket.id);
    setDraggingId(ticket.id);
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
    const ticketId = event.dataTransfer.getData('text/plain');
    setDropTarget(null);
    setDraggingId(null);
    if (!ticketId) return;

    const fromStage = findTicketStage(ticketId);
    if (!fromStage || fromStage === targetStage) return;

    const ticket = findTicketById(ticketId);
    if (!ticket) return;

    if (GATED_STAGES.has(targetStage)) {
      setPendingTransition({ ticket, fromStage, toStage: targetStage });
      return;
    }

    moveTicketLocally(ticketId, fromStage, targetStage);

    try {
      const response = await updateKaizenTicket(ticketId, { workflow_stage: targetStage });
      handleTicketUpdated(response.ticket || response);
    } catch (err) {
      setError(err.message || 'Erro ao mover o card.');
      await loadBoard();
    }
  }

  function cancelPendingTransition() {
    setPendingTransition(null);
  }

  function handleTransitionCompleted({ ticket, fromStage, toStage }) {
    moveTicketLocally(ticket.id, fromStage, toStage, ticket);
    handleTicketUpdated(ticket);
    setPendingTransition(null);
  }

  async function handleFiveWhysTransitionSaved(savedTicket) {
    if (!pendingTransition) return;
    const { fromStage, toStage, ticket } = pendingTransition;
    try {
      const response = await updateKaizenTicket(ticket.id, { workflow_stage: toStage });
      const merged = { ...(response.ticket || response), ...savedTicket };
      moveTicketLocally(ticket.id, fromStage, toStage, merged);
      handleTicketUpdated(merged);
      setPendingTransition(null);
    } catch (err) {
      setError(err.message || 'Análise salva, mas não foi possível avançar a fase.');
      await loadBoard();
      setPendingTransition(null);
    }
  }

  function handleEscalated(response) {
    const ticket = response.ticket;
    if (!ticket) return;

    const fromStage = pendingTransition?.fromStage || findTicketStage(ticket.id);
    if (fromStage && fromStage !== 'Concluido') {
      moveTicketLocally(ticket.id, fromStage, 'Concluido', ticket);
    } else {
      handleTicketUpdated(ticket);
    }

    setPendingTransition(null);
    setInvestigationTicket(null);
    setToastMessage(
      'Problema escalado! Uma nova Sprint foi gerada no Kanban de Transformação Digital.',
    );
  }

  function handleCardClick(ticket, stageId) {
    if (stageId === 'Cinco_Porques') {
      setInvestigationTicket(ticket);
    }
  }

  function handleTicketUpdated(updatedTicket) {
    setBoard((prev) => {
      const next = { ...prev };
      for (const stage of KAIZEN_STAGES) {
        next[stage.id] = (next[stage.id] || []).map((ticket) =>
          ticket.id === updatedTicket.id ? { ...ticket, ...updatedTicket } : ticket,
        );
      }
      return next;
    });
  }

  const totalTickets = KAIZEN_STAGES.reduce(
    (sum, stage) => sum + (board[stage.id]?.length || 0),
    0,
  );

  const showFiveWhysTransition =
    pendingTransition?.toStage === 'Cinco_Porques' && pendingTransition?.ticket;
  const showStageTransition =
    pendingTransition &&
    ['Contencao', 'Padronizacao', 'Concluido'].includes(pendingTransition.toStage);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-chameleon">
            Gemba · Melhoria Contínua
          </p>
          <h1 className="text-2xl font-bold text-slate-900">Quadro Kaizen</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Alertas do Diário de Obra entram automaticamente. Arraste os cards para avançar na
            jornada Lean — cada fase exige o preenchimento dos dados obrigatórios.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {totalTickets} ticket{totalTickets === 1 ? '' : 's'}
          </span>
          <button
            type="button"
            onClick={loadBoard}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-white"
          >
            Atualizar
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex min-h-[320px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-sm text-slate-500">
          Carregando quadro...
        </div>
      ) : (
        <div className="-mx-1 overflow-x-auto pb-2">
          <div className="flex min-w-[1100px] gap-3 px-1">
            {KAIZEN_STAGES.map((stage) => {
              const tickets = board[stage.id] || [];
              const isTarget = dropTarget === stage.id;

              return (
                <section
                  key={stage.id}
                  onDragOver={(event) => handleDragOverColumn(event, stage.id)}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(event) => handleDropOnColumn(event, stage.id)}
                  className={[
                    'flex w-72 shrink-0 flex-col rounded-2xl border shadow-sm transition',
                    stage.columnClass,
                    isTarget ? `ring-2 ${stage.accentClass}` : '',
                  ].join(' ')}
                >
                  <header
                    className={`rounded-t-2xl border-b px-4 py-3 ${stage.headerClass}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h2 className={`text-sm font-bold ${stage.titleClass}`}>{stage.label}</h2>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-bold ${stage.titleClass} bg-white/70`}
                      >
                        {tickets.length}
                      </span>
                    </div>
                  </header>

                  <div className="flex min-h-[420px] flex-1 flex-col gap-2 p-3">
                    {tickets.length === 0 ? (
                      <p className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-slate-200/80 px-3 py-8 text-center text-xs text-slate-400">
                        Arraste cards para cá
                      </p>
                    ) : (
                      tickets.map((ticket) => (
                        <KaizenTicketCard
                          key={ticket.id}
                          ticket={ticket}
                          stageId={stage.id}
                          isDragging={draggingId === ticket.id}
                          onDragStart={handleDragStart}
                          onDragEnd={handleDragEnd}
                          onClick={(item) => handleCardClick(item, stage.id)}
                        />
                      ))
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      )}

      <FiveWhysModal
        open={Boolean(investigationTicket)}
        ticket={investigationTicket}
        onClose={() => setInvestigationTicket(null)}
        onSaved={handleTicketUpdated}
        onEscalated={handleEscalated}
      />

      <FiveWhysModal
        open={Boolean(showFiveWhysTransition)}
        ticket={pendingTransition?.ticket}
        onClose={cancelPendingTransition}
        onSaved={handleFiveWhysTransitionSaved}
        onEscalated={handleEscalated}
        requireComplete
      />

      {showStageTransition && (
        <KaizenStageTransitionModal
          transition={pendingTransition}
          onClose={cancelPendingTransition}
          onCompleted={handleTransitionCompleted}
          onEscalated={handleEscalated}
        />
      )}

      <TdToast message={toastMessage} tone="success" onClose={() => setToastMessage('')} />
    </div>
  );
}
