/**
 * Variáveis esperadas no payload por indicador (planilhas Gestão Técnica + Técnica).
 * Referência para a aba Fórmulas e Variáveis.
 */
export const VARIAVEIS_INDICADORES = {
  // Gestão Técnica
  S001: ["ml", "mli"],
  S002: ["prom", "detrat"],
  P001: ["ir", "sr", "rs", "eo", "rc", "sc"],
  P002: ["ac", "ua"],
  P003: ["tr", "bt"],
  P004: ["pe", "pp"],
  P005: ["cmpp", "zmpt"],
  P006: ["bve", "coe"],
  A001: ["ca", "bp"],
  A002: ["fd", "fp"],
  A003: ["pa", "ts"],
  A004: ["dv", "mi"],
  A005: ["spr", "spi"],
  A006: ["mt", "mp"],
  C001: ["it", "tq"],
  C002: ["dr", "i3us"],
  C003: ["gm3s"],
  C004: ["m3Gs"],
  C005: ["m3GEs"],
  E001: ["mwi", "mWE"],
  E002: ["ta", "lt"],
  E003: ["hr", "fte"],
  E004: ["ir", "it"],
  // Planilha Técnica (execução)
  P007: ["ir", "ie"],
  P008: ["df", "dr"],
  P009: ["carc", "pr"],
  P010: ["mtbf", "tt", "ip"],
  A007: ["pra", "mvt"],
  A008: ["dprod", "dup"],
  A009: ["sta", "sdp"],
  A010: ["btes", "bprod"],
  C006: ["trev", "mter"],
  C007: ["comcod", "pcrit"],
  C008: ["wdr", "ics"],
  E005: ["bfl", "ttj", "trs", "bet"],
  E006: ["tec", "ctt"],
  E007: ["rttdev"],
  E008: ["dpcy", "mcy"],
};

/** @deprecated use VARIAVEIS_INDICADORES */
export const VARIAVEIS_GESTAO_TECNICA = VARIAVEIS_INDICADORES;

export function obterVariaveisIndicador(codIndicador) {
  return VARIAVEIS_INDICADORES[codIndicador] || [];
}
