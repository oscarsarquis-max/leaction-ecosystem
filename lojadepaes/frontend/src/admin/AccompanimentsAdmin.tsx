import { useEffect, useState, type FormEvent } from "react";
import { AdminApiError, adminRequest } from "./api";
type Overlay = {
  id: string;
  hub_offer_id: string;
  snapshot_title: string;
  occasion: string;
  story_title: string;
  story_lead: string;
  why_pairs: string;
  serving_tip: string;
  related_product_slugs: string[];
  related_recipe_slugs: string[];
  sort_order: number;
  published: boolean;
};

type HubItem = {
  hub_offer_id: string;
  title: string;
  price_label: string | null;
  link_valid: boolean;
  outbound_href: string | null;
  outbound_label: string;
  vendor: string;
  category: string;
  overlay: Overlay | null;
};

type AdminPayload = {
  curation_home: string;
  hub_ok: boolean;
  hub_items: HubItem[];
  overlays: Overlay[];
  items: Overlay[];
};

const EMPTY = {
  hub_offer_id: "",
  occasion: "",
  story_title: "",
  story_lead: "",
  why_pairs: "",
  serving_tip: "",
  related_product_slugs: [] as string[],
  related_recipe_slugs: [] as string[],
  sort_order: 0,
  published: false,
};

export function AccompanimentsAdmin() {
  const [payload, setPayload] = useState<AdminPayload | null>(null);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  function load() {
    adminRequest<AdminPayload>("/api/v1/admin/accompaniments")
      .then(setPayload)
      .catch((reason) => setError(reason instanceof AdminApiError ? reason.message : "Falha ao carregar."));
  }

  useEffect(() => {
    load();
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy("save");
    setError(null);
    try {
      await adminRequest("/api/v1/admin/accompaniments", {
        method: "POST",
        body: JSON.stringify(draft),
      });
      setDraft(EMPTY);
      load();
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível gravar a narrativa.");
    } finally {
      setBusy(null);
    }
  }

  async function update(item: Overlay) {
    setBusy(item.id);
    setError(null);
    try {
      await adminRequest(`/api/v1/admin/accompaniments/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({
          hub_offer_id: item.hub_offer_id,
          occasion: item.occasion,
          story_title: item.story_title,
          story_lead: item.story_lead,
          why_pairs: item.why_pairs,
          serving_tip: item.serving_tip,
          related_product_slugs: item.related_product_slugs,
          related_recipe_slugs: item.related_recipe_slugs,
          sort_order: item.sort_order,
          published: item.published,
        }),
      });
      load();
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível atualizar.");
    } finally {
      setBusy(null);
    }
  }

  const overlays = payload?.overlays ?? payload?.items ?? [];

  return (
    <section className="admin-page">
      <p className="admin-eyebrow">Complementos</p>
      <h1>Para acompanhar seu pão</h1>
      <p className="admin-lead">
        {payload?.curation_home ||
          "ActionHub → Marketplace → perfil A Loja. Preço, foto e link vêm só de lá. Aqui só narrativa e pães."}
      </p>
      {!payload?.hub_ok ? (
        <p className="admin-muted">O Hub não respondeu agora. As narrativas locais permanecem; não cadastre preço nem link aqui.</p>
      ) : null}
      {error ? <p className="admin-error">{error}</p> : null}
      {payload?.hub_items.length ? (
        <ul className="admin-muted">
          {payload.hub_items.map((item) => (
            <li key={item.hub_offer_id}>
              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    hub_offer_id: item.hub_offer_id,
                    story_title: current.story_title || item.title,
                  }))
                }
              >
                Anexar narrativa a {item.hub_offer_id}
              </button>{" "}
              {item.title}
              {item.price_label ? ` · ${item.price_label}` : ""}
              {` · ${item.outbound_label}`}
              {item.link_valid ? "" : " · sem destino oficial"}
              {item.overlay ? " · narrativa já anexada" : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="admin-muted">Nenhum item no perfil A Loja do Hub. Selecione vinhos, queijos, frios e azeites lá.</p>
      )}
      <form className="admin-note-form" onSubmit={save}>
        <label>
          ID do Hub (já curado no perfil A Loja)
          <input value={draft.hub_offer_id} onChange={(event) => setDraft({ ...draft, hub_offer_id: event.target.value })} required />
        </label>
        <label>
          Ocasião
          <input value={draft.occasion} onChange={(event) => setDraft({ ...draft, occasion: event.target.value })} placeholder="Café da manhã" />
        </label>
        <label>
          Título da história
          <input value={draft.story_title} onChange={(event) => setDraft({ ...draft, story_title: event.target.value })} />
        </label>
        <label>
          Chamada
          <textarea value={draft.story_lead} onChange={(event) => setDraft({ ...draft, story_lead: event.target.value })} />
        </label>
        <label>
          Por que combina
          <textarea value={draft.why_pairs} onChange={(event) => setDraft({ ...draft, why_pairs: event.target.value })} />
        </label>
        <label>
          Dica de servir
          <textarea value={draft.serving_tip} onChange={(event) => setDraft({ ...draft, serving_tip: event.target.value })} />
        </label>
        <label>
          Slugs dos pães
          <input
            value={draft.related_product_slugs.join(" ")}
            onChange={(event) => setDraft({ ...draft, related_product_slugs: event.target.value.split(/\s+/).filter(Boolean) })}
          />
        </label>
        <label>
          Slugs das receitas
          <input
            value={draft.related_recipe_slugs.join(" ")}
            onChange={(event) => setDraft({ ...draft, related_recipe_slugs: event.target.value.split(/\s+/).filter(Boolean) })}
          />
        </label>
        <button type="submit" className="primary" disabled={busy === "save" || !draft.hub_offer_id}>
          Guardar narrativa
        </button>
      </form>
      {overlays.map((item) => (
        <article key={item.id}>
          <h2>{item.snapshot_title || item.hub_offer_id}</h2>
          <p className="admin-muted">{item.hub_offer_id} · narrativa da Loja — preço e link continuam no Hub</p>
          <label>
            Ocasião
            <input value={item.occasion} onChange={(event) => setPayload((current) => current ? { ...current, overlays: current.overlays.map((row) => (row.id === item.id ? { ...row, occasion: event.target.value } : row)), items: current.items.map((row) => (row.id === item.id ? { ...row, occasion: event.target.value } : row)) } : current)} />
          </label>
          <label>
            Título da história
            <input value={item.story_title} onChange={(event) => setPayload((current) => current ? { ...current, overlays: current.overlays.map((row) => (row.id === item.id ? { ...row, story_title: event.target.value } : row)), items: current.items.map((row) => (row.id === item.id ? { ...row, story_title: event.target.value } : row)) } : current)} />
          </label>
          <label>
            Por que combina
            <textarea value={item.why_pairs} onChange={(event) => setPayload((current) => current ? { ...current, overlays: current.overlays.map((row) => (row.id === item.id ? { ...row, why_pairs: event.target.value } : row)), items: current.items.map((row) => (row.id === item.id ? { ...row, why_pairs: event.target.value } : row)) } : current)} />
          </label>
          <label>
            Pães (slugs)
            <input
              value={item.related_product_slugs.join(" ")}
              onChange={(event) =>
                setPayload((current) =>
                  current
                    ? {
                        ...current,
                        overlays: current.overlays.map((row) =>
                          row.id === item.id ? { ...row, related_product_slugs: event.target.value.split(/\s+/).filter(Boolean) } : row,
                        ),
                        items: current.items.map((row) =>
                          row.id === item.id ? { ...row, related_product_slugs: event.target.value.split(/\s+/).filter(Boolean) } : row,
                        ),
                      }
                    : current,
                )
              }
            />
          </label>
          <button type="button" className="primary" disabled={busy === item.id} onClick={() => void update(item)}>
            Gravar narrativa
          </button>
        </article>
      ))}
    </section>
  );
}
