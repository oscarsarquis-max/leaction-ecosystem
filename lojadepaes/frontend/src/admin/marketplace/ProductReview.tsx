import { useEffect, useState } from "react";
import { formatCents } from "../../lib/money";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { MARKETPLACE_API, categoryLabel, decisionLabel, houseName, productStatus, stampLabel } from "./labels";
import type { Partner, PartnerProduct, ProductReview } from "./types";

type Props = {
  product: PartnerProduct | null;
  partner: Partner | null;
  loading: boolean;
  onBack: () => void;
  onDecided: () => void;
};

type Key = "quality" | "visual" | "complementarity";

const CRITERIA: Array<[Key, string, string]> = [
  ["quality", "Qualidade", "produto e origem"],
  ["visual", "Visual", "fotos e apresentação"],
  ["complementarity", "Complementaridade", "combina com o pão da casa"],
];

function deliveryArea(product: PartnerProduct): string {
  const parts = [...product.delivery_cities, ...product.delivery_districts];
  if (product.delivery_cep_prefixes.length) {
    parts.push(`CEPs ${product.delivery_cep_prefixes.join(", ")}`);
  }
  return parts.length ? parts.join(", ") : "Não informada";
}

export function ProductReviewPage({ product, partner, loading, onBack, onDecided }: Props) {
  const [scores, setScores] = useState<Record<Key, number>>({ quality: 0, visual: 0, complementarity: 0 });
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [history, setHistory] = useState<ProductReview[]>([]);

  const productId = product?.id ?? null;
  useEffect(() => {
    if (!productId) {
      return;
    }
    let cancelled = false;
    adminRequest<ProductReview[]>(`${MARKETPLACE_API}/products/${productId}/reviews`)
      .then((rows) => {
        if (!cancelled) {
          setHistory(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHistory([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [productId]);

  const back = (
    <a
      className="mkt-back"
      href="/admin/marketplace/avaliacao"
      onClick={(event) => {
        event.preventDefault();
        onBack();
      }}
    >
      ← Fila de avaliação
    </a>
  );

  if (!product) {
    return (
      <section className="mkt-page" aria-busy={loading || undefined}>
        {back}
        {loading ? (
          <div className="admin-card mkt-skel">
            <span className="mkt-sr">Carregando…</span>
          </div>
        ) : (
          <p className="mkt-alert" role="alert">
            Produto não encontrado.
          </p>
        )}
      </section>
    );
  }

  const status = productStatus(product.status);
  const allScored = scores.quality > 0 && scores.visual > 0 && scores.complementarity > 0;
  const hasNote = note.trim().length > 0;
  const open = product.status === "pending" && !done;
  const hint = !allScored
    ? "Dê as três notas para decidir."
    : hasNote
      ? "Pronto para decidir."
      : "Para aprovar, basta decidir. Para devolver ou recusar, escreva a observação.";

  async function decide(decision: "approve" | "return" | "reject") {
    if (!product) {
      return;
    }
    setBusy(decision);
    setError(null);
    try {
      await adminRequest(`${MARKETPLACE_API}/products/${product.id}/review`, {
        method: "POST",
        body: JSON.stringify({ ...scores, decision, note: note.trim() }),
      });
      setDone(decision === "approve" ? "Aprovado e publicado." : decision === "return" ? "Devolvido ao parceiro." : "Recusado.");
      onDecided();
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível registrar a avaliação.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="mkt-page">
      {back}
      <header className="mkt-review-head">
        <div className="mkt-title-row">
          <h1 className="mkt-h1 is-xl">{product.name}</h1>
          <span className={`admin-chip ${status.tone}`}>
            <span className="dot" aria-hidden="true" />
            {status.label}
          </span>
        </div>
        <p className="mkt-lead">
          {partner?.brand_name ?? "Parceiro"} · {categoryLabel(product.category)} · {formatCents(product.price_cents)}
          {product.updated_at ? ` · enviado ${stampLabel(product.updated_at)}` : ""}
          {history.length ? ` · ${history.length + 1}ª rodada` : ""}
        </p>
      </header>

      <div className="mkt-review-grid">
        <div className="mkt-stack">
          <section className="admin-card mkt-section" aria-labelledby="mkt-photos">
            <h2 id="mkt-photos" className="mkt-h2">
              Fotos
            </h2>
            {product.photos.length ? (
              <div className="mkt-photos">
                {product.photos.slice(0, 3).map((src, index) => (
                  <a key={src} href={src} target="_blank" rel="noreferrer" className={index === 0 ? "mkt-photo is-main" : "mkt-photo"}>
                    <img src={src} alt={`Foto ${index + 1} de ${product.name}`} loading="lazy" />
                  </a>
                ))}
              </div>
            ) : (
              <p className="mkt-muted">Sem foto.</p>
            )}
          </section>

          <section className="admin-card mkt-section" aria-labelledby="mkt-desc">
            <h2 id="mkt-desc" className="mkt-h2">
              Descrição do parceiro
            </h2>
            <p className="mkt-story">{product.description || "Sem descrição."}</p>
          </section>

          <section className="admin-card mkt-section" aria-labelledby="mkt-pairs">
            <h2 id="mkt-pairs" className="mkt-h2">
              Combina com os pães da casa
            </h2>
            {product.pairings.length ? (
              <ul className="mkt-list">
                {product.pairings.map((row) => (
                  <li key={row.id} className="mkt-pair">
                    <strong>{houseName(row.house_product_slug, row.house_product_name)}</strong>
                    <p className="mkt-muted">{row.reason}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mkt-muted">Nenhum pão indicado.</p>
            )}
          </section>

          <section className="admin-card mkt-section" aria-labelledby="mkt-delivery">
            <div className="mkt-title-row is-spread">
              <h2 id="mkt-delivery" className="mkt-h2">
                Entrega do parceiro
              </h2>
              <span className="mkt-muted">a Loja não entrega este item</span>
            </div>
            <dl className="mkt-kv">
              <dt>Área</dt>
              <dd>{deliveryArea(product)}</dd>
              <dt>Prazo</dt>
              <dd>{product.delivery_days === null ? "Não informado" : `${product.delivery_days} ${product.delivery_days === 1 ? "dia" : "dias"} após o pedido`}</dd>
              <dt>Frete</dt>
              <dd>{product.freight_cents === null ? "Não informado" : formatCents(product.freight_cents)}</dd>
              <dt>Conservação</dt>
              <dd>{product.perishable ? "Perecível · refrigerado" : "Não perecível"}</dd>
            </dl>
          </section>

          {history.length ? (
            <section className="admin-card mkt-section" aria-labelledby="mkt-history">
              <h2 id="mkt-history" className="mkt-h2">
                Rodadas anteriores
              </h2>
              <ul className="mkt-list">
                {history.map((row) => (
                  <li key={row.id} className="mkt-history-row">
                    <span className="mkt-muted">{stampLabel(row.reviewed_at)}</span>
                    <span>
                      <strong>{decisionLabel(row.decision)}</strong>{" "}
                      <span className="mkt-muted">
                        · qualidade {row.quality}, visual {row.visual}, complementaridade {row.complementarity}
                        {row.note ? ` · “${row.note}”` : ""}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <aside className="admin-card mkt-section mkt-decide" aria-labelledby="mkt-decide-title">
          <div>
            <p className="mkt-eyebrow">Avaliação da Loja</p>
            <h2 id="mkt-decide-title" className="mkt-h2 is-lg">
              Publicar na vitrine?
            </h2>
          </div>
          {open ? (
            <>
              {CRITERIA.map(([key, label, help]) => (
                <fieldset key={key} className="mkt-score">
                  <legend>
                    {label} <span className="mkt-muted">· {help}</span>
                  </legend>
                  <div className="mkt-score-row">
                    {[1, 2, 3, 4, 5].map((value) => (
                      <button
                        key={value}
                        type="button"
                        className={scores[key] === value ? "mkt-score-btn is-on" : "mkt-score-btn"}
                        aria-pressed={scores[key] === value}
                        aria-label={`${label}: nota ${value}`}
                        onClick={() => setScores({ ...scores, [key]: value })}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </fieldset>
              ))}
              <label className="mkt-field">
                <span>
                  Observação ao parceiro <span className="mkt-muted">· obrigatória para devolver ou recusar</span>
                </span>
                <textarea
                  className="mkt-input mkt-textarea"
                  maxLength={2000}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Ex.: fotos com o queijo cortado e luz natural"
                />
              </label>
              <p className="mkt-muted" role="status">
                {hint}
              </p>
              {error ? (
                <p className="mkt-alert" role="alert">
                  {error}
                </p>
              ) : null}
              <div className="mkt-decide-actions">
                <Button variant="primary" disabled={!allScored || busy !== null} onClick={() => void decide("approve")}>
                  {busy === "approve" ? "Publicando…" : "Aprovar e publicar"}
                </Button>
                <Button disabled={!allScored || !hasNote || busy !== null} onClick={() => void decide("return")}>
                  {busy === "return" ? "Devolvendo…" : "Devolver com observação"}
                </Button>
                <Button variant="danger" disabled={!allScored || !hasNote || busy !== null} onClick={() => void decide("reject")}>
                  {busy === "reject" ? "Recusando…" : "Recusar"}
                </Button>
              </div>
            </>
          ) : (
            <p className="mkt-ok" role="status">
              {done ?? `Este produto não está em avaliação (${status.label.toLowerCase()}).`}
            </p>
          )}
        </aside>
      </div>
    </section>
  );
}
