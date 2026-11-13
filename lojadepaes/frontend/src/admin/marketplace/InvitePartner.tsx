import { useState, type FormEvent } from "react";
import { parseBrlToCents } from "../../lib/money";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { MARKETPLACE_API, PARTNER_TYPES, stampLabel } from "./labels";
import { PartnerMark } from "./PartnerMark";
import type { PartnerCreated } from "./types";

type Props = {
  onBack: () => void;
  onCreated: () => void;
  onOpen: (id: string) => void;
};

type Draft = {
  partner_type: string;
  brand_name: string;
  brand_slug: string;
  city: string;
  region: string;
  highlight_hex: string;
  document: string;
  contact: string;
  email: string;
  fee_text: string;
  story: string;
  logo_url: string;
};

const EMPTY: Draft = {
  partner_type: "producer",
  brand_name: "",
  brand_slug: "",
  city: "",
  region: "",
  highlight_hex: "#2F5D3A",
  document: "",
  contact: "",
  email: "",
  fee_text: "2,50",
  story: "",
  logo_url: "",
};

export function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function InvitePartner({ onBack, onCreated, onOpen }: Props) {
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [slugTouched, setSlugTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<PartnerCreated | null>(null);
  const [copied, setCopied] = useState(false);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => {
      const next = { ...current, [key]: value };
      if (key === "brand_name" && !slugTouched) {
        next.brand_slug = slugify(String(value));
      }
      return next;
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    let fee: number | null;
    try {
      fee = draft.fee_text.trim() === "0" || draft.fee_text.trim() === "0,00" ? 0 : parseBrlToCents(draft.fee_text);
    } catch (reason) {
      setError(`Taxa por pedido: ${reason instanceof Error ? reason.message : "valor inválido"}.`);
      return;
    }
    if (fee === null) {
      setError("Informe a taxa por pedido.");
      return;
    }
    setBusy(true);
    try {
      const body = {
        partner_type: draft.partner_type,
        brand_name: draft.brand_name,
        brand_slug: draft.brand_slug,
        city: draft.city,
        region: draft.region,
        highlight_hex: draft.highlight_hex.toUpperCase(),
        document: draft.document,
        contact: draft.contact,
        email: draft.email,
        fee_cents: fee,
        story: draft.story,
        logo_url: draft.logo_url,
      };
      const result = await adminRequest<PartnerCreated>(`${MARKETPLACE_API}/partners`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setCreated(result);
      onCreated();
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível criar o convite.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    const link = `${window.location.origin}${created.invite_link}`;
    return (
      <section className="mkt-page">
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
        <div className="admin-card mkt-invite-done" role="status">
          <div className="mkt-brand">
            <PartnerMark partner={created} size="lg" />
            <div className="mkt-brand-text">
              <h1 className="mkt-h1">Convite criado para {created.brand_name}</h1>
              <p className="mkt-muted">
                Envie este link para {created.email}. Ele vale até {stampLabel(created.invite_expires_at)} e só aparece agora.
              </p>
            </div>
          </div>
          <div className="mkt-copy">
            <label className="mkt-field mkt-grow">
              Link do convite
              <input className="mkt-input" readOnly value={link} onFocus={(event) => event.currentTarget.select()} />
            </label>
            <Button
              variant="primary"
              onClick={() => {
                void navigator.clipboard?.writeText(link).then(
                  () => setCopied(true),
                  () => setCopied(false),
                );
              }}
            >
              {copied ? "Copiado" : "Copiar link"}
            </Button>
          </div>
          <div className="mkt-row">
            <Button onClick={() => onOpen(created.id)}>Abrir parceiro</Button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="mkt-page">
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
      <header className="admin-page-header">
        <div>
          <h1>Convidar parceiro</h1>
          <p>O parceiro recebe um link para criar a senha e cadastrar os produtos. Nada vai para a vitrine sem a avaliação da Loja.</p>
        </div>
      </header>
      <form className="admin-card mkt-form" onSubmit={(event) => void submit(event)} noValidate>
        <fieldset className="mkt-fieldset">
          <legend>Marca</legend>
          <div className="mkt-grid mkt-grid-3">
            <label className="mkt-field">
              Tipo
              <select className="mkt-input" value={draft.partner_type} onChange={(event) => set("partner_type", event.target.value)}>
                {PARTNER_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="mkt-field mkt-span-2">
              Nome da marca
              <input
                className="mkt-input"
                required
                maxLength={120}
                value={draft.brand_name}
                onChange={(event) => set("brand_name", event.target.value)}
                placeholder="Ex.: Queijaria Serra Clara"
              />
            </label>
            <div className="mkt-field">
              <label htmlFor="mkt-slug">Endereço na loja</label>
              <input
                id="mkt-slug"
                className="mkt-input"
                required
                maxLength={80}
                value={draft.brand_slug}
                onChange={(event) => {
                  setSlugTouched(true);
                  set("brand_slug", event.target.value);
                }}
                aria-describedby="mkt-slug-help"
              />
              <span id="mkt-slug-help" className="mkt-help">
                /parceiros/{draft.brand_slug || "nome-da-marca"}
              </span>
            </div>
            <label className="mkt-field">
              Cidade
              <input className="mkt-input" required maxLength={80} value={draft.city} onChange={(event) => set("city", event.target.value)} />
            </label>
            <label className="mkt-field">
              Região
              <input
                className="mkt-input"
                required
                maxLength={80}
                value={draft.region}
                onChange={(event) => set("region", event.target.value)}
                placeholder="Ex.: Ceará"
              />
            </label>
            <label className="mkt-field">
              Cor da marca
              <span className="mkt-color">
                <input
                  type="color"
                  value={/^#[0-9a-fA-F]{6}$/.test(draft.highlight_hex) ? draft.highlight_hex : "#000000"}
                  onChange={(event) => set("highlight_hex", event.target.value)}
                  aria-label="Escolher cor"
                />
                <input
                  className="mkt-input"
                  required
                  maxLength={7}
                  value={draft.highlight_hex}
                  onChange={(event) => set("highlight_hex", event.target.value)}
                  aria-label="Cor em hexadecimal"
                />
              </span>
            </label>
            <label className="mkt-field mkt-span-2">
              Logo (endereço da imagem, opcional)
              <input
                className="mkt-input"
                type="url"
                maxLength={500}
                value={draft.logo_url}
                onChange={(event) => set("logo_url", event.target.value)}
                placeholder="https://"
              />
            </label>
            <label className="mkt-field mkt-span-3">
              História (opcional)
              <textarea
                className="mkt-input mkt-textarea"
                maxLength={4000}
                value={draft.story}
                onChange={(event) => set("story", event.target.value)}
                placeholder="Origem, processo, quem faz"
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="mkt-fieldset">
          <legend>Acesso e cobrança</legend>
          <div className="mkt-grid mkt-grid-3">
            <label className="mkt-field">
              E-mail de acesso
              <input
                className="mkt-input"
                type="email"
                required
                maxLength={160}
                autoComplete="off"
                value={draft.email}
                onChange={(event) => set("email", event.target.value)}
              />
            </label>
            <label className="mkt-field">
              CNPJ ou CPF
              <input className="mkt-input" required maxLength={40} value={draft.document} onChange={(event) => set("document", event.target.value)} />
            </label>
            <label className="mkt-field">
              Contato (nome e telefone)
              <input className="mkt-input" required maxLength={160} value={draft.contact} onChange={(event) => set("contact", event.target.value)} />
            </label>
            <div className="mkt-field">
              <label htmlFor="mkt-fee">Taxa por pedido (R$)</label>
              <input
                id="mkt-fee"
                className="mkt-input mkt-num"
                inputMode="decimal"
                required
                value={draft.fee_text}
                onChange={(event) => set("fee_text", event.target.value)}
                aria-describedby="mkt-fee-help"
              />
              <span id="mkt-fee-help" className="mkt-help">
                Paga pelo parceiro em cada pedido. O cliente não paga.
              </span>
            </div>
          </div>
        </fieldset>
        {error ? (
          <p className="mkt-alert" role="alert">
            {error}
          </p>
        ) : null}
        <div className="mkt-form-foot">
          <Button onClick={onBack}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Criando…" : "Criar convite"}
          </Button>
        </div>
      </form>
    </section>
  );
}
