import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { resolveJourneyFlags } from '../utils/journeyState';

export default function PlanoGeral() {
  const { journey } = useAuth();
  const flags = resolveJourneyFlags(journey);

  if (!flags.mostrarPlanoKanban) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
        <h1 className="text-xl font-bold text-amber-900">Plano Geral</h1>
        <p className="text-sm text-amber-800">
          Disponível após a Gênese IA — até 12 sprints priorizadas por gap (PanelDX{' '}
          <code className="text-xs">/meu-plano</code>).
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
        <h1 className="text-2xl font-bold text-[#4A2E80]">Plano Geral</h1>
        <p className="mt-1 text-sm text-slate-500">
          Roadmap por ondas — 3 sprints ativas na Onda 1, demais no backlog (até 12 no Kanban).
        </p>
      </header>
      <section className="rounded-xl border border-dashed border-violet-200 bg-violet-50/40 p-8 text-center text-sm text-slate-600">
        Timeline de sprints será renderizada aqui após implementar a Gênese IA (referência PanelDX{' '}
        <strong>client_journey.ejs</strong>).
      </section>
    </div>
  );
}
