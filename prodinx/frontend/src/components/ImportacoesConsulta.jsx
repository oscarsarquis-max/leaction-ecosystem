import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchImportacoes } from "../api/client";
import ImportHistoryTable from "./ImportHistoryTable";
import LogoutButton from "./LogoutButton";

function ImportacoesConsulta() {
  const navigate = useNavigate();
  const [importacoes, setImportacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  const loadImportacoes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchImportacoes();
      setImportacoes(data.importacoes || []);
    } catch (err) {
      setError(err.response?.data?.erro || "Não foi possível carregar o histórico de importações.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadImportacoes();
  }, [loadImportacoes]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return importacoes;

    return importacoes.filter((item) => {
      const haystack = [
        item.id,
        item.nome_arquivo,
        item.cod_indicador,
        item.nome_indicador,
        item.nome_metrica,
        item.nome_grupo,
        item.colaborador_nome,
        item.colaborador_matricula,
        item.status,
        item.mensagem_erro,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(term);
    });
  }, [importacoes, query]);

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-brand-verde text-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-white/70">
              Prodinx · Monitoria
            </p>
            <h1 className="text-xl font-bold">Consulta de Importações</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-primary bg-brand-laranja"
              onClick={() => navigate("/dashboard")}
            >
              Voltar ao dashboard
            </button>
            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <div className="card-panel space-y-4">
          <div>
            <h2 className="section-title">Pesquisar importações</h2>
            <p className="section-subtitle">
              Consulte ficheiros processados, estado e período de referência quando necessário.
            </p>
          </div>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ID, ficheiro, indicador, grupo, colaborador, estado ou erro..."
            className="w-full rounded-lg border border-gray-200 px-4 py-2 text-sm text-brand-cinza focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-verde/20"
          />
          <div className="flex gap-2">
            <button type="button" className="btn-primary" onClick={loadImportacoes} disabled={loading}>
              {loading ? "A pesquisar..." : "Atualizar lista"}
            </button>
            <span className="self-center text-sm text-brand-cinza">
              {filtered.length} de {importacoes.length} registos
            </span>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-brand-vermelho/30 bg-brand-vermelho/10 px-4 py-3 text-sm text-brand-vermelho">
            {error}
          </div>
        )}

        {loading ? (
          <div className="card-panel flex items-center justify-center gap-3 py-16 text-brand-cinza">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-verde border-t-transparent" />
            A carregar histórico...
          </div>
        ) : (
          <ImportHistoryTable importacoes={filtered} />
        )}
      </main>
    </div>
  );
}

export default ImportacoesConsulta;
