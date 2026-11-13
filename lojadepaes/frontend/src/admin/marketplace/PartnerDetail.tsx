import { useCallback, useEffect, useState, type FormEvent } from "react";
import { formatCents, parseBrlToCents } from "../../lib/money";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import {
  CATEGORIES,
  LINK_TYPES,
  MARKETPLACE_API,
  categoryLabel,
  feeLabel,
  linkActive,
  linkTone,
  linkTypeLabel,
  partnerStatus,
  partnerTypeLabel,
  periodLabel,
  productStatus,
  todayIso,
} from "./labels";
import { PartnerMark } from "./PartnerMark";
import type { Partner, PartnerLink, PartnerProduct } from "./types";

type Props = {
  partnerId: string;
  products: PartnerProduct[];
  onBack: () => void;
  onChanged: () => void;
  onReview: (productId: string) => void;
};

function message(reason: unknown, fallback: string): string {
  return reason instanceof AdminApiError ? reason.message : fallback;
}

export function PartnerDetail({ partnerId, products, onBack, onChanged, onReview }: Props) {
  const [partner, setPartner] = useState<Partner | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [feeText, setFeeText] = useState("");
  const [feeState, setFeeState] = useState<{ busy: boolean; error: string | null; saved: boolean }>({
    busy: false,
    error: null,
    saved: false,
  });
  const [link, setLink] = useState({ category: "", link_type: "partial", starts_on: todayIso(), ends_on: "" });
  const [linkState, setLinkState] = useState<{ busy: boolean; error: string | null }>({ busy: false, error: null });
  const [endingId, setEndingId] = useState<string | null>(null);
  const [pauseStep, setPauseStep] = useState<"idle" | "confirm" | "busy">("idle");
  const [pauseError, setPauseError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const row = await adminRequest<Partner>(`${MARKETPLACE_API}/partners/${partnerId}`);
      setPartner(row);
      setFeeText(formatCents(row.fee_cents).replace("R$ ", ""));
    } catch (reason) {
      setLoadError(message(reason, "Não foi possível abrir o parceiro."));
    }
  }, [partnerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const back = (
    <a
      className="mkt-back"
      href="/admin/marketplace/parceiros"
      onClick={(event) => {
        event.preventDefault();
        onBack();
      }}
    >
      ← Parceiros
    </a>
  );

  if (loadError) {
    return (
      <section className="mkt-page">
        {back}
        <p className="mkt-alert" role="alert">
          {loadError}
        </p>
      </section>
    );
  }
  if (!partner) {
    return (
      <section className="mkt-page" aria-busy="true">
        {back}
        <div className="admin-card mkt-skel">
          <span className="mkt-sr">Carregando…</span>
        </div>
      </section>
    );
  }

  const status = partnerStatus(partner.status);
  const today = todayIso();
  const links = partner.links ?? [];

  async function saveFee(event: FormEvent) {
    event.preventDefault();
    let cents: number | null;
    try {
      cents = /^0+(,0+)?$/.test(feeText.trim()) ? 0 : parseBrlToCents(feeText);
    } catch (reason) {
      setFeeState({ busy: false, error: reason instanceof Error ? reason.message : "valor inválido", saved: false });
      return;
    }
    if (cents === null) {
      setFeeState({ busy: false, error: "Informe a taxa.", saved: false });
      return;
    }
    setFeeState({ busy: true, error: null, saved: false });
    try {
      await adminRequest(`${MARKETPLACE_API}/partners/${partnerId}`, {
        method: "PATCH",
        body: JSON.stringify({ fee_cents: cents }),
      });
      setFeeState({ busy: false, error: null, saved: true });
      await load();
      onChanged();
    } catch (reason) {
      setFeeState({ busy: false, error: message(reason, "Não foi possível salvar a taxa."), saved: false });
    }
  }

  async function addLink(event: FormEvent) {
    event.preventDefault();
    if (!link.category) {
      setLinkState({ busy: false, error: "Escolha a categoria." });
      return;
    }
    setLinkState({ busy: true, error: null });
    try {
      await adminRequest(`${MARKETPLACE_API}/partners/${partnerId}/links`, {
        method: "POST",
        body: JSON.stringify({
          category: link.category,
          link_type: link.link_type,
          starts_on: link.starts_on,
          ends_on: link.ends_on || null,
        }),
      });
      setLink({ category: "", link_type: "partial", starts_on: todayIso(), ends_on: "" });
      setLinkState({ busy: false, error: null });
      await load();
      onChanged();
    } catch (reason) {
      setLinkState({ busy: false, error: message(reason, "Não foi possível criar o vínculo.") });
    }
  }

  async function endLink(row: PartnerLink) {
    setEndingId(row.id);
    setLinkState({ busy: false, error: null });
    try {
      await adminRequest(`${MARKETPLACE_API}/partners/${partnerId}/links/${row.id}/end`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await load();
      onChanged();
    } catch (reason) {
      setLinkState({ busy: false, error: message(reason, "Não foi possível encerrar o vínculo.") });
    } finally {
      setEndingId(null);
    }
  }

  async function pause() {
    setPauseStep("busy");
    setPauseError(null);
    try {
      await adminRequest(`${MARKETPLACE_API}/partners/${partnerId}/pause`, { method: "POST" });
      setPauseStep("idle");
      await load();
      onChanged();
    } catch (reason) {
      setPauseStep("confirm");
      setPauseError(message(reason, "Não foi possível pausar o parceiro."));
    }
  }

  return (
    <section className="mkt-page">
      {back}
      <header className="mkt-detail-head">
        <div className="mkt-brand">
          <PartnerMark partner={partner} size="lg" />
          <div className="mkt-brand-text">
            <div className="mkt-title-row">
              <h1 className="mkt-h1">{partner.brand_name}</h1>
              <span className={`admin-chip ${status.tone}`}>
                <span className="dot" aria-hidden="true" />
                {status.label}
              </span>
            </div>
            <p className="mkt-muted">
              {partnerTypeLabel(partner.partner_type)} · {partner.city} · {partner.region}
            </p>
          </div>
        </div>
        {partner.status !== "paused" ? (
          <div className="mkt-pause">
            {pauseStep === "idle" ? (
              <Button variant="danger" onClick={() => setPauseStep("confirm")}>
                Pausar parceiro
              </Button>
            ) : (
              <div className="mkt-confirm" role="group" aria-label="Confirmar pausa">
                <p>O parceiro deixa de poder alterar a marca e os produtos. Nesta versão ainda não há como reativar pela tela.</p>
                <div className="mkt-row">
                  <Button onClick={() => setPauseStep("idle")} disabled={pauseStep === "busy"}>
                    Voltar
                  </Button>
                  <Button variant="danger" onClick={() => void pause()} disabled={pauseStep === "busy"}>
                    {pauseStep === "busy" ? "Pausando…" : "Confirmar pausa"}
                  </Button>
                </div>
              </div>
            )}
            {pauseError ? (
              <p className="mkt-alert" role="alert">
                {pauseError}
              </p>
            ) : null}
          </div>
        ) : null}
      </header>

      <div className="mkt-detail-grid">
        <div className="mkt-stack">
          <section className="admin-card mkt-section" aria-labelledby="mkt-links-title">
            <h2 id="mkt-links-title" className="mkt-h2">
              Vínculos por categoria
            </h2>
            {links.length === 0 ? (
              <p className="mkt-muted">Sem vínculo. Sem vínculo vigente, os produtos não aparecem na harmonização.</p>
            ) : (
              <ul className="mkt-list">
                {links.map((row) => {
                  const active = linkActive(row.starts_on, row.ends_on, today);
                  const ended = row.ends_on !== null && row.ends_on < today;
                  return (
                    <li key={row.id} className="mkt-list-row">
                      <div>
                        <strong>{categoryLabel(row.category)}</strong>{" "}
                        <span className={`admin-chip ${ended ? "c-none" : linkTone(row.link_type)}`}>{linkTypeLabel(row.link_type)}</span>
                        <p className="mkt-muted">
                          {periodLabel(row.starts_on, row.ends_on)}
                          {ended ? " · encerrado" : active ? "" : " · ainda não começou"}
                        </p>
                      </div>
                      {!ended && row.ends_on === null ? (
                        <Button onClick={() => void endLink(row)} disabled={endingId === row.id}>
                          {endingId === row.id ? "Encerrando…" : "Encerrar hoje"}
                        </Button>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
            <form className="mkt-subform" onSubmit={(event) => void addLink(event)} aria-label="Novo vínculo">
              <div className="mkt-grid mkt-grid-4">
                <label className="mkt-field">
                  Categoria
                  <select
                    className="mkt-input"
                    value={link.category}
                    onChange={(event) => setLink({ ...link, category: event.target.value })}
                  >
                    <option value="">Escolha</option>
                    {CATEGORIES.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="mkt-field">
                  Vínculo
                  <select
                    className="mkt-input"
                    value={link.link_type}
                    onChange={(event) => setLink({ ...link, link_type: event.target.value })}
                  >
                    {LINK_TYPES.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="mkt-field">
                  Início
                  <input
                    className="mkt-input"
                    type="date"
                    required
                    value={link.starts_on}
                    onChange={(event) => setLink({ ...link, starts_on: event.target.value })}
                  />
                </label>
                <label className="mkt-field">
                  Fim (opcional)
                  <input
                    className="mkt-input"
                    type="date"
                    min={link.starts_on}
                    value={link.ends_on}
                    onChange={(event) => setLink({ ...link, ends_on: event.target.value })}
                  />
                </label>
              </div>
              {linkState.error ? (
                <p className="mkt-alert" role="alert">
                  {linkState.error}
                </p>
              ) : null}
              <div className="mkt-row">
                <Button type="submit" disabled={linkState.busy}>
                  {linkState.busy ? "Salvando…" : "Adicionar vínculo"}
                </Button>
              </div>
            </form>
          </section>

          <section className="admin-card mkt-section" aria-labelledby="mkt-products-title">
            <h2 id="mkt-products-title" className="mkt-h2">
              Produtos
            </h2>
            {products.length === 0 ? (
              <p className="mkt-muted">O parceiro ainda não cadastrou produtos.</p>
            ) : (
              <ul className="mkt-list">
                {products.map((product) => {
                  const tone = productStatus(product.status);
                  return (
                    <li key={product.id} className="mkt-list-row">
                      <div>
                        <strong>{product.name}</strong>
                        <p className="mkt-muted">
                          {categoryLabel(product.category)} · {formatCents(product.price_cents)}
                        </p>
                      </div>
                      <div className="mkt-row">
                        <span className={`admin-chip ${tone.tone}`}>
                          <span className="dot" aria-hidden="true" />
                          {tone.label}
                        </span>
                        {product.status === "pending" ? (
                          <Button variant="primary" onClick={() => onReview(product.id)} aria-label={`Avaliar ${product.name}`}>
                            Avaliar
                          </Button>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>

        <aside className="mkt-stack">
          <form className="admin-card mkt-section" onSubmit={(event) => void saveFee(event)} aria-labelledby="mkt-fee-title">
            <h2 id="mkt-fee-title" className="mkt-h2">
              Taxa por pedido
            </h2>
            <p className="mkt-muted">Hoje: {feeLabel(partner.fee_cents)}. Paga pelo parceiro em cada pedido; o cliente não paga.</p>
            <label className="mkt-field">
              Novo valor (R$)
              <input
                className="mkt-input mkt-num"
                inputMode="decimal"
                value={feeText}
                onChange={(event) => {
                  setFeeText(event.target.value);
                  setFeeState({ busy: false, error: null, saved: false });
                }}
              />
            </label>
            {feeState.error ? (
              <p className="mkt-alert" role="alert">
                {feeState.error}
              </p>
            ) : null}
            {feeState.saved ? (
              <p className="mkt-ok" role="status">
                Taxa salva.
              </p>
            ) : null}
            <div className="mkt-row">
              <Button type="submit" disabled={feeState.busy}>
                {feeState.busy ? "Salvando…" : "Salvar taxa"}
              </Button>
            </div>
          </form>

          <section className="admin-card mkt-section" aria-labelledby="mkt-data-title">
            <h2 id="mkt-data-title" className="mkt-h2">
              Dados
            </h2>
            <dl className="mkt-kv">
              <dt>E-mail de acesso</dt>
              <dd>{partner.email ?? "—"}</dd>
              <dt>Documento</dt>
              <dd>{partner.document}</dd>
              <dt>Contato</dt>
              <dd>{partner.contact}</dd>
              <dt>Endereço na loja</dt>
              <dd>/parceiros/{partner.brand_slug}</dd>
            </dl>
            {partner.story ? <p className="mkt-story">{partner.story}</p> : null}
          </section>
        </aside>
      </div>
    </section>
  );
}
