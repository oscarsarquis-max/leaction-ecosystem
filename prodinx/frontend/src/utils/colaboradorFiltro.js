export function normalizarTextoColaborador(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function resolverColaboradorPorTermo(colaboradores = [], termo = "") {
  const busca = String(termo || "").trim();
  if (!busca) {
    return null;
  }

  const buscaNormalizada = normalizarTextoColaborador(busca);

  const porMatricula = colaboradores.find(
    (item) => normalizarTextoColaborador(item.matricula) === buscaNormalizada
  );
  if (porMatricula) {
    return porMatricula;
  }

  const porId = colaboradores.find(
    (item) => String(item.id_colaborador ?? "") === busca
  );
  if (porId) {
    return porId;
  }

  const candidatos = colaboradores.filter((item) => {
    const campos = [item.nome, item.matricula, item.label, item.funcao, item.papel, item.subpapel];
    return campos.some((campo) =>
      normalizarTextoColaborador(campo).includes(buscaNormalizada)
    );
  });

  if (candidatos.length === 1) {
    return candidatos[0];
  }

  const porNomeExato = colaboradores.find(
    (item) => normalizarTextoColaborador(item.nome) === buscaNormalizada
  );

  return porNomeExato ?? null;
}

export function filtrosColaboradorResolvidos(colaboradores, filtros, termoBusca = "") {
  if (filtros.nivel !== "colaborador") {
    return { ...filtros };
  }

  if (filtros.id_colaborador) {
    const porId = colaboradores.find(
      (item) => item.id_colaborador === filtros.id_colaborador
    );
    if (porId) {
      return {
        nivel: "colaborador",
        busca: porId.matricula,
        id_colaborador: porId.id_colaborador ?? null,
      };
    }
  }

  const termo = termoBusca || filtros.busca;
  const colaborador = resolverColaboradorPorTermo(colaboradores, termo);
  if (!colaborador) {
    return { ...filtros };
  }

  return {
    nivel: "colaborador",
    busca: colaborador.matricula,
    id_colaborador: colaborador.id_colaborador ?? null,
  };
}
