import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { formatCents } from "../lib/money";
import { comboStatus, houseName } from "../admin/marketplace/labels";
import type { Partner, PartnerProduct, ProductCombo } from "../admin/marketplace/types";
import { Button } from "../admin/shell/Button";
import { COMBO_DEFAULT_FEE_CENTS } from "../features/marketplace/comboPricing";
import { PartnerApiError, houseBreads, partnerApi, type HouseBread } from "./partnerApi";

type Props = {
  partner: Partner;
  onBack: () => void;
};

type Draft = { bread: string; product: string; reason: string };

const EMPTY: Draft = { bread: "", product: "", reason: "" };

function errorText(reason: unknown, fallback: string): string {
  return reason instanceof PartnerApiError ? reason.message : fallback;
}

/** Demonstrativo do parceiro: só a parte dele. A parte da Loja não aparece aqui. */
function PriceBox({ product, feeCents }: { product?: PartnerProduct; feeCents: number }) {
  const freight = product?.freight_cents ?? null;
  const face = product ? product.price_cents + (freight ?? 0) : null;
  return (
    <div className="ptn-price-wrap">
      <dl className="ptn-price" aria-label="Seu recebimento">
        <dt>Seu produto</dt>
        <dd>{product ? formatCents(product.price_cents) : "—"}</dd>
        <dt>Seu frete</dt>
        <dd>{product ? (freight === null ? "—" : formatCents(freight)) : "—"}</dd>
        <dt>Taxa combo</dt>
        <dd>− {formatCents(feeCents)}</dd>
        <dt className="ptn-price-total">Você recebe</dt>
        <dd className="ptn-price-total">{face === null ? "—" : formatCents(face - feeCents)}</dd>
      </dl>
      <p className="ptn-price-note">
        O cliente paga o seu produto e o seu frete direto a você, pelo preço que você cadastrou. A taxa combo é descontada
        desse valor e não aparece para o cliente.
      </p>
    </div>
  );
}

export function PartnerCombos({ partner, onBack }: Props) {
  const [combos, setCombos] = useState<ProductCombo[] | null>(null);
  const [products, setProducts] = useState<PartnerProduct[]>([]);
  const [breads, setBreads] = useState<HouseBread[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: string; bread: string; reason: string } | null>(null);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const paused = partner.status === "paused";

  const load = useCallback(async () => {
    setError(null);
    try {
      const [comboRows, productRows] = await Promise.all([partnerApi.combos(), partnerApi.products()]);
      setCombos(comboRows);
      setProducts(productRows);
    } catch (reason) {
      setError(errorText(reason, "Não foi possível carregar as combinações."));
    }
  }, []);

  useEffect(() => {
    void load();
    houseBreads()
      .then(setBreads)
      .catch(() => setBreads([]));
  }, [load]);

  const approved = useMemo(() => products.filter((row) => row.status === "approved"), [products]);
  const product = approved.find((row) => row.id === draft.product);

  function pick(next: Partial<Draft>) {
    setNotice(null);
    setFormError(null);
    setDraft((current) => {
      const merged = { ...current, ...next };
      if (!current.reason.trim() && merged.bread && merged.product) {
        const chosen = approved.find((row) => row.id === merged.product);
        const pairing = chosen?.pairings.find((row) => row.house_product_slug === merged.bread);
        if (pairing) {
          merged.reason = pairing.reason;
        }
      }
      return merged;
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.bread || !draft.product || !draft.reason.trim()) {
      setFormError("Escolha o pão, o seu produto e diga por que combinam.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await partnerApi.createCombo({
        partner_product_id: draft.product,
        house_product_slug: draft.bread,
        reason: draft.reason.trim(),
      });
      setDraft(EMPTY);
      setNotice("Combinação enviada para avaliação.");
      await load();
    } catch (reason) {
      setFormError(errorText(reason, "Não foi possível enviar a combinação."));
    } finally {
      setBusy(false);
    }
  }

  async function resubmit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    if (!editing.bread || !editing.reason.trim()) {
      setEditError("Escolha o pão e diga por que combinam.");
      return;
    }
    setEditBusy(true);
    setEditError(null);
    try {
      await partnerApi.resubmitCombo(editing.id, { house_product_slug: editing.bread, reason: editing.reason.trim() });
      setEditing(null);
      await load();
    } catch (reason) {
      setEditError(errorText(reason, "Não foi possível reenviar a combinação."));
    } finally {
      setEditBusy(false);
    }
  }

  const breadName = (slug: string, fallback?: string | null) =>
    breads.find((row) => row.slug === slug)?.name ?? houseName(slug, fallback);
  const productOf = (id: string) => products.find((row) => row.id === id);

  return (
    <>
      <a
        className="mkt-back"
        href="/parceiro"
        onClick={(event) => {
          event.preventDefault();
          onBack();
        }}
      >
        ← Meus produtos
      </a>
      <header className="admin-page-header">
        <div>
          <h1>Combinações</h1>
          <p>
            Sempre um pão da casa com um produto seu. O cliente paga o seu produto e o seu frete direto a você; cada um entrega o
            seu. Toda combinação passa pela avaliação da Loja de Pães.
          </p>
        </div>
      </header>

      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}

      {paused ? null : (
        <form className="admin-card mkt-form" onSubmit={(event) => void submit(event)} aria-labelledby="ptn-new-combo" noValidate>
          <h2 id="ptn-new-combo" className="mkt-h2">
            Nova combinação
          </h2>
          {combos !== null && approved.length === 0 ? (
            <p className="ptn-banner" role="status">
              Para propor uma combinação, você precisa de pelo menos um produto aprovado pela Loja.
            </p>
          ) : (
            <div className="ptn-combo-grid">
              <div className="mkt-stack">
                <div className="mkt-grid mkt-grid-2">
                  <label className="mkt-field">
                    Pão da casa
                    <select className="mkt-input" value={draft.bread} onChange={(event) => pick({ bread: event.target.value })}>
                      <option value="">Escolha</option>
                      {breads.map((row) => (
                        <option key={row.slug} value={row.slug}>
                          {row.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="mkt-field">
                    Seu produto (aprovado)
                    <select className="mkt-input" value={draft.product} onChange={(event) => pick({ product: event.target.value })}>
                      <option value="">Escolha</option>
                      {approved.map((row) => (
                        <option key={row.id} value={row.id}>
                          {row.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="mkt-field">
                  Por que combinam
                  <input
                    className="mkt-input"
                    maxLength={400}
                    value={draft.reason}
                    placeholder="Ex.: a acidez do pão equilibra o sal do queijo"
                    onChange={(event) => pick({ reason: event.target.value })}
                  />
                </label>
              </div>
              <PriceBox product={product} feeCents={partner.fee_cents ?? COMBO_DEFAULT_FEE_CENTS} />
            </div>
          )}
          {formError ? (
            <p className="mkt-alert" role="alert">
              {formError}
            </p>
          ) : null}
          {notice ? (
            <p className="mkt-ok" role="status">
              {notice}
            </p>
          ) : null}
          {approved.length ? (
            <div className="mkt-form-foot">
              <Button type="submit" variant="primary" disabled={busy}>
                {busy ? "Enviando…" : "Enviar para avaliação"}
              </Button>
            </div>
          ) : null}
        </form>
      )}

      {combos === null && !error ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : null}
      {combos && combos.length === 0 ? (
        <div className="admin-card mkt-empty">
          <p className="mkt-empty-title">Nenhuma combinação ainda.</p>
          <p className="mkt-muted">Combine um pão da casa com um produto seu aprovado.</p>
        </div>
      ) : null}
      {combos && combos.length > 0 ? (
        <ul className="ptn-combos" aria-label="Minhas combinações">
          {combos.map((row) => {
            const tone = comboStatus(row.status);
            const own = productOf(row.partner_product_id);
            const isEditing = editing?.id === row.id;
            return (
              <li key={row.id} className="admin-card ptn-combo">
                <div className="ptn-combo-top">
                  <strong>
                    {breadName(row.house_product_slug, row.house_product_name)} + {own?.name ?? row.partner_product_name ?? "Seu produto"}
                  </strong>
                  <span className={`admin-chip ${tone.tone}`}>
                    <span className="dot" aria-hidden="true" />
                    {tone.label}
                  </span>
                </div>
                <p className="mkt-muted">{row.reason}</p>
                {row.review_note && (row.status === "returned" || row.status === "rejected") ? (
                  <p className="ptn-note">Loja: {row.review_note}</p>
                ) : null}
                {row.status === "returned" && !paused && !isEditing ? (
                  <div className="mkt-row">
                    <Button onClick={() => setEditing({ id: row.id, bread: row.house_product_slug, reason: row.reason })}>
                      Ajustar e reenviar
                    </Button>
                  </div>
                ) : null}
                {isEditing && editing ? (
                  <form className="mkt-subform" onSubmit={(event) => void resubmit(event)} aria-label="Ajustar combinação">
                    <div className="mkt-grid mkt-grid-2">
                      <label className="mkt-field">
                        Pão da casa
                        <select
                          className="mkt-input"
                          value={editing.bread}
                          onChange={(event) => setEditing({ ...editing, bread: event.target.value })}
                        >
                          {breads.map((option) => (
                            <option key={option.slug} value={option.slug}>
                              {option.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="mkt-field">
                        Por que combinam
                        <input
                          className="mkt-input"
                          maxLength={400}
                          value={editing.reason}
                          onChange={(event) => setEditing({ ...editing, reason: event.target.value })}
                        />
                      </label>
                    </div>
                    {editError ? (
                      <p className="mkt-alert" role="alert">
                        {editError}
                      </p>
                    ) : null}
                    <div className="mkt-row">
                      <Button type="submit" variant="primary" disabled={editBusy}>
                        {editBusy ? "Reenviando…" : "Reenviar para avaliação"}
                      </Button>
                      <Button onClick={() => setEditing(null)}>Cancelar</Button>
                    </div>
                  </form>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </>
  );
}
