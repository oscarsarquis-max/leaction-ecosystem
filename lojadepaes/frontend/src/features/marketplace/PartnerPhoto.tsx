import { useState } from "react";

type Props = {
  src?: string | null;
  alt: string;
  className: string;
  lazy?: boolean;
};

/** Foto do parceiro; sem foto ou se ela não carregar, mostra o fundo neutro em vez da imagem quebrada. */
export function PartnerPhoto({ src, alt, className, lazy = false }: Props) {
  const [failed, setFailed] = useState<string | null>(null);
  if (!src || failed === src) {
    return <span className={`${className} mkp-photo-empty`} aria-hidden="true" />;
  }
  return <img className={className} src={src} alt={alt} loading={lazy ? "lazy" : undefined} onError={() => setFailed(src)} />;
}
