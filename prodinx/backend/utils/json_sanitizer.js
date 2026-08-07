const SEM_INFORMACAO = /sem\s+informa[cç][aã]o/i;

function isSemInformacao(valor) {
  return typeof valor === "string" && SEM_INFORMACAO.test(valor.trim());
}

function toNumberIfNumericString(valor) {
  if (typeof valor !== "string") {
    return valor;
  }

  const trimmed = valor.trim();
  if (!trimmed) {
    return valor;
  }

  // Evita converter strings que não são números puros (ex.: matrículas F123)
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) {
    return valor;
  }

  const numerico = Number(trimmed);
  return Number.isFinite(numerico) ? numerico : valor;
}

/**
 * Higieniza recursivamente um valor JSON:
 * - 'Sem informação' → null
 * - números em string → Number
 * - remove chaves que começam com sc_ (scores pré-calculados)
 */
function sanitizeJsonValue(valor) {
  if (valor === null || valor === undefined) {
    return null;
  }

  if (typeof valor === "string") {
    if (isSemInformacao(valor)) {
      return null;
    }
    return toNumberIfNumericString(valor);
  }

  if (typeof valor === "number" || typeof valor === "boolean") {
    return valor;
  }

  if (Array.isArray(valor)) {
    return valor.map((item) => sanitizeJsonValue(item));
  }

  if (typeof valor === "object") {
    const limpo = {};

    for (const [chave, filho] of Object.entries(valor)) {
      if (chave.startsWith("sc_")) {
        continue;
      }
      limpo[chave] = sanitizeJsonValue(filho);
    }

    return limpo;
  }

  return valor;
}

module.exports = {
  SEM_INFORMACAO,
  isSemInformacao,
  sanitizeJsonValue,
};
