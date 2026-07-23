import { useMemo, useRef } from "react";
import ColaboradorAutocomplete from "./ColaboradorAutocomplete";

function FilterIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h18M7 12h10M10 20h4" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4v6h6M20 20v-6h-6M5 19a9 9 0 0014-7M19 5a9 9 0 00-14 7"
      />
    </svg>
  );
}

const NIVEL_BASELINE = {
  colaborador: "Baseline: média do subpapel",
  papel: "Baseline: média do setor",
  subpapel: "Baseline: média do papel",
  setor: "Baseline: média total",
};

const BUSCA_POR_NIVEL = {
  colaborador: {
    label: "Buscar colaborador",
    placeholder: "Nome ou matrícula — necessário para análise individual",
    listKey: null,
  },
  papel: {
    label: "Buscar papel",
    placeholder: "Ex.: Técnica, Gestão Técnica",
    listKey: "papeis",
  },
  subpapel: {
    label: "Buscar subpapel",
    placeholder: "Ex.: Dev, PO, Scrum Master",
    listKey: "subpapeis",
  },
  setor: {
    label: "Buscar setor",
    placeholder: "Ex.: APD — vazio inclui todos",
    listKey: "setores",
  },
};

const NIVEIS_PADRAO = [
  { valor: "colaborador", label: "Colaborador", baseline: "Média do subpapel" },
  { valor: "papel", label: "Papel", baseline: "Média do setor" },
  { valor: "subpapel", label: "Subpapel", baseline: "Média do papel" },
  { valor: "setor", label: "Setor", baseline: "Média total" },
];

/** Atalhos temporários até a importação JSON popular o universo real. */
const COLABORADORES_TESTE = [
  { label: "José", matricula: "F178992" },
  { label: "Saulo", matricula: "F178841" },
  { label: "Samuel", matricula: "F170046" },
  { label: "Francisco", matricula: "F179117" },
];

function countActiveFilters(filtros) {
  if (filtros.id_colaborador) {
    return 1;
  }
  return String(filtros.busca || "").trim() ? 1 : 0;
}

function FilterBar({
  filtros,
  opcoes,
  filtrosAbertos,
  onToggleFiltros,
  onFiltrosChange,
  onApply,
  onClear,
  onRefresh,
  loading,
  onSelectColaboradorTeste,
  onSelectColaborador,
  onClearColaborador,
  onInvalidateColaborador,
  modoColaborador = false,
}) {
  const autocompleteRef = useRef(null);
  const activeCount = useMemo(() => countActiveFilters(filtros), [filtros]);
  const niveis = opcoes.niveis?.length ? opcoes.niveis : NIVEIS_PADRAO;
  const nivelInfo = niveis.find((item) => item.valor === filtros.nivel);
  const buscaConfig = BUSCA_POR_NIVEL[filtros.nivel] || BUSCA_POR_NIVEL.colaborador;

  const handleNivelChange = (nivel) => {
    onFiltrosChange({ nivel, busca: "", id_colaborador: null });
  };

  return (
    <div className="card-panel space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-laranja/15 text-brand-laranja">
            <FilterIcon />
          </div>
          <div>
            <h2 className="section-title">Janela de análise</h2>
            <p className="section-subtitle">
              {modoColaborador
                ? "Análise individual do colaborador selecionado"
                : "Visão geral da organização · selecione um colaborador para detalhar"}
              {" · "}
              {NIVEL_BASELINE[filtros.nivel]}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={`btn-outline ${filtrosAbertos ? "border-brand-verde bg-brand-verde/5" : ""}`}
            onClick={onToggleFiltros}
          >
            <FilterIcon />
            Filtros
            {activeCount > 0 && (
              <span className="rounded-full bg-brand-laranja px-2 py-0.5 text-xs font-semibold text-white">
                {activeCount}
              </span>
            )}
          </button>
          <button type="button" className="btn-primary" onClick={onRefresh} disabled={loading}>
            <RefreshIcon />
            {loading ? "A atualizar..." : "Atualizar dados"}
          </button>
        </div>
      </div>

      {onSelectColaboradorTeste && (
        <div className="space-y-2 border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-brand-cinza">
            Atalhos temporários — colaboradores de validação APD
          </p>
          <div className="flex flex-wrap gap-2">
            {COLABORADORES_TESTE.map((item) => {
              const ativo = modoColaborador && filtros.busca === item.matricula;
              return (
                <button
                  key={item.matricula}
                  type="button"
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    ativo
                      ? "border-brand-verde bg-brand-verde text-white"
                      : "border-gray-200 bg-white text-brand-cinza hover:border-brand-verde/40 hover:bg-brand-verde/5"
                  }`}
                  onClick={() => onSelectColaboradorTeste(item.matricula)}
                >
                  {item.label}
                  <span className="ml-1 font-normal opacity-70">{item.matricula}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {filtrosAbertos && (
        <div className="space-y-4 border-t border-gray-100 pt-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block text-sm text-brand-cinza">
              <span className="mb-1 block font-medium">Nível de comparação</span>
              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-verde/20"
                value={filtros.nivel}
                onChange={(event) => handleNivelChange(event.target.value)}
              >
                {niveis.map((item) => (
                  <option key={item.valor} value={item.valor}>
                    {item.label} ({item.baseline})
                  </option>
                ))}
              </select>
            </label>

            {filtros.nivel === "colaborador" ? (
              <div className="block text-sm text-brand-cinza">
                <span className="mb-1 block font-medium">{buscaConfig.label}</span>
                <ColaboradorAutocomplete
                  ref={autocompleteRef}
                  colaboradores={opcoes.colaboradores || []}
                  valorSelecionado={filtros.busca}
                  onSelect={onSelectColaborador}
                  onClear={onClearColaborador}
                  onInvalidateSelection={onInvalidateColaborador}
                  disabled={loading}
                  placeholder={buscaConfig.placeholder}
                />
              </div>
            ) : (
              <label className="block text-sm text-brand-cinza">
                <span className="mb-1 block font-medium">{buscaConfig.label}</span>
                <input
                  type="search"
                  list={buscaConfig.listKey ? `filtro-${buscaConfig.listKey}` : undefined}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-verde/20"
                  value={filtros.busca}
                  onChange={(event) =>
                    onFiltrosChange({ ...filtros, busca: event.target.value })
                  }
                  placeholder={buscaConfig.placeholder}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      onApply();
                    }
                  }}
                />
                {buscaConfig.listKey && (opcoes[buscaConfig.listKey] || []).length > 0 && (
                  <datalist id={`filtro-${buscaConfig.listKey}`}>
                    {(opcoes[buscaConfig.listKey] || []).map((item) => (
                      <option key={item} value={item} />
                    ))}
                  </datalist>
                )}
              </label>
            )}
          </div>

          <p className="text-xs text-brand-cinza/80">
            {filtros.nivel === "colaborador"
              ? "Pesquise por nome ou matrícula. A análise individual só é exibida após selecionar um colaborador."
              : "Uma única caixa de busca por nível. Deixe vazio para ver "}
            {filtros.nivel !== "colaborador" && (
              <>
                <strong>todos</strong> os registos do critério selecionado.
              </>
            )}
          </p>

          {nivelInfo && (
            <p className="text-xs text-brand-cinza/80">
              Ao filtrar por <strong>{nivelInfo.label.toLowerCase()}</strong>, o gráfico
              comparativo usa como referência a{" "}
              <strong>{nivelInfo.baseline.toLowerCase()}</strong>.
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={() => onApply(autocompleteRef.current?.getTermoBusca?.() ?? "")}
              disabled={loading}
            >
              Aplicar filtros
            </button>
            <button
              type="button"
              className="btn-outline"
              onClick={onClear}
              disabled={loading && activeCount === 0}
            >
              Limpar filtros
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default FilterBar;
