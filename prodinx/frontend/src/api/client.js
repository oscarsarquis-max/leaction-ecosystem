import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 120000,
});

export const FILTROS_INICIAIS = {
  nivel: "setor",
  busca: "",
  id_colaborador: null,
};

export function isModoColaborador(filtros = FILTROS_INICIAIS) {
  return Boolean(filtros?.id_colaborador);
}

export function buildMetricasParams(filtros = FILTROS_INICIAIS) {
  const params = { nivel: filtros.nivel || "colaborador" };

  if (filtros.id_colaborador) {
    params.id_colaborador = filtros.id_colaborador;
  }

  const busca = String(filtros.busca || "").trim();

  if (params.nivel === "colaborador") {
    if (busca) {
      params.colaborador_busca = busca;
    }
    return params;
  }

  if (!busca) {
    return params;
  }

  if (params.nivel === "papel") {
    params.papel = busca;
  } else if (params.nivel === "subpapel") {
    params.subpapel = busca;
  } else if (params.nivel === "setor") {
    params.codsetor = busca;
  } else if (params.nivel === "funcao") {
    params.subpapel = busca;
    params.nivel = "subpapel";
  }

  return params;
}

export async function fetchFiltrosOpcoes() {
  const { data } = await api.get("/api/dashboard/filtros-opcoes");
  return data;
}

export async function fetchMetricas(filtros = FILTROS_INICIAIS) {
  const { data } = await api.get("/api/dashboard/metricas", {
    params: buildMetricasParams(filtros),
  });
  return data;
}

export async function fetchMedicaoItens(medicaoId, { q = "", limit = 50, offset = 0 } = {}) {
  const { data } = await api.get(`/api/medicoes/${medicaoId}/itens`, {
    params: { q, limit, offset },
  });
  return data;
}

export async function fetchImportacoes() {
  const { data } = await api.get("/api/importacoes");
  return data;
}

export async function fetchConfiguracaoPesosOpcoes() {
  const { data } = await api.get("/api/configuracao-pesos/opcoes");
  return data;
}

export async function fetchConfiguracaoPesos(papel, subpapel) {
  const { data } = await api.get("/api/configuracao-pesos", {
    params: { papel, subpapel },
  });
  return data;
}

export async function salvarConfiguracaoPesos(payload) {
  const { data } = await api.put("/api/configuracao-pesos", payload);
  return data;
}

export async function fetchIndicadoresConfig() {
  const { data } = await api.get("/api/indicadores/config");
  return data;
}

export async function salvarIndicadorConfig(codIndicador, payload, nomeGrupo = null) {
  const params = nomeGrupo ? { nome_grupo: nomeGrupo } : undefined;
  const { data } = await api.put(
    `/api/indicadores/config/${encodeURIComponent(codIndicador)}`,
    payload,
    { params }
  );
  return data;
}

export async function fetchAnaliseInteligente(idColaborador, { regenerar = false } = {}) {
  const { data } = await api.get(
    `/api/analise-inteligente/${encodeURIComponent(idColaborador)}`,
    {
      timeout: regenerar ? 180000 : 30000,
      params: regenerar ? { regenerar: 1 } : undefined,
    }
  );
  return data;
}

export default api;
