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

export const TOKEN_PAIRS: Array<{ name: string; fg: string; bg: string }> = [
  { name: "grafite sobre bege", fg: "#323334", bg: "#E5E4D6" },
  { name: "espresso sobre creme", fg: "#49352A", bg: "#F7F2E8" },
  { name: "castanho sobre creme", fg: "#6B4A3A", bg: "#F7F2E8" },
  { name: "oliva sobre creme", fg: "#3D5A3A", bg: "#F7F2E8" },
  { name: "ocre sobre creme", fg: "#8A5A12", bg: "#F7F2E8" },
  { name: "terracota sobre creme", fg: "#8B3A2A", bg: "#F7F2E8" },
  { name: "creme sobre grafite", fg: "#F7F2E8", bg: "#323334" },
  { name: "trigo sobre espresso", fg: "#C7A878", bg: "#49352A" },
];
