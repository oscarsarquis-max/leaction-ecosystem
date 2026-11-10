import yellow from "../assets/brand/actionfinance-yellow.png";
import blue from "../assets/brand/actionfinance-blue.png";
import white from "../assets/brand/actionfinance-white.png";
import mark from "../assets/brand/af-logo-vazado-branco.png";

const ASSETS = {
  yellow: { src: yellow, intrinsicWidth: 2098, intrinsicHeight: 749 },
  blue: { src: blue, intrinsicWidth: 2127, intrinsicHeight: 739 },
  white: { src: white, intrinsicWidth: 1254, intrinsicHeight: 1254 },
  /* letreiro branco com fundo transparente, para a faixa marrom */
  mark: { src: mark, intrinsicWidth: 640, intrinsicHeight: 115 },
} as const;

export type BrandVariant = keyof typeof ASSETS;

export function BrandLogo({
  variant = "yellow",
  width,
  to,
  onNavigate,
}: {
  variant?: BrandVariant;
  width: number;
  to?: string;
  onNavigate?: (to: string) => void;
}) {
  const asset = ASSETS[variant];
  const height = Math.round((width * asset.intrinsicHeight) / asset.intrinsicWidth);
  const image = (
    <img
      className={`brand-logo brand-logo--${variant}`}
      src={asset.src}
      alt="Action Finance Capital"
      width={width}
      height={height}
    />
  );
  if (!to) {
    return image;
  }
  return (
    <a
      href={to}
      className="brand-logo-link"
      aria-label="Action Finance Capital — início"
      onClick={(event) => {
        if (!onNavigate) {
          return;
        }
        event.preventDefault();
        onNavigate(to);
      }}
    >
      {image}
    </a>
  );
}
