type Props = {
  className?: string;
  /** Accessible label; image is decorative when empty string. */
  alt?: string;
  /**
   * Zooms the asset to crop empty padding in the source PNG
   * so the wordmark reads at a useful size without growing the chrome.
   */
  zoom?: number;
};

/** Brand mark from `/public/qmind-logo.png`. */
export function BrandLogo({
  className = "h-10 w-40",
  alt = "QMind",
  zoom = 2.4,
}: Props) {
  return (
    <span className={`relative inline-block overflow-hidden ${className}`}>
      <img
        src="/qmind-logo.png"
        alt={alt}
        decoding="async"
        className="absolute left-0 top-1/2 h-full w-auto max-w-none origin-left object-contain object-left"
        style={{ transform: `translateY(-50%) scale(${zoom})` }}
      />
    </span>
  );
}
