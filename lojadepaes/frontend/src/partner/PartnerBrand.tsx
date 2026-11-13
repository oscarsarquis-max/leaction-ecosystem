import { useState, type FormEvent } from "react";
import { PartnerMark } from "../admin/marketplace/PartnerMark";
import { Photo } from "../admin/marketplace/Photo";
import type { Partner } from "../admin/marketplace/types";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, partnerApi } from "./partnerApi";

type Props = {
  partner: Partner;
  onSaved: (partner: Partner) => void;
  onBack: () => void;
};

type Draft = Pick<Partner, "brand_name" | "city" | "region" | "highlight_hex" | "logo_url" | "photo_url" | "story">;

function draftOf(partner: Partner): Draft {
  return {
    brand_name: partner.brand_name,
    city: partner.city,
    region: partner.region,
    highlight_hex: partner.highlight_hex,
    logo_url: partner.logo_url,
    photo_url: partner.photo_url,
    story: partner.story,
  };
}

export function PartnerBrand({ partner, onSaved, onBack }: Props) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(partner));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const locked = partner.status === "paused";

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const next = await partnerApi.profile({ ...draft, highlight_hex: draft.highlight_hex.toUpperCase() });
      onSaved(next);
      setDraft(draftOf(next));
      setSaved(true);
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível salvar a marca.");
    } finally {
      setBusy(false);
    }
  }

  const validHex = /^#[0-9a-fA-F]{6}$/.test(draft.highlight_hex);

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
          <h1>Minha marca</h1>
          <p>É assim que a Loja de Pães apresenta você na vitrine, ao lado do pão da casa.</p>
        </div>
      </header>
      <div className="ptn-brand-grid">
        <form className="admin-card mkt-form" onSubmit={(event) => void submit(event)} noValidate>
          <fieldset className="mkt-fieldset" disabled={locked}>
            <legend>Marca</legend>
            <div className="mkt-grid mkt-grid-3">
              <label className="mkt-field mkt-span-2">
                Nome da marca
                <input className="mkt-input" maxLength={120} value={draft.brand_name} onChange={(event) => set("brand_name", event.target.value)} />
              </label>
              <label className="mkt-field">
                Cor da marca
                <span className="mkt-color">
                  <input type="color" value={validHex ? draft.highlight_hex : "#000000"} onChange={(event) => set("highlight_hex", event.target.value)} aria-label="Escolher cor" />
                  <input className="mkt-input" maxLength={7} value={draft.highlight_hex} onChange={(event) => set("highlight_hex", event.target.value)} aria-label="Cor em hexadecimal" />
                </span>
              </label>
              <label className="mkt-field">
                Cidade
                <input className="mkt-input" maxLength={80} value={draft.city} onChange={(event) => set("city", event.target.value)} />
              </label>
              <label className="mkt-field">
                Região
                <input className="mkt-input" maxLength={80} value={draft.region} onChange={(event) => set("region", event.target.value)} />
              </label>
              <label className="mkt-field">
                Logo (endereço da imagem)
                <input className="mkt-input" type="url" maxLength={500} placeholder="https://" value={draft.logo_url} onChange={(event) => set("logo_url", event.target.value)} />
              </label>
              <label className="mkt-field mkt-span-3">
                Foto da marca (endereço da imagem)
                <input className="mkt-input" type="url" maxLength={500} placeholder="https://" value={draft.photo_url} onChange={(event) => set("photo_url", event.target.value)} />
              </label>
              <label className="mkt-field mkt-span-3">
                História
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
          {error ? (
            <p className="mkt-alert" role="alert">
              {error}
            </p>
          ) : null}
          {saved ? (
            <p className="mkt-ok" role="status">
              Marca salva.
            </p>
          ) : null}
          {locked ? null : (
            <div className="mkt-form-foot">
              <Button type="submit" variant="primary" disabled={busy}>
                {busy ? "Salvando…" : "Salvar marca"}
              </Button>
            </div>
          )}
        </form>

        <aside className="admin-card ptn-preview" aria-label="Como aparece na vitrine">
          <p className="mkt-eyebrow">A Loja de Pães apresenta</p>
          {draft.photo_url.trim() ? (
            <Photo className="ptn-preview-photo" src={draft.photo_url.trim()} alt={`Foto de ${draft.brand_name}`} />
          ) : (
            <span className="ptn-preview-photo mkt-photo-missing">Sem foto da marca</span>
          )}
          <div className="ptn-preview-body" style={{ borderTopColor: validHex ? draft.highlight_hex : "transparent" }}>
            <div className="mkt-brand">
              <PartnerMark partner={{ brand_name: draft.brand_name || "Marca", highlight_hex: validHex ? draft.highlight_hex : "#6B645A", logo_url: draft.logo_url.trim() }} size="lg" />
              <div className="mkt-brand-text">
                <strong>{draft.brand_name || "Nome da marca"}</strong>
                <span className="mkt-muted">
                  {[draft.city, draft.region].filter(Boolean).join(" · ") || "Cidade · Região"}
                </span>
              </div>
            </div>
            {draft.story ? <p className="mkt-story">{draft.story}</p> : null}
          </div>
          <p className="mkt-muted">Endereço na loja: /parceiros/{partner.brand_slug}</p>
        </aside>
      </div>
    </>
  );
}
