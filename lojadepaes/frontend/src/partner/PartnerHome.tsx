import { useCallback, useEffect, useState } from "react";
import { formatCents } from "../lib/money";
import { categoryLabel, productStatus } from "../admin/marketplace/labels";
import { Photo } from "../admin/marketplace/Photo";
import type { Partner, PartnerProduct, ProductReview } from "../admin/marketplace/types";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, partnerApi } from "./partnerApi";

type Props = {
  partner: Partner;
  onNew: () => void;
  onOpen: (id: string) => void;
  onBrand: () => void;
};

const HINT: Record<string, string> = {
  draft: "Ainda não enviado. Complete e envie para avaliação.",
  pending: "A Loja de Pães está avaliando.",
  approved: "Na vitrine. Editar o manda de volta para avaliação.",
  returned: "Devolvido com observação. Ajuste e envie de novo.",
  rejected: "Recusado. Veja a observação da Loja.",
  paused: "Pausado pela Loja de Pães.",
};

export function PartnerHome({ partner, onNew, onOpen, onBrand }: Props) {
  const [products, setProducts] = useState<PartnerProduct[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await partnerApi.products();
      setProducts(rows);
      const flagged = rows.filter((row) => row.status === "returned" || row.status === "rejected");
      const pairs = await Promise.all(
        flagged.map(async (row) => {
          const reviews: ProductReview[] = await partnerApi.reviews(row.id).catch(() => []);
          const last = reviews[reviews.length - 1];
          return [row.id, last?.note ?? ""] as const;
        }),
      );
      setNotes(Object.fromEntries(pairs.filter(([, note]) => note)));
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível carregar seus produtos.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const paused = partner.status === "paused";

  return (
    <>
      <header className="admin-page-header">
        <div>
          <h1>Meus produtos</h1>
          <p>Só categorias que acompanham pão. Todo produto passa pela avaliação da Loja de Pães: qualidade, visual e se combina com os pães da casa.</p>
        </div>
        <div className="mkt-row">
          <Button onClick={onBrand}>Minha marca</Button>
          {paused ? null : (
            <Button variant="primary" onClick={onNew}>
              Novo produto
            </Button>
          )}
        </div>
      </header>
      {paused ? (
        <p className="ptn-banner" role="status">
          Sua conta está pausada pela Loja de Pães. Você ainda vê seus produtos, mas não consegue alterar nada.
        </p>
      ) : null}
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {products === null && !error ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : null}
      {products && products.length === 0 ? (
        <div className="admin-card mkt-empty">
          <p className="mkt-empty-title">Nenhum produto ainda.</p>
          <p className="mkt-muted">Cadastre o primeiro: fotos, com qual pão da casa combina e como você entrega.</p>
          {paused ? null : (
            <Button variant="primary" onClick={onNew}>
              Novo produto
            </Button>
          )}
        </div>
      ) : null}
      {products && products.length > 0 ? (
        <ul className="ptn-products">
          {products.map((product) => {
            const status = productStatus(product.status);
            const note = notes[product.id];
            return (
              <li key={product.id}>
                <button type="button" className="admin-card ptn-product" onClick={() => onOpen(product.id)}>
                  {product.photos[0] ? (
                    <Photo className="ptn-product-photo" src={product.photos[0]} alt={product.name} />
                  ) : (
                    <span className="ptn-product-photo mkt-photo-missing">Sem foto</span>
                  )}
                  <span className="ptn-product-body">
                    <span className="ptn-product-top">
                      <strong>{product.name}</strong>
                      <span className={`admin-chip ${status.tone}`}>
                        <span className="dot" aria-hidden="true" />
                        {status.label}
                      </span>
                    </span>
                    <span className="mkt-muted">
                      {categoryLabel(product.category)} · {formatCents(product.price_cents)}
                    </span>
                    {note ? (
                      <span className="ptn-note">Loja: {note}</span>
                    ) : (
                      <span className="mkt-muted">{HINT[product.status] ?? ""}</span>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </>
  );
}
