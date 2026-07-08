import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listSurveys } from '../services/api';

function shortId(id) {
  return id ? String(id).slice(0, 8) : '—';
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR');
  } catch {
    return iso;
  }
}

export default function Avaliacoes() {
  const navigate = useNavigate();
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const loadSurveys = useCallback(async (term = '') => {
    setLoading(true);
    setError('');
    try {
      const data = await listSurveys(term);
      setSurveys(data.surveys || []);
    } catch (err) {
      setError(err.message || 'Não foi possível carregar as avaliações.');
      setSurveys([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSurveys();
  }, [loadSurveys]);

  function handleSearch(e) {
    e.preventDefault();
    setSearch(searchInput);
    loadSurveys(searchInput);
  }

  function openDiagnostico(survey) {
    navigate('/', {
      state: {
        assessmentResult: {
          submission_id: survey.id,
          framework_id: survey.framework_id,
          score_global: survey.score_global,
          nivel_maturidade: survey.maturity_level_name,
          scores_por_eixo: survey.scores_por_eixo,
          action_plan_id: survey.action_plan_id,
        },
      },
    });
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-slate-800">Avaliações (Surveys)</h2>
        <p className="mt-1 text-sm text-slate-500">
          Listagem de diagnósticos realizados por clientes.
        </p>
      </header>

      <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Buscar por nome do cliente (mín. 3 caracteres)..."
          className="flex-1 rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:border-chameleon focus:outline-none focus:ring-2 focus:ring-chameleon/20"
        />
        <button
          type="submit"
          className="rounded-lg bg-chameleon px-5 py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark"
        >
          Buscar
        </button>
        <Link
          to="/diagnostico"
          className="rounded-lg border border-chameleon/30 bg-chameleon/5 px-5 py-2.5 text-center text-sm font-semibold text-chameleon-dark hover:bg-chameleon/10"
        >
          Novo diagnóstico
        </Link>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-500">Carregando avaliações...</p>
        ) : surveys.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">
            {search
              ? 'Nenhuma avaliação encontrada para esta busca.'
              : 'Nenhuma avaliação registrada. Inicie um diagnóstico para popular esta lista.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-semibold">ID</th>
                  <th className="px-4 py-3 font-semibold">Cliente</th>
                  <th className="px-4 py-3 font-semibold">Framework</th>
                  <th className="px-4 py-3 text-center font-semibold">Score</th>
                  <th className="px-4 py-3 font-semibold">Nível</th>
                  <th className="px-4 py-3 text-center font-semibold">Respostas</th>
                  <th className="px-4 py-3 font-semibold">Data</th>
                  <th className="px-4 py-3 text-center font-semibold">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {surveys.map((survey) => (
                  <tr key={survey.id} className="hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">
                      {shortId(survey.id)}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{survey.tenant_name}</td>
                    <td className="px-4 py-3 text-slate-600">{survey.framework_id}</td>
                    <td className="px-4 py-3 text-center font-semibold text-chameleon-dark">
                      {survey.score_global != null ? Number(survey.score_global).toFixed(2) : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{survey.maturity_level_name || '—'}</td>
                    <td className="px-4 py-3 text-center text-slate-600">{survey.response_count}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(survey.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-3">
                        <Link
                          to={`/avaliacoes/${survey.id}`}
                          title="Ver formulário (respostas)"
                          className="text-lg text-orange-500 hover:text-orange-600"
                        >
                          📋
                        </Link>
                        <button
                          type="button"
                          title="Ver diagnóstico"
                          onClick={() => openDiagnostico(survey)}
                          className="text-lg text-red-500 hover:text-red-600"
                        >
                          📊
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
