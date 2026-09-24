import { useState } from "react";
import type { PublicProduct } from "./types";

type FeaturedPhotoProps = {
  product: PublicProduct;
  figureClassName?: string;
  mediaClassName?: string;
};

export function FeaturedPhoto({
  product,
  figureClassName = "shelf-card-figure",
  mediaClassName = "shelf-card-media",
}: FeaturedPhotoProps) {
  const [failed, setFailed] = useState(false);
  const caption = product.image_caption?.trim() ?? "";
  const alt = product.image_alt?.trim() || product.name;
  if (!product.image_url || failed) {
    return (
      <div className={`${mediaClassName} ${mediaClassName}--missing`}>
        <span>Fotografia ainda não disponível</span>
      </div>
    );
  }
  const captionMatchesAlt = caption.localeCompare(alt, undefined, { sensitivity: "accent" }) === 0;
  return (
    <figure className={figureClassName}>
      <div className={mediaClassName}>
        <img src={product.image_url} alt={alt} onError={() => setFailed(true)} />
      </div>
      {caption ? (
        <figcaption className="shelf-card-caption" aria-hidden={captionMatchesAlt || undefined}>
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
