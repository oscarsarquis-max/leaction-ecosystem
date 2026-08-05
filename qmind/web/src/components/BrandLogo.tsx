type Props = {
  className?: string;
  /** Accessible label; image is decorative when empty string. */
  alt?: string;
  /**
   * Zooms the asset to crop empty padding (header lockup).
   * Ignorado quando mode="full".
   */
  zoom?: number;
  align?: "left" | "center";
  /**
   * full = PNG inteiro, object-contain (login).
   * crop = recorte com zoom (header).
   */
  mode?: "full" | "crop";
};

/** Brand mark from `/public/qmind-logo.png` (preto e branco). */
export function BrandLogo({
  className = "h-10 w-40",
  alt = "QMind",
  zoom = 2.4,
  align = "left",
  mode = "full",
}: Props) {
  /** full = logo inteiro (login grande / header sem crop). */
  if (mode === "full") {
    return (
      <img
        src="/qmind-logo-light.png"
        alt={alt}
        decoding="async"
        className={`block object-contain ${className}`}
      />
    );
  }

  const imgClass =
    align === "center"
      ? "absolute left-1/2 top-1/2 h-full w-auto max-w-none origin-center object-contain"
      : "absolute left-0 top-1/2 h-full w-auto max-w-none origin-left object-contain object-left";

  const imgStyle =
    align === "center"
      ? { transform: `translate(-50%, -50%) scale(${zoom})` }
      : { transform: `translateY(-50%) scale(${zoom})` };

  return (
    <span className={`relative inline-block overflow-hidden ${className}`}>
      <img
        src="/qmind-logo-light.png"
        alt={alt}
        decoding="async"
        className={imgClass}
        style={imgStyle}
      />
    </span>
  );
}
