import { useEffect, useRef, useState } from "react";
import { parseBrlToCents } from "../lib/money";
import { AdminApiError, adminRequest } from "./api";
import type { AdminProductDetail, ProductDraft, VariantDraft } from "./productTypes";

function centsToInput(cents: number | null): string {
  if (cents === null) {
    return "";
  }
  const whole = Math.trunc(cents / 100);
  const fraction = cents % 100;
  return `${whole},${fraction.toString().padStart(2, "0")}`;
}

function emptyVariant(partial?: Partial<VariantDraft>): VariantDraft {
  return {
    key: partial?.key ?? crypto.randomUUID(),
    id: partial?.id,
    display_name: partial?.display_name ?? "500 g",
    presentation_type: partial?.presentation_type ?? "weight",
    net_weight_grams: partial?.net_weight_grams ?? "500",
    units_per_pack: partial?.units_per_pack ?? "",
    price_text: partial?.price_text ?? "",
    is_active: partial?.is_active ?? true,
  };
}

function fromDetail(detail: AdminProductDetail): ProductDraft {
  return {
    name: detail.name,
    slug: detail.slug,
    short_description: detail.short_description,
    long_description: detail.long_description ?? "",
    featured_image_alt: detail.featured_image_alt,
    is_available: detail.is_available,
    sort_order: String(detail.sort_order),
    ingredients: detail.ingredients.length ? detail.ingredients.map((row) => row.name) : [""],
    variants: detail.variants.length
      ? detail.variants.map((row) =>
          emptyVariant({
            key: row.id,
            id: row.id,
            display_name: row.display_name,
            presentation_type: row.presentation_type === "pack" ? "pack" : "weight",
            net_weight_grams: row.net_weight_grams ? String(row.net_weight_grams) : "",
            units_per_pack: row.units_per_pack ? String(row.units_per_pack) : "",
            price_text: centsToInput(row.price.cents),
            is_active: row.is_active,
          }),
        )
      : [emptyVariant()],
  };
}

function moveItem<T>(list: T[], index: number, direction: -1 | 1): T[] {
  const target = index + direction;
  if (target < 0 || target >= list.length) {
    return list;
  }
  const next = [...list];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function suggestName(variant: VariantDraft): string {
  if (variant.presentation_type === "weight") {
    return variant.net_weight_grams ? `${variant.net_weight_grams} g` : "Peso";
  }
  const units = Number.parseInt(variant.units_per_pack, 10);
  if (units === 1) {
    return "1 unidade";
  }
  if (units > 1) {
    return `Pacote com ${units} unidades`;
  }
  return "Unidade ou pacote";
}

type EditorProps = {
  productId: string | null;
  onBack: () => void;
  onSaved: (id: string) => void;
};

export function ProductEditor({ productId, onBack, onSaved }: EditorProps) {
  const [draft, setDraft] = useState<ProductDraft>({
    name: "",
    slug: "",
    short_description: "",
    long_description: "",
    featured_image_alt: "",
    is_available: true,
    sort_order: "0",
    ingredients: ["Farinha de trigo", "Água", "Levain", "Sal"],
    variants: [emptyVariant()],
  });
  const [detail, setDetail] = useState<AdminProductDetail | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(productId));
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!productId) {
      return;
    }
    let cancelled = false;
    adminRequest<AdminProductDetail>(`/api/v1/admin/products/${productId}`)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setDetail(data);
        setDraft(fromDetail(data));
        setPreview(data.featured_image?.url ?? null);
        setDirty(false);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof AdminApiError ? reason.message : "Não foi possível abrir o produto.");
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

  useEffect(() => {
    const onLeave = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onLeave);
    return () => window.removeEventListener("beforeunload", onLeave);
  }, [dirty]);

  function update<K extends keyof ProductDraft>(key: K, value: ProductDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setSuccess(null);
    setDirty(true);
  }

  function validate(): Record<string, string> {
    const next: Record<string, string> = {};
    if (!draft.name.trim()) {
      next.name = "Informe o nome.";
    }
    draft.variants.forEach((variant, index) => {
      if (!variant.display_name.trim()) {
        next[`variant-${index}-name`] = "Informe o nome da opção.";
      }
      if (variant.presentation_type === "weight") {
        const grams = Number.parseInt(variant.net_weight_grams, 10);
        if (!Number.isInteger(grams) || grams < 1) {
          next[`variant-${index}-weight`] = "Informe o peso em gramas.";
        }
      } else {
        const units = Number.parseInt(variant.units_per_pack, 10);
        if (!Number.isInteger(units) || units < 1) {
          next[`variant-${index}-pack`] = "Informe quantas unidades vão na embalagem.";
        }
      }
      if (variant.price_text.trim()) {
        try {
          parseBrlToCents(variant.price_text);
        } catch (reason) {
          next[`variant-${index}-price`] = reason instanceof Error ? reason.message : "Preço inválido.";
        }
      }
    });
    return next;
  }

  function payload() {
    return {
      name: draft.name,
      slug: draft.slug || undefined,
      short_description: draft.short_description,
      long_description: draft.long_description || null,
      featured_image_alt: draft.featured_image_alt,
      is_available: draft.is_available,
      sort_order: Number.parseInt(draft.sort_order, 10) || 0,
      expected_updated_at: detail?.updated_at,
      ingredients: draft.ingredients.filter((name) => name.trim()).map((name) => ({ name: name.trim() })),
      variants: draft.variants.map((variant) => ({
        id: variant.id,
        display_name: variant.display_name.trim() || suggestName(variant),
        presentation_type: variant.presentation_type,
        net_weight_grams:
          variant.presentation_type === "weight" ? Number.parseInt(variant.net_weight_grams, 10) : null,
        units_per_pack:
          variant.presentation_type === "pack" ? Number.parseInt(variant.units_per_pack, 10) : null,
        price_text: variant.price_text,
        is_active: variant.is_active,
      })),
    };
  }

  async function uploadIfNeeded(id: string) {
    if (!file) {
      return;
    }
    const body = new FormData();
    body.append("file", file);
    if (draft.featured_image_alt.trim()) {
      body.append("alt", draft.featured_image_alt.trim());
    }
    const updated = await adminRequest<AdminProductDetail>(`/api/v1/admin/products/${id}/image`, {
      method: "POST",
      body,
    });
    setFile(null);
    return updated;
  }

  async function persist(action: "draft" | "publish" | "unpublish" | "archive") {
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError("Revise os campos destacados.");
      return;
    }
    setSaving(action);
    setError(null);
    setSuccess(null);
    try {
      let current = detail;
      if (productId) {
        current = await adminRequest<AdminProductDetail>(`/api/v1/admin/products/${productId}`, {
          method: "PUT",
          body: JSON.stringify(payload()),
        });
      } else {
        current = await adminRequest<AdminProductDetail>("/api/v1/admin/products", {
          method: "POST",
          body: JSON.stringify(payload()),
        });
      }
      const afterImage = await uploadIfNeeded(current.id);
      current = afterImage ?? current;
      if (action === "publish") {
        current = await adminRequest<AdminProductDetail>(`/api/v1/admin/products/${current.id}/publish`, {
          method: "POST",
        });
        setSuccess("Produto publicado na vitrine.");
      } else if (action === "unpublish") {
        current = await adminRequest<AdminProductDetail>(`/api/v1/admin/products/${current.id}/unpublish`, {
          method: "POST",
        });
        setSuccess("Produto voltou a rascunho.");
      } else if (action === "archive") {
        current = await adminRequest<AdminProductDetail>(`/api/v1/admin/products/${current.id}/archive`, {
          method: "POST",
        });
        setSuccess("Produto arquivado.");
      } else {
        setSuccess("Rascunho salvo.");
      }
      setDetail(current);
      setDraft(fromDetail(current));
      setPreview(current.featured_image?.url ?? preview);
      setDirty(false);
      if (!productId) {
        onSaved(current.id);
      }
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível salvar.");
    } finally {
      setSaving(null);
    }
  }

  if (loading) {
    return <p className="admin-muted">Carregando produto…</p>;
  }

  return (
    <section className="admin-page">
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Catálogo</p>
          <h1>{productId ? "Editar produto" : "Novo produto"}</h1>
        </div>
        <button type="button" className="admin-text" onClick={onBack}>
          Voltar à lista
        </button>
      </header>
      {error ? <p className="admin-error">{error}</p> : null}
      {success ? <p className="admin-success">{success}</p> : null}
      {detail?.publication_gaps.length ? (
        <p className="admin-warning">Para publicar, complete: {detail.publication_gaps.join(", ")}.</p>
      ) : null}

      <article>
        <h2>Informações</h2>
        <label>
          Nome
          <input
            value={draft.name}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? "product-name-error" : undefined}
            onChange={(event) => update("name", event.target.value)}
          />
          {fieldErrors.name ? (
            <span className="admin-error" id="product-name-error">
              {fieldErrors.name}
            </span>
          ) : null}
        </label>
        <label>
          Descrição curta
          <textarea
            rows={3}
            maxLength={280}
            value={draft.short_description}
            onChange={(event) => update("short_description", event.target.value)}
          />
        </label>
        <label>
          Descrição detalhada (opcional)
          <textarea
            rows={4}
            value={draft.long_description}
            onChange={(event) => update("long_description", event.target.value)}
          />
        </label>
      </article>

      <article>
        <h2>Imagem destacada</h2>
        {preview ? <img className="admin-preview" src={preview} alt={draft.featured_image_alt || "Prévia"} /> : null}
        <label>
          Foto (JPEG, PNG ou WebP, até 8 MB)
          <input
            ref={fileInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(event) => {
              const next = event.target.files?.[0] ?? null;
              setFile(next);
              if (next) {
                setPreview(URL.createObjectURL(next));
                setDirty(true);
              }
            }}
          />
        </label>
        <label>
          Texto alternativo da foto
          <input
            value={draft.featured_image_alt}
            onChange={(event) => update("featured_image_alt", event.target.value)}
          />
        </label>
      </article>

      <article>
        <h2>Ingredientes básicos</h2>
        <p className="admin-muted">Lista de composição, sem quantidades de receita.</p>
        {draft.ingredients.map((name, index) => (
          <div className="admin-row" key={`ing-${index}`}>
            <input
              value={name}
              onChange={(event) => {
                const next = [...draft.ingredients];
                next[index] = event.target.value;
                update("ingredients", next);
              }}
            />
            <button
              type="button"
              className="admin-text"
              disabled={index === 0}
              aria-label={`Subir ${name.trim() || `ingrediente ${index + 1}`}`}
              onClick={() => update("ingredients", moveItem(draft.ingredients, index, -1))}
            >
              Subir
            </button>
            <button
              type="button"
              className="admin-text"
              disabled={index === draft.ingredients.length - 1}
              aria-label={`Descer ${name.trim() || `ingrediente ${index + 1}`}`}
              onClick={() => update("ingredients", moveItem(draft.ingredients, index, 1))}
            >
              Descer
            </button>
            <button
              type="button"
              className="admin-text"
              aria-label={`Remover ${name.trim() || `ingrediente ${index + 1}`}`}
              onClick={() => update("ingredients", draft.ingredients.filter((_, item) => item !== index))}
            >
              Remover
            </button>
          </div>
        ))}
        <button type="button" className="admin-secondary" onClick={() => update("ingredients", [...draft.ingredients, ""])}>
          Adicionar ingrediente
        </button>
      </article>

      <article>
        <h2>Variações</h2>
        <p className="admin-muted">
          O preço é da opção inteira: duas unidades de 500 g são dois pães de 500 g. Dois pacotes de 6 são 12 pães.
        </p>
        {draft.variants.map((variant, index) => (
          <fieldset key={variant.key} className="admin-variant">
            <legend>Opção {index + 1}</legend>
            <label>
              Como o cliente vê
              <input
                value={variant.display_name}
                aria-invalid={Boolean(fieldErrors[`variant-${index}-name`])}
                aria-describedby={fieldErrors[`variant-${index}-name`] ? `variant-${index}-name-error` : undefined}
                onChange={(event) => {
                  const next = [...draft.variants];
                  next[index] = { ...variant, display_name: event.target.value };
                  update("variants", next);
                }}
              />
              {fieldErrors[`variant-${index}-name`] ? (
                <span className="admin-error" id={`variant-${index}-name-error`}>
                  {fieldErrors[`variant-${index}-name`]}
                </span>
              ) : null}
            </label>
            <label>
              Tipo
              <select
                value={variant.presentation_type}
                onChange={(event) => {
                  const type: VariantDraft["presentation_type"] =
                    event.target.value === "pack" ? "pack" : "weight";
                  const next = [...draft.variants];
                  const updated: VariantDraft = {
                    ...variant,
                    presentation_type: type,
                    net_weight_grams: type === "weight" ? variant.net_weight_grams || "500" : "",
                    units_per_pack: type === "pack" ? variant.units_per_pack || "1" : "",
                  };
                  updated.display_name = suggestName(updated);
                  next[index] = updated;
                  update("variants", next);
                }}
              >
                <option value="weight">Peso fixo</option>
                <option value="pack">Unidade ou pacote</option>
              </select>
            </label>
            {variant.presentation_type === "weight" ? (
              <label>
                Peso de cada pão (gramas)
                <input
                  inputMode="numeric"
                  value={variant.net_weight_grams}
                  aria-invalid={Boolean(fieldErrors[`variant-${index}-weight`])}
                  aria-describedby={fieldErrors[`variant-${index}-weight`] ? `variant-${index}-weight-error` : undefined}
                  onChange={(event) => {
                    const next = [...draft.variants];
                    const updated = { ...variant, net_weight_grams: event.target.value };
                    updated.display_name = suggestName(updated);
                    next[index] = updated;
                    update("variants", next);
                  }}
                />
                {fieldErrors[`variant-${index}-weight`] ? (
                  <span className="admin-error" id={`variant-${index}-weight-error`}>
                    {fieldErrors[`variant-${index}-weight`]}
                  </span>
                ) : null}
              </label>
            ) : (
              <label>
                Unidades nesta embalagem
                <input
                  inputMode="numeric"
                  value={variant.units_per_pack}
                  aria-invalid={Boolean(fieldErrors[`variant-${index}-pack`])}
                  aria-describedby={fieldErrors[`variant-${index}-pack`] ? `variant-${index}-pack-error` : undefined}
                  onChange={(event) => {
                    const next = [...draft.variants];
                    const updated = { ...variant, units_per_pack: event.target.value };
                    updated.display_name = suggestName(updated);
                    next[index] = updated;
                    update("variants", next);
                  }}
                />
                {fieldErrors[`variant-${index}-pack`] ? (
                  <span className="admin-error" id={`variant-${index}-pack-error`}>
                    {fieldErrors[`variant-${index}-pack`]}
                  </span>
                ) : null}
              </label>
            )}
            <label>
              Preço (ex.: 24,90)
              <input
                value={variant.price_text}
                aria-invalid={Boolean(fieldErrors[`variant-${index}-price`])}
                aria-describedby={fieldErrors[`variant-${index}-price`] ? `variant-${index}-price-error` : undefined}
                onChange={(event) => {
                  const next = [...draft.variants];
                  next[index] = { ...variant, price_text: event.target.value };
                  update("variants", next);
                }}
              />
              {fieldErrors[`variant-${index}-price`] ? (
                <span className="admin-error" id={`variant-${index}-price-error`}>
                  {fieldErrors[`variant-${index}-price`]}
                </span>
              ) : null}
            </label>
            <label className="admin-check">
              <input
                type="checkbox"
                checked={variant.is_active}
                onChange={(event) => {
                  const next = [...draft.variants];
                  next[index] = { ...variant, is_active: event.target.checked };
                  update("variants", next);
                }}
              />
              Opção à venda
            </label>
            <div className="admin-row">
              <button
                type="button"
                className="admin-text"
                disabled={index === 0}
                aria-label={`Subir opção ${index + 1}`}
                onClick={() => update("variants", moveItem(draft.variants, index, -1))}
              >
                Subir
              </button>
              <button
                type="button"
                className="admin-text"
                disabled={index === draft.variants.length - 1}
                aria-label={`Descer opção ${index + 1}`}
                onClick={() => update("variants", moveItem(draft.variants, index, 1))}
              >
                Descer
              </button>
              <button
                type="button"
                className="admin-text"
                aria-label={`Remover opção ${index + 1}`}
                onClick={() => update("variants", draft.variants.filter((item) => item.key !== variant.key))}
              >
                Remover opção
              </button>
            </div>
          </fieldset>
        ))}
        <div className="admin-actions">
          <button type="button" className="admin-secondary" onClick={() => update("variants", [...draft.variants, emptyVariant()])}>
            Adicionar 500 g
          </button>
          <button
            type="button"
            className="admin-secondary"
            onClick={() =>
              update("variants", [
                ...draft.variants,
                emptyVariant({ display_name: "800 g", net_weight_grams: "800" }),
              ])
            }
          >
            Adicionar 800 g
          </button>
          <button
            type="button"
            className="admin-secondary"
            onClick={() =>
              update("variants", [
                ...draft.variants,
                emptyVariant({
                  presentation_type: "pack",
                  display_name: "1 unidade",
                  net_weight_grams: "",
                  units_per_pack: "1",
                }),
              ])
            }
          >
            Adicionar 1 unidade
          </button>
          <button
            type="button"
            className="admin-secondary"
            onClick={() =>
              update("variants", [
                ...draft.variants,
                emptyVariant({
                  presentation_type: "pack",
                  display_name: "Pacote com 6 unidades",
                  net_weight_grams: "",
                  units_per_pack: "6",
                }),
              ])
            }
          >
            Adicionar pacote com 6
          </button>
        </div>
      </article>

      <article className="admin-publish">
        <h2>Publicação</h2>
        <label className="admin-check">
          <input
            type="checkbox"
            checked={draft.is_available}
            onChange={(event) => update("is_available", event.target.checked)}
          />
          Disponível para compra
        </label>
        <div className="admin-actions">
          <button type="button" className="admin-secondary" disabled={Boolean(saving)} onClick={() => void persist("draft")}>
            {saving === "draft" ? "Salvando…" : "Salvar rascunho"}
          </button>
          <button type="button" className="admin-primary" disabled={Boolean(saving)} onClick={() => void persist("publish")}>
            {saving === "publish" ? "Publicando…" : "Publicar produto"}
          </button>
          {detail?.editorial_status === "published" ? (
            <button type="button" className="admin-secondary" disabled={Boolean(saving)} onClick={() => void persist("unpublish")}>
              Retirar de publicação
            </button>
          ) : null}
          {detail && detail.editorial_status !== "archived" ? (
            <button type="button" className="admin-danger" disabled={Boolean(saving)} onClick={() => void persist("archive")}>
              Arquivar
            </button>
          ) : null}
        </div>
      </article>
    </section>
  );
}
