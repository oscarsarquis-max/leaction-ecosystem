import { useEffect, useState } from "react";

type Props = {
  src: string;
  alt: string;
  className?: string;
};

/** Foto de parceiro. Se o endereço não carregar, mostra "Foto indisponível" em vez do texto alternativo quebrado. */
export function Photo({ src, alt, className }: Props) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  if (failed || !src) {
    return (
      <span className={["mkt-photo-missing", className].filter(Boolean).join(" ")} role="img" aria-label={`${alt}: foto indisponível`}>
        Foto indisponível
      </span>
    );
  }
  return <img className={className} src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}
