import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getSurvey } from '../services/api';

export default function AvaliacaoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [survey, setSurvey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await getSurvey(id);
        if (!cancelled) setSurvey(data);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Survey não encontrado.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  function openDiagnostico() {
    if (!survey) return;
    navigate('/', {
      state: {
        assessmentResult: {
          submission_id: survey.id,
          framework_id: survey.framework_id,
          score_global: survey.score_global,
          nivel_maturidade: survey.nivel_maturidade,
          maturity_level_description: survey.maturity_level_description,
          scores_por_eixo: survey.scores_por_eixo,
          action_plan_id: survey.action_plan_id,
        },
      },
    });
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Carregando formulário do survey...</p>;
  }

  if (error || !survey) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-600">{error || 'Survey não encontrado.'}</p>
        <Link to="/avaliacoes" className="text-sm font-medium text-chameleon hover:underline">
          ← Voltar à listagem
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/avaliacoes" className="text-sm font-medium text-chameleon hover:underline">
            ← Avaliações
          </Link>
          <h2 className="mt-2 text-2xl font-bold text-slate-800">Formulário do Survey</h2>
          <p className="mt-1 text-sm text-slate-500">
            Cliente: <span className="font-medium text-slate-700">{survey.tenant_name}</span> ·
            Framework: <span className="font-medium">{survey.framework_id}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={openDiagnostico}
          className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
        >
          Ver diagnóstico
        </button>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Score global</p>
          <p className="text-2xl font-bold text-chameleon-dark">
            {survey.score_global != null ? Number(survey.score_global).toFixed(2) : '—'}
          </p>
        </article>
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Nível de maturidade</p>
          <p className="text-lg font-semibold text-slate-800">{survey.nivel_maturidade || '—'}</p>
        </article>
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Respostas registradas</p>
          <p className="text-2xl font-bold text-slate-800">{survey.responses?.length || 0}</p>
        </article>
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Dimensão / Eixo</th>
                <th className="px-4 py-3 font-semibold">Questão</th>
                <th className="px-4 py-3 text-center font-semibold">Nota</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(survey.responses || []).map((row) => (
                <tr key={row.id}>
                  <td className="px-4 py-3 text-slate-600">{row.axis}</td>
                  <td className="px-4 py-3 text-slate-800">{row.question_text}</td>
                  <td className="px-4 py-3 text-center font-semibold text-chameleon-dark">
                    {row.selected_value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
