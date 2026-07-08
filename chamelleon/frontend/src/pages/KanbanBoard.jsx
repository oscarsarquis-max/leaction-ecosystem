import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { resolveJourneyFlags } from '../utils/journeyState';

const DEFAULT_COLUMNS = [
  { id: 'em_analise', label: 'Inovação (Em Análise)' },
  { id: 'planejada_backlog', label: 'Planejada (Backlog)' },
  { id: 'em_andamento', label: 'Em Andamento' },
  { id: 'concluida', label: 'Concluído' },
];

export default function KanbanBoard() {
  const { journey } = useAuth();
  const flags = resolveJourneyFlags(journey);
  const columns = journey?.kanban_columns?.length ? journey.kanban_columns : DEFAULT_COLUMNS;

  if (!flags.mostrarPlanoKanban) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
        <h1 className="text-xl font-bold text-amber-900">Quadro Kanban</h1>
        <p className="text-sm text-amber-800">
          Liberado após geração do plano com IA (PanelDX <code className="text-xs">/projeto/sprint-atual</code>).
        </p>
        <Link to="/" className="inline-block text-sm font-semibold text-chameleon-dark hover:underline">
          Voltar ao painel
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-[#4A2E80]">Quadro Kanban</h1>
        <p className="mt-1 text-sm text-slate-500">
          Colunas PanelDX — drag-and-drop e sprints serão conectados na Gênese IA.
        </p>
      </header>
      <div className="grid gap-4 lg:grid-cols-4">
        {columns.map((col) => (
          <section
            key={col.id}
            className="flex min-h-[320px] flex-col rounded-xl border border-violet-100 bg-white shadow-sm"
          >
            <header className="border-b border-violet-50 px-4 py-3">
              <h2 className="text-sm font-bold text-[#4A2E80]">{col.label}</h2>
            </header>
            <div className="flex-1 p-3">
              <p className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-slate-400">
                Sem sprints
              </p>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
