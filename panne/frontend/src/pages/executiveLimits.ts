/** Limites de crescimento do painel. Não cortar com overflow hidden. */
export const EXEC_LIMITS = {
  kpis: 6,
  priorities: 3,
  agenda: 5,
  production: 6,
  costsProduced: 5,
  costsPurchased: 3,
  prices: 5,
} as const;
