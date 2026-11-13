import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { formatCents, parseBrlToCents } from "../lib/money";
import { CATEGORIES, decisionLabel, productStatus, stampLabel } from "../admin/marketplace/labels";
import type { PartnerProduct, ProductReview } from "../admin/marketplace/types";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, houseBreads, partnerApi, type HouseBread } from "./partnerApi";
import { MAX_PHOTOS, PhotoPicker } from "./PhotoPicker";

type Props = {
  productId: string | null;
  paused: boolean;
  onBack: () => void;
  onSaved: (id: string) => void;
};

type Pair = { house_product_slug: string; reason: string };

type Draft = {
  category: string;
  name: string;
  description: string;
  photos: string[];
  pairings: Pair[];
  cities: string;
  districts: string;
  ceps: string;
  days: string;
  freight: string;
  price: string;
  perishable: boolean;
  available: boolean;
};

const EMPTY: Draft = {
  category: "",
  name: "",
  description: "",
  photos: [],
  pairings: [{ house_product_slug: "", reason: "" }],
  cities: "",
  districts: "",
  ceps: "",
  days: "",
  freight: "",
  price: "",
  perishable: false,
  available: true,
};

function money(cents: number | null): string {
  return cents === null ? "" : formatCents(cents).replace("R$ ", "");
}

function fromProduct(product: PartnerProduct): Draft {
  const photos = product.photos.slice(0, MAX_PHOTOS);
  return {
    category: product.category,
    name: product.name,
    description: product.description,
    photos,
    pairings: product.pairings.length
      ? product.pairings.map((row) => ({ house_product_slug: row.house_product_slug, reason: row.reason }))
      : [{ house_product_slug: "", reason: "" }],
    cities: product.delivery_cities.join(", "),
    districts: product.delivery_districts.join(", "),
    ceps: product.delivery_cep_prefixes.join(", "),
    days: product.delivery_days === null ? "" : String(product.delivery_days),
    freight: money(product.freight_cents),
    price: money(product.price_cents),
    perishable: product.perishable,
    available: product.is_available,
  };
}

function list(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function cents(text: string, label: string, allowZero: boolean): number | null {
  const value = text.trim();
  if (!value) {
    return null;
  }
  if (allowZero && /^0+(,0+)?$/.test(value)) {
    return 0;
  }
  try {
    return parseBrlToCents(value);
  } catch {
    throw new Error(`${label}: informe o valor como 24,90.`);
  }
}

export function PartnerProductForm({ productId, paused, onBack, onSaved }: Props) {
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [product, setProduct] = useState<PartnerProduct | null>(null);
  const [reviews, setReviews] = useState<ProductReview[]>([]);
  const [breads, setBreads] = useState<HouseBread[]>([]);
  const [loading, setLoading] = useState(productId !== null);
  const [busy, setBusy] = useState<"save" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const loadedId = useRef<string | null>(null);

  useEffect(() => {
    houseBreads()
      .then(setBreads)
      .catch(() => setBreads([]));
  }, []);

  useEffect(() => {
    if (!productId) {
      loadedId.current = null;
      setProduct(null);
      setDraft(EMPTY);
      setReviews([]);
      setLoading(false);
      return;
    }
    if (loadedId.current === productId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([partnerApi.products(), partnerApi.reviews(productId).catch(() => [] as ProductReview[])])
      .then(([rows, history]) => {
        if (cancelled) {
          return;
        }
        const found = rows.find((row) => row.id === productId) ?? null;
        loadedId.current = found?.id ?? null;
        setProduct(found);
        if (found) {
          setDraft(fromProduct(found));
        }
        setReviews(history);
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível abrir o produto.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [productId]);

  const status = product?.status ?? "draft";
  const locked = paused || status === "paused";
  const checks = useMemo(
    () => [
      { label: "Categoria", ok: Boolean(draft.category) },
      { label: "Nome", ok: Boolean(draft.name.trim()) },
      { label: "Preço", ok: Boolean(draft.price.trim()) },
      { label: "1 foto", ok: draft.photos.length > 0 },
      { label: "Pão e motivo", ok: draft.pairings.some((row) => row.house_product_slug && row.reason.trim()) },
      { label: "Área de entrega", ok: Boolean(list(draft.cities).length || list(draft.districts).length || list(draft.ceps).length) },
      { label: "Prazo e frete", ok: Boolean(draft.days.trim() && draft.freight.trim()) },
    ],
    [draft],
  );
  const ready = checks.every((check) => check.ok);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setNotice(null);
  }

  function setPair(index: number, patch: Partial<Pair>) {
    set(
      "pairings",
      draft.pairings.map((row, position) => (position === index ? { ...row, ...patch } : row)),
    );
  }

  function body() {
    const price = cents(draft.price, "Preço", false);
    if (price === null) {
      throw new Error("Informe o preço.");
    }
    const days = draft.days.trim() ? Number.parseInt(draft.days.trim(), 10) : null;
    if (days !== null && (!Number.isFinite(days) || days < 0 || days > 60)) {
      throw new Error("Prazo: informe de 0 a 60 dias.");
    }
    return {
      category: draft.category,
      name: draft.name,
      description: draft.description,
      photos: draft.photos,
      price_cents: price,
      is_available: draft.available,
      delivery_cities: list(draft.cities),
      delivery_districts: list(draft.districts),
      delivery_cep_prefixes: list(draft.ceps),
      delivery_days: days,
      freight_cents: cents(draft.freight, "Frete", true),
      perishable: draft.perishable,
      pairings: draft.pairings
        .filter((row) => row.house_product_slug || row.reason.trim())
        .map((row) => ({ house_product_slug: row.house_product_slug, reason: row.reason.trim() })),
    };
  }

  async function save(mode: "save" | "submit", event?: FormEvent) {
    event?.preventDefault();
    setError(null);
    setNotice(null);
    if (!draft.category) {
      setError("Escolha a categoria.");
      return;
    }
    let payload;
    try {
      payload = body();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Confira os campos.");
      return;
    }
    setBusy(mode);
    try {
      let saved = product ? await partnerApi.updateProduct(product.id, payload) : await partnerApi.createProduct(payload);
      if (mode === "submit" && ["draft", "returned", "rejected"].includes(saved.status)) {
        saved = await partnerApi.submitProduct(saved.id);
      }
      loadedId.current = saved.id;
      setProduct(saved);
      setDraft(fromProduct(saved));
      setNotice(
        saved.status === "pending"
          ? "Enviado para avaliação. A Loja de Pães avisa quando decidir."
          : "Rascunho salvo.",
      );
      if (!productId) {
        onSaved(saved.id);
      }
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível salvar.");
    } finally {
      setBusy(null);
    }
  }

  const back = (
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
  );

  if (loading) {
    return (
      <>
        {back}
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      </>
    );
  }
  if (productId && !product) {
    return (
      <>
        {back}
        <p className="mkt-alert" role="alert">
          {error ?? "Produto não encontrado."}
        </p>
      </>
    );
  }

  const tone = productStatus(status);
  const lastReview = reviews[reviews.length - 1];
  const breadOptions = breads.slice();
  for (const row of draft.pairings) {
    if (row.house_product_slug && !breadOptions.some((bread) => bread.slug === row.house_product_slug)) {
      const known = product?.pairings.find((pair) => pair.house_product_slug === row.house_product_slug);
      breadOptions.push({ slug: row.house_product_slug, name: known?.house_product_name ?? row.house_product_slug });
    }
  }
  const primary =
    status === "approved"
      ? "Salvar e reenviar para avaliação"
      : status === "pending"
        ? "Salvar alterações"
        : "Enviar para avaliação";

  return (
    <>
      {back}
      <header className="admin-page-header">
        <div>
          <div className="mkt-title-row">
            <h1>{product ? product.name : "Novo produto"}</h1>
            {product ? (
              <span className={`admin-chip ${tone.tone}`}>
                <span className="dot" aria-hidden="true" />
                {tone.label}
              </span>
            ) : null}
          </div>
          <p>Só categorias que acompanham pão. Pães, focaccias e confeitaria são da casa.</p>
        </div>
      </header>

      {lastReview && (status === "returned" || status === "rejected") ? (
        <div className="ptn-banner is-warn" role="status">
          <strong>
            {decisionLabel(lastReview.decision)} em {stampLabel(lastReview.reviewed_at)}
          </strong>
          {lastReview.note ? <span>Loja: “{lastReview.note}”</span> : null}
          <span className="mkt-muted">
            Notas: qualidade {lastReview.quality}, visual {lastReview.visual}, complementaridade {lastReview.complementarity}.
          </span>
        </div>
      ) : null}
      {status === "approved" ? (
        <p className="ptn-banner" role="status">
          Este produto está na vitrine. Salvar uma alteração o manda de volta para avaliação.
        </p>
      ) : null}
      {locked ? (
        <p className="ptn-banner is-warn" role="status">
          {status === "paused" ? "Produto pausado pela Loja de Pães." : "Sua conta está pausada."} Não é possível alterar.
        </p>
      ) : null}

      <form className="admin-card mkt-form" onSubmit={(event) => void save("submit", event)} noValidate>
        <fieldset className="mkt-fieldset" disabled={locked}>
          <legend>Produto</legend>
          <div className="mkt-grid mkt-grid-3">
            <label className="mkt-field">
              Categoria
              <select className="mkt-input" value={draft.category} onChange={(event) => set("category", event.target.value)}>
                <option value="">Escolha</option>
                {CATEGORIES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="mkt-field mkt-span-2">
              Nome
              <input
                className="mkt-input"
                maxLength={120}
                value={draft.name}
                onChange={(event) => set("name", event.target.value)}
                placeholder="Ex.: Queijo de casca florida 250 g"
              />
            </label>
            <label className="mkt-field mkt-span-3">
              Descrição
              <textarea
                className="mkt-input mkt-textarea"
                maxLength={4000}
                value={draft.description}
                onChange={(event) => set("description", event.target.value)}
                placeholder="Origem, processo, sabor"
              />
            </label>
          </div>
        </fieldset>

        <fieldset className="mkt-fieldset" disabled={locked}>
          <legend>Fotos (até 3)</legend>
          <p className="mkt-muted">Fotos claras, com o produto aberto ou cortado. A primeira é a principal na vitrine.</p>
          <PhotoPicker photos={draft.photos} disabled={locked} onChange={(photos) => set("photos", photos)} />
        </fieldset>

        <fieldset className="mkt-fieldset" disabled={locked}>
          <legend>Combina com qual pão da casa?</legend>
          {draft.pairings.map((row, index) => (
            <div key={index} className="ptn-pair-row">
              <label className="mkt-field">
                Pão
                <select
                  className="mkt-input"
                  value={row.house_product_slug}
                  onChange={(event) => setPair(index, { house_product_slug: event.target.value })}
                >
                  <option value="">Escolha</option>
                  {breadOptions.map((bread) => (
                    <option key={bread.slug} value={bread.slug}>
                      {bread.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="mkt-field">
                Por que combina
                <input
                  className="mkt-input"
                  maxLength={400}
                  value={row.reason}
                  onChange={(event) => setPair(index, { reason: event.target.value })}
                  placeholder="Ex.: a acidez do pão corta a gordura do queijo"
                />
              </label>
              {draft.pairings.length > 1 ? (
                <Button
                  className="ptn-pair-remove"
                  onClick={() => set("pairings", draft.pairings.filter((_, position) => position !== index))}
                  aria-label={`Remover pão ${index + 1}`}
                >
                  Remover
                </Button>
              ) : null}
            </div>
          ))}
          {draft.pairings.length < 3 ? (
            <div className="mkt-row">
              <Button onClick={() => set("pairings", [...draft.pairings, { house_product_slug: "", reason: "" }])}>
                Adicionar outro pão
              </Button>
            </div>
          ) : null}
        </fieldset>

        <fieldset className="mkt-fieldset" disabled={locked}>
          <legend>
            Preço e entrega <span className="mkt-muted">· a Loja não entrega seus produtos</span>
          </legend>
          <div className="mkt-grid mkt-grid-3">
            <label className="mkt-field">
              Preço (R$)
              <input className="mkt-input mkt-num" inputMode="decimal" placeholder="Ex.: 46,00" value={draft.price} onChange={(event) => set("price", event.target.value)} />
            </label>
            <label className="mkt-field">
              Prazo (dias após o pedido)
              <input className="mkt-input mkt-num" inputMode="numeric" placeholder="Ex.: 2" value={draft.days} onChange={(event) => set("days", event.target.value)} />
            </label>
            <label className="mkt-field">
              Frete (R$)
              <input className="mkt-input mkt-num" inputMode="decimal" placeholder="Ex.: 12,00" value={draft.freight} onChange={(event) => set("freight", event.target.value)} />
            </label>
            <label className="mkt-field">
              Cidades atendidas
              <input className="mkt-input" placeholder="Ex.: Fortaleza, Eusébio" value={draft.cities} onChange={(event) => set("cities", event.target.value)} />
            </label>
            <label className="mkt-field">
              Bairros (opcional)
              <input className="mkt-input" placeholder="Ex.: Aldeota, Meireles" value={draft.districts} onChange={(event) => set("districts", event.target.value)} />
            </label>
            <label className="mkt-field">
              Início do CEP (opcional)
              <input className="mkt-input" inputMode="numeric" placeholder="Ex.: 60, 61" value={draft.ceps} onChange={(event) => set("ceps", event.target.value)} />
            </label>
          </div>
          <div className="ptn-checks">
            <label className="ptn-check">
              <input type="checkbox" checked={draft.perishable} onChange={(event) => set("perishable", event.target.checked)} />
              Perecível (precisa de refrigeração)
            </label>
            <label className="ptn-check">
              <input type="checkbox" checked={draft.available} onChange={(event) => set("available", event.target.checked)} />
              Disponível para venda
            </label>
          </div>
        </fieldset>

        {locked ? null : (
          <div className="ptn-foot">
            <ul className="ptn-ready" aria-label="Para enviar à avaliação">
              {checks.map((check) => (
                <li key={check.label} className={check.ok ? "is-ok" : ""}>
                  <span className="ptn-dot" aria-hidden="true" />
                  {check.label}
                  <span className="mkt-sr">{check.ok ? ": feito" : ": falta"}</span>
                </li>
              ))}
            </ul>
            {error ? (
              <p className="mkt-alert" role="alert">
                {error}
              </p>
            ) : null}
            {notice ? (
              <p className="mkt-ok" role="status">
                {notice}
              </p>
            ) : null}
            <div className="ptn-actions">
              {status === "pending" || status === "approved" ? null : (
                <Button onClick={() => void save("save")} disabled={busy !== null}>
                  {busy === "save" ? "Salvando…" : "Salvar rascunho"}
                </Button>
              )}
              <Button type="submit" variant="primary" disabled={busy !== null || !ready}>
                {busy === "submit" ? "Enviando…" : primary}
              </Button>
            </div>
          </div>
        )}
      </form>

      {reviews.length ? (
        <section className="admin-card mkt-section" aria-labelledby="ptn-history">
          <h2 id="ptn-history" className="mkt-h2">
            Avaliações da Loja
          </h2>
          <ul className="mkt-list">
            {reviews
              .slice()
              .reverse()
              .map((row) => (
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
    </>
  );
}
