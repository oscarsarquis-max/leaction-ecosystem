import { useState } from "react";
import { formatCents } from "../../lib/money";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { MARKETPLACE_API, comboStatus, houseName } from "./labels";
import { ComboPrice } from "./ComboPrice";
import type { Partner, PartnerProduct, ProductCombo } from "./types";

type Props = {
  combo: ProductCombo;
  partner?: Partner;
  product?: PartnerProduct;
  onDecided: (message: string) => void;
};

export function ComboReviewCard({ combo, partner, product, onDecided }: Props) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const hasNote = note.trim().length > 0;
  const bread = houseName(combo.house_product_slug, combo.house_product_name);
  const item = product?.name ?? combo.partner_product_name ?? "Produto do parceiro";

  async function decide(decision: "approve" | "return" | "reject") {
    setBusy(decision);
    setError(null);
    try {
      await adminRequest(`${MARKETPLACE_API}/combos/${combo.id}/review`, {
        method: "POST",
        body: JSON.stringify({ decision, note: note.trim() }),
      });
      const message =
        decision === "approve" ? "Combinação aprovada." : decision === "return" ? "Combinação devolvida ao parceiro." : "Combinação recusada.";
      setDone(message);
      onDecided(message);
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível registrar a decisão.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <li className="admin-card mkt-combo-card">
      <div className="mkt-combo-head">
        <div>
          <p className="mkt-eyebrow">Combinação · {partner?.brand_name ?? "Parceiro"}</p>
          <h3 className="mkt-combo-title">
            {bread} <span aria-hidden="true">+</span>
            <span className="mkt-sr"> com </span> {item}
          </h3>
        </div>
        <span className={`admin-chip ${comboStatus(combo.status).tone}`}>
          <span className="dot" aria-hidden="true" />
          {comboStatus(combo.status).label}
        </span>
      </div>
      <p className="mkt-story">“{combo.reason}”</p>
      <p className="mkt-muted">
        Cliente paga: pão ({combo.house_unit_price_cents != null ? `${formatCents(combo.house_unit_price_cents)} no acordo` : "preço da vitrine"})
        {product ? ` + ${formatCents(product.price_cents)}` : ""}
        {product?.freight_cents != null ? ` + frete ${formatCents(product.freight_cents)}` : ""} · cada um entrega o seu
      </p>
      {done ? (
        <p className="mkt-ok" role="status">
          {done}
        </p>
      ) : (
        <>
          <ComboPrice comboId={combo.id} value={combo.house_unit_price_cents} />
          <label className="mkt-field">
            <span>
              Observação ao parceiro <span className="mkt-muted">· obrigatória para devolver ou recusar</span>
            </span>
            <input className="mkt-input" maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} />
          </label>
          {error ? (
            <p className="mkt-alert" role="alert">
              {error}
            </p>
          ) : null}
          <div className="mkt-row">
            <Button variant="primary" disabled={busy !== null} onClick={() => void decide("approve")}>
              {busy === "approve" ? "Aprovando…" : "Aprovar"}
            </Button>
            <Button disabled={busy !== null || !hasNote} onClick={() => void decide("return")}>
              {busy === "return" ? "Devolvendo…" : "Devolver com observação"}
            </Button>
            <Button variant="danger" disabled={busy !== null || !hasNote} onClick={() => void decide("reject")}>
              {busy === "reject" ? "Recusando…" : "Recusar"}
            </Button>
          </div>
        </>
      )}
    </li>
  );
}
