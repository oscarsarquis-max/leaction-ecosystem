const FORMATADOR_DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const FORMATADOR_DATA_HORA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function parseData(valor) {
  if (!valor) {
    return null;
  }

  const parsed = new Date(valor);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

export function formatarData(valor) {
  const parsed = parseData(valor);
  if (!parsed) {
    return valor ? String(valor) : "—";
  }

  return FORMATADOR_DATA.format(parsed);
}

export function formatarDataHora(valor) {
  const parsed = parseData(valor);
  if (!parsed) {
    return valor ? String(valor) : "—";
  }

  return FORMATADOR_DATA_HORA.format(parsed);
}

export function formatarPeriodo(inicio, fim) {
  if (!inicio && !fim) {
    return "—";
  }

  if (inicio && fim) {
    return `${formatarData(inicio)} → ${formatarData(fim)}`;
  }

  return formatarData(inicio || fim);
}
