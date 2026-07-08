import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchMedicaoItens, fetchMetricas } from "../api/client";
import ItemsTable from "./ItemsTable";
import LogoutButton from "./LogoutButton";
import { extractTableRows } from "../utils/metricas";

function DetalhesConsulta() {
  const navigate = useNavigate();
  const [metricas, setMetricas] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loadingMetricas, setLoadingMetricas] = useState(true);
  const [loadingItens, setLoadingItens] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMetricas()
      .then((data) => {
        const lista = data.metricas || [];
        setMetricas(lista);
        if (lista.length > 0) {
          setSelectedId(String(lista[0].id));
        }
      })
      .catch((err) => {
        setError(err.response?.data?.erro || "Não foi possível carregar as métricas.");
      })
      .finally(() => setLoadingMetricas(false));
  }, []);

  const loadItens = useCallback(async () => {
    if (!selectedId) {
      setRows([]);
      setTotal(0);
      return;
    }

    try {
      setLoadingItens(true);
      setError(null);
      const data = await fetchMedicaoItens(selectedId, { q: query, limit: 100 });
      const metrica = metricas.find((item) => String(item.id) === String(selectedId));
      setRows(
        extractTableRows([
          {
            id: data.medicao_id,
            nome_metrica: data.nome_metrica || metrica?.nome_metrica,
            data_importacao: data.data_importacao,
            itens: data.itens,
          },
        ])
      );
      setTotal(data.total);
    } catch (err) {
      setError(err.response?.data?.erro || "Não foi possível carregar os registos detalhados.");
      setRows([]);
      setTotal(0);
    } finally {
      setLoadingItens(false);
    }
  }, [metricas, query, selectedId]);

  useEffect(() => {
    if (!loadingMetricas) {
      loadItens();
    }
  }, [loadItens, loadingMetricas]);

  const selectedMetrica = useMemo(
    () => metricas.find((item) => String(item.id) === String(selectedId)),
    [metricas, selectedId]
  );

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-brand-verde text-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-white/70">
              Prodinx · Consulta
            </p>
            <h1 className="text-xl font-bold">Registos Detalhados</h1>
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
            <h2 className="section-title">Pesquisar itens</h2>
            <p className="section-subtitle">
              Selecione a medição e pesquise nos itens do JSON apenas quando necessário.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm text-brand-cinza">
              <span className="mb-1 block font-medium">Medição</span>
              <select
                value={selectedId}
                onChange={(event) => setSelectedId(event.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2"
                disabled={loadingMetricas}
              >
                {metricas.map((metrica) => (
                  <option key={metrica.id} value={metrica.id}>
                    {metrica.nome_metrica}
                    {metrica.itens_total ? ` (${metrica.itens_total} itens)` : ""}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm text-brand-cinza">
              <span className="mb-1 block font-medium">Pesquisa</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Título, ID, estado, tags..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-sm text-brand-cinza">
            <button type="button" className="btn-primary" onClick={loadItens} disabled={loadingItens}>
              {loadingItens ? "A pesquisar..." : "Pesquisar"}
            </button>
            {selectedMetrica && (
              <span>
                A mostrar até 100 de {total} registos
                {selectedMetrica.itens_total > 100 ? " (primeira página)" : ""}
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-brand-vermelho/30 bg-brand-vermelho/10 px-4 py-3 text-sm text-brand-vermelho">
            {error}
          </div>
        )}

        {loadingItens ? (
          <div className="card-panel flex items-center justify-center gap-3 py-16 text-brand-cinza">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-verde border-t-transparent" />
            A carregar registos...
          </div>
        ) : (
          <ItemsTable rows={rows} />
        )}
      </main>
    </div>
  );
}

export default DetalhesConsulta;
