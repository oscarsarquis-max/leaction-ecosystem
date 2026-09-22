export function relativeLuminance(hex: string): number {
  const raw = hex.replace("#", "");
  const value = raw.length === 3 ? raw.split("").map((ch) => ch + ch).join("") : raw;
  const rgb = [0, 2, 4].map((index) => {
    const channel = Number.parseInt(value.slice(index, index + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
}

export function contrastRatio(foreground: string, background: string): number {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

/** Pares oficiais do tema marrom/bege (WCAG AA ≥ 4.5:1 texto). */
export const TOKEN_PAIRS: Array<{ name: string; fg: string; bg: string }> = [
  { name: "grafite sobre bege", fg: "#323334", bg: "#e5e4d6" },
  { name: "grafite sobre creme", fg: "#323334", bg: "#f7f2e8" },
  { name: "bege sobre grafite (chrome)", fg: "#e5e4d6", bg: "#323334" },
  { name: "creme sobre espresso (botão)", fg: "#f7f2e8", bg: "#49352a" },
  { name: "oliva sobre bege", fg: "#3d5a3a", bg: "#e5e4d6" },
  { name: "ocre sobre bege", fg: "#8a5a12", bg: "#e5e4d6" },
  { name: "terracota sobre creme", fg: "#8b3a2a", bg: "#f7f2e8" },
];

/** Escala marrom/bege de referência (tema aprovado na demo). */
export const BROWN_SCALE = {
  grafite: "#323334",
  bege: "#e5e4d6",
  espresso: "#49352a",
  castanho: "#6b4a3a",
  caramelo: "#a06f49",
  trigo: "#c7a878",
  creme: "#f7f2e8",
  areia: "#d8c9af",
  oliva: "#3d5a3a",
  ocre: "#8a5a12",
  terracota: "#8b3a2a",
  foco: "#5a3d2c",
} as const;

/** Tema verde rejeitado — não usar. */
export const GREEN_SCALE = {} as Record<string, string>;
