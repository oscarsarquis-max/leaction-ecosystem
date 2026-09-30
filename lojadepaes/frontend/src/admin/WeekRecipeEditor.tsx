import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AdminApiError, actionErrorMessage, adminRequest } from "./api";
import { CatalogTabs } from "./CatalogTabs";
import type { AdminProductList } from "./productTypes";
import { clearRecipeDraft, persistRecipeDraft, recoverRecipeDraft, recoveryMessage } from "./recipeDraft";
import { WeekRecipeCard } from "../shop/WeekRecipeCard";
import { ingredientsToText, stepsToMethodText, textToIngredients } from "../shop/recipeText";
import type { WeekRecipeAdmin, WeekRecipePublic } from "../shop/weekRecipe";
import "./week-recipe-editor.css";

type Draft = {
  title: string;
  summary: string;
  featured_image_alt: string;
  featured_image_caption: string;
  image_focus_x: number;
  image_focus_y: number;
  prep_time_text: string;
  yield_text: string;
  ingredientsText: string;
  methodText: string;
  product_ids: string[];
};

const emptyDraft: Draft = {
  title: "",
  summary: "",
  featured_image_alt: "",
  featured_image_caption: "",
  image_focus_x: 50,
  image_focus_y: 50,
  prep_time_text: "",
  yield_text: "",
  ingredientsText: "",
  methodText: "",
  product_ids: [],
};

function fromAdmin(detail: WeekRecipeAdmin): Draft {
  return {
    title: detail.title,
    summary: detail.summary,
    featured_image_alt: detail.featured_image_alt,
    featured_image_caption: detail.featured_image_caption,
    image_focus_x: detail.image_focus_x,
    image_focus_y: detail.image_focus_y,
    prep_time_text: detail.prep_time_text,
    yield_text: detail.yield_text ?? "",
    ingredientsText: ingredientsToText(detail.ingredients),
    methodText: (detail.method_text || stepsToMethodText(detail.steps)).replace(/\r\n/g, "\n"),
    product_ids: detail.product_ids,
  };
}

function snapshot(draft: Draft): string {
  return JSON.stringify(draft);
}

function statusLabel(detail: WeekRecipeAdmin | null, dirty: boolean): string {
  if (!detail) {
    return dirty ? "Não salvo · rascunho só neste navegador" : "Nova receita · rascunho ainda não salvo";
  }
  const state =
    detail.editorial_status === "published"
      ? detail.is_featured
        ? "Publicada · destaque da home"
        : "Publicada · sem destaque na home"
      : detail.editorial_status === "archived"
        ? "Arquivada"
        : "Rascunho salvo";
  return dirty ? `${state} · alterações não salvas` : state;
}

function localGaps(draft: Draft, hasImage: boolean): string[] {
  const gaps: string[] = [];
  if (!draft.title.trim()) {
    gaps.push("o título");
  }
  if (!draft.summary.trim()) {
    gaps.push("o resumo");
  }
  if (!hasImage) {
    gaps.push("a foto de destaque");
  }
  if (!draft.featured_image_alt.trim()) {
    gaps.push("o texto alternativo da foto");
  }
  if (!textToIngredients(draft.ingredientsText).length) {
    gaps.push("pelo menos um ingrediente");
  }
  if (!draft.methodText.trim()) {
    gaps.push("o modo de preparo");
  }
  return gaps;
}

type Props = {
  recipeId: string | null;
  onBack: () => void;
  onSaved: (id: string) => void;
};

function ActionBar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`wre-actions ${className ?? ""}`}>{children}</div>;
}

export function WeekRecipeEditor({ recipeId, onBack, onSaved }: Props) {
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [savedSnap, setSavedSnap] = useState(snapshot(emptyDraft));
  const [detail, setDetail] = useState<WeekRecipeAdmin | null>(null);
  const [products, setProducts] = useState<AdminProductList | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [breadsOpen, setBreadsOpen] = useState(false);
  const [needsReauth, setNeedsReauth] = useState(false);
  const [ready, setReady] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const loadGen = useRef(0);
  const typedRef = useRef(false);

  const dirty = snapshot(draft) !== savedSnap || pendingFile !== null;
  const photoUrl = pendingUrl || previewUrl;
  const hasImage = Boolean(photoUrl);
  const gaps = detail?.id && !dirty && !pendingFile ? detail.publish_gaps : localGaps(draft, hasImage);
  const ingredients = textToIngredients(draft.ingredientsText);

  useEffect(() => {
    adminRequest<AdminProductList>("/api/v1/admin/products?status=published&page_size=50")
      .then(setProducts)
      .catch(() => setProducts(null));
  }, []);

  useEffect(() => {
    if (recipeId && detail?.id === recipeId) {
      setReady(true);
      return;
    }
    const generation = ++loadGen.current;
    setReady(false);
    if (!recipeId) {
      void recoverRecipeDraft(null).then((recovered) => {
        if (generation !== loadGen.current || typedRef.current) {
          setReady(true);
          return;
        }
        if (!recovered || snapshot(recovered.draft) === snapshot(emptyDraft)) {
          setDraft(emptyDraft);
          setSavedSnap(snapshot(emptyDraft));
          setDetail(null);
          setPreviewUrl(null);
          setReady(true);
          return;
        }
        setDraft(recovered.draft);
        setSavedSnap(snapshot(emptyDraft));
        if (recovered.file) {
          setPendingFile(recovered.file);
          setPendingUrl(URL.createObjectURL(recovered.file));
        }
        setNotice(recoveryMessage(recovered));
        setReady(true);
      });
      return;
    }
    adminRequest<WeekRecipeAdmin>(`/api/v1/admin/week-recipes/${recipeId}`)
      .then(async (data) => {
        if (generation !== loadGen.current) {
          return;
        }
        const next = fromAdmin(data);
        const recovered = await recoverRecipeDraft(recipeId);
        if (generation !== loadGen.current) {
          return;
        }
        setDetail(data);
        setPreviewUrl(data.image_url);
        if (recovered && snapshot(recovered.draft) !== snapshot(next) && snapshot(recovered.draft) !== snapshot(emptyDraft)) {
          setDraft(recovered.draft);
          setSavedSnap(snapshot(next));
          if (recovered.file) {
            setPendingFile(recovered.file);
            setPendingUrl(URL.createObjectURL(recovered.file));
          }
          setNotice(recoveryMessage(recovered));
        } else {
          setDraft(next);
          setSavedSnap(snapshot(next));
        }
        setReady(true);
      })
      .catch((reason) => {
        if (generation !== loadGen.current) {
          return;
        }
        setError(actionErrorMessage(reason, "Não foi possível abrir a receita."));
        setReady(true);
      });
  }, [recipeId, detail?.id]);

  useEffect(() => {
    if (!ready) {
      return;
    }
    if (!recipeId && !detail?.id && snapshot(draft) === snapshot(emptyDraft) && !pendingFile) {
      return;
    }
    persistRecipeDraft(recipeId ?? detail?.id ?? null, draft, pendingFile);
  }, [draft, pendingFile, recipeId, detail?.id, ready]);

  useEffect(() => {
    const onLeave = (event: BeforeUnloadEvent) => {
      if (!dirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onLeave);
    return () => window.removeEventListener("beforeunload", onLeave);
  }, [dirty]);

  useEffect(() => {
    return () => {
      if (pendingUrl) {
        URL.revokeObjectURL(pendingUrl);
      }
    };
  }, [pendingUrl]);

  const preview: WeekRecipePublic = useMemo(
    () => ({
      title: draft.title || "Sem título",
      slug: detail?.slug ?? "pre-via",
      summary: draft.summary,
      image_url: photoUrl,
      image_alt: draft.featured_image_alt,
      image_caption: draft.featured_image_caption,
      image_focus: `${draft.image_focus_x}% ${draft.image_focus_y}%`,
      prep_time: draft.prep_time_text || null,
      yield_text: draft.yield_text || null,
      ingredients,
      method_text: draft.methodText,
      steps: [],
      breads: draft.product_ids.map((id) => {
        const product = products?.items.find((item) => item.id === id);
        return { name: product?.name ?? "Pão", slug: product?.slug ?? null, href: product ? `/paes/${product.slug}` : null };
      }),
      href: detail ? `/receitas/${detail.slug}` : "/#paes",
    }),
    [detail, draft, ingredients, photoUrl, products],
  );

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    typedRef.current = true;
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function askLeave(): boolean {
    if (!dirty) {
      return true;
    }
    return window.confirm("Há alterações que ainda não foram salvas. Deseja sair mesmo assim?");
  }

  function applySaved(saved: WeekRecipeAdmin, ok: string) {
    const next = fromAdmin(saved);
    setDetail(saved);
    setDraft(next);
    setSavedSnap(snapshot(next));
    setPreviewUrl(saved.image_url);
    setNotice(ok);
    setNeedsReauth(false);
    if (!recipeId) {
      onSaved(saved.id);
    }
  }

  async function uploadTo(id: string, file: File): Promise<WeekRecipeAdmin> {
    const body = new FormData();
    body.append("file", file);
    if (draft.featured_image_alt.trim()) {
      body.append("alt", draft.featured_image_alt.trim());
    }
    return adminRequest<WeekRecipeAdmin>(`/api/v1/admin/week-recipes/${id}/image`, {
      method: "POST",
      body,
    });
  }

  async function persistDraft(): Promise<WeekRecipeAdmin> {
    const payload = {
      title: draft.title,
      summary: draft.summary,
      featured_image_alt: draft.featured_image_alt,
      featured_image_caption: draft.featured_image_caption,
      image_focus_x: draft.image_focus_x,
      image_focus_y: draft.image_focus_y,
      prep_time_text: draft.prep_time_text,
      yield_text: draft.yield_text,
      ingredients,
      method_text: draft.methodText,
      product_ids: draft.product_ids,
    };
    const existingId = recipeId || detail?.id;
    let saved = existingId
      ? await adminRequest<WeekRecipeAdmin>(`/api/v1/admin/week-recipes/${existingId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        })
      : await adminRequest<WeekRecipeAdmin>("/api/v1/admin/week-recipes", {
          method: "POST",
          body: JSON.stringify(payload),
        });
    if (!existingId) {
      setDetail(saved);
      onSaved(saved.id);
    }
    if (pendingFile) {
      saved = await uploadTo(saved.id, pendingFile);
      if (pendingUrl) {
        URL.revokeObjectURL(pendingUrl);
      }
      setPendingFile(null);
      setPendingUrl(null);
    }
    clearRecipeDraft();
    return saved;
  }

  function noteFailure(reason: unknown, fallback: string) {
    const message = actionErrorMessage(reason, fallback);
    setError(message);
    setNeedsReauth(reason instanceof AdminApiError && (reason.status === 401 || reason.status === 403));
  }

  async function save(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const hadFile = pendingFile !== null;
      const saved = await persistDraft();
      applySaved(saved, hadFile ? "Rascunho e foto salvos." : "Rascunho salvo.");
    } catch (reason) {
      noteFailure(reason, "Não foi possível salvar. O texto preenchido foi mantido.");
    } finally {
      setSaving(false);
    }
  }

  async function publish(mode: "featured" | "plain") {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await persistDraft();
      applySaved(saved, "Rascunho salvo.");
      if (saved.publish_gaps.length) {
        setError("Ainda não dá para publicar. Complete: " + saved.publish_gaps.join(", ") + ".");
        return;
      }
      if (mode === "featured" && saved.other_featured_title) {
        const ok = window.confirm(
          `“${saved.other_featured_title}” deixa de ser o destaque da home. Essa receita continua publicada.`,
        );
        if (!ok) {
          setNotice("Rascunho salvo. A publicação foi cancelada.");
          return;
        }
      }
      const path = mode === "featured" ? "publish-featured" : "publish";
      const published = await adminRequest<WeekRecipeAdmin>(`/api/v1/admin/week-recipes/${saved.id}/${path}`, {
        method: "POST",
      });
      applySaved(
        published,
        mode === "featured"
          ? "Receita publicada e destacada na home."
          : "Receita publicada, sem alterar o destaque da home.",
      );
    } catch (reason) {
      noteFailure(reason, "Não foi possível publicar. O texto preenchido foi mantido.");
    } finally {
      setSaving(false);
    }
  }

  async function act(path: string, ok: string) {
    if (!detail) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (dirty) {
        const saved = await persistDraft();
        applySaved(saved, "Rascunho salvo.");
      }
      const saved = await adminRequest<WeekRecipeAdmin>(`/api/v1/admin/week-recipes/${detail.id}/${path}`, {
        method: "POST",
      });
      applySaved(saved, ok);
    } catch (reason) {
      noteFailure(reason, "Não foi possível concluir.");
    } finally {
      setSaving(false);
    }
  }

  function chooseFile(file: File | undefined) {
    if (!file) {
      return;
    }
    typedRef.current = true;
    if (pendingUrl) {
      URL.revokeObjectURL(pendingUrl);
    }
    setPendingFile(file);
    setPendingUrl(URL.createObjectURL(file));
    setNotice(
      detail
        ? "Foto selecionada. Ela só substitui a imagem atual depois do envio bem-sucedido."
        : "Foto selecionada. Será enviada ao salvar, sem criar receita em duplicata.",
    );
  }

  const actions = (
    <>
      <button type="button" className="admin-primary" disabled={saving} onClick={() => void save()}>
        Salvar rascunho
      </button>
      <button type="button" className="admin-primary" disabled={saving} onClick={() => void publish("featured")}>
        Publicar e destacar na home
      </button>
      <button type="button" className="admin-secondary" disabled={saving} onClick={() => void publish("plain")}>
        Publicar sem destacar
      </button>
      {detail?.is_featured ? (
        <button type="button" className="admin-secondary" disabled={saving} onClick={() => void act("unfeature", "Destaque retirado. A receita continua publicada.")}>
          Retirar destaque
        </button>
      ) : null}
      {detail && detail.editorial_status !== "archived" ? (
        <button type="button" className="admin-text" disabled={saving} onClick={() => void act("archive", "Receita arquivada.")}>
          Arquivar
        </button>
      ) : null}
      <p className="wre-save-state" role="status">
        {saving ? "Salvando…" : error ? "Erro ao salvar" : notice || (dirty ? "Alterações não salvas" : "Salvo")}
      </p>
    </>
  );

  return (
    <section className="admin-page week-recipe-editor">
      <CatalogTabs current="recipes" />
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Receitas da semana</p>
          <h1>{recipeId || detail ? "Editar receita" : "Nova receita"}</h1>
          <p className="wre-status">{statusLabel(detail, dirty)}</p>
        </div>
        <button
          type="button"
          className="admin-text"
          onClick={() => {
            if (askLeave()) {
              onBack();
            }
          }}
        >
          Voltar à lista
        </button>
      </header>
      {error ? <p className="admin-error">{error}</p> : null}
      {notice ? <p className="admin-success">{notice}</p> : null}
      {needsReauth ? (
        <p className="wre-reauth admin-warning">
          Use o menu da conta no alto da página para entrar de novo. O texto desta receita permanece no formulário e
          neste navegador.
        </p>
      ) : null}
      <ActionBar>{actions}</ActionBar>
      {gaps.length ? (
        <>
          <p className="admin-warning">Para publicar e destacar, ainda falta:</p>
          <ul className="wre-gaps">
            {gaps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="admin-muted">Pronto para publicar quando você quiser. Salvar rascunho não publica.</p>
      )}
      <div className="wre-tabs" role="tablist" aria-label="Editor e prévia">
        <button type="button" role="tab" aria-selected={tab === "edit"} onClick={() => setTab("edit")}>
          Edição
        </button>
        <button type="button" role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>
          Prévia
        </button>
      </div>
      {tab === "preview" ? (
        <div className="wre-preview-panel">
          <h2>Prévia do cartão</h2>
          <WeekRecipeCard recipe={preview} />
          <h2>Prévia da página</h2>
          {preview.image_url ? (
            <div className="week-recipe-hero">
              <img src={preview.image_url} alt={preview.image_alt || preview.title} />
            </div>
          ) : null}
          <p>{preview.title}</p>
          <p>{preview.summary}</p>
          {preview.ingredients.length ? (
            <ul>
              {preview.ingredients.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="admin-muted">Sem ingredientes ainda.</p>
          )}
          <div className="week-recipe-method">{preview.method_text || "Sem modo de preparo ainda."}</div>
        </div>
      ) : (
        <form onSubmit={(event) => void save(event)}>
          <div className="wre-layout">
            <div className="wre-main">
              <article className="wre-block">
                <h2>Apresentação</h2>
                <div className="wre-field">
                  <label htmlFor="wre-title">Título da receita</label>
                  <input id="wre-title" value={draft.title} maxLength={160} onChange={(event) => update("title", event.target.value)} />
                </div>
                <div className="wre-field">
                  <label htmlFor="wre-summary">Resumo para o destaque</label>
                  <textarea
                    id="wre-summary"
                    className="wre-summary"
                    rows={5}
                    value={draft.summary}
                    maxLength={280}
                    onChange={(event) => update("summary", event.target.value)}
                  />
                  <span className="wre-count">{draft.summary.length}/280</span>
                </div>
              </article>
              <article className="wre-block">
                <h2>Receita</h2>
                <div className="wre-field">
                  <label htmlFor="wre-ingredients">Ingredientes</label>
                  <p className="wre-hint" id="wre-ingredients-hint">
                    Um ingrediente por linha, com a quantidade
                  </p>
                  <textarea
                    id="wre-ingredients"
                    className="wre-ingredients"
                    rows={8}
                    aria-describedby="wre-ingredients-hint"
                    value={draft.ingredientsText}
                    onChange={(event) => update("ingredientsText", event.target.value)}
                  />
                </div>
                <div className="wre-field">
                  <label htmlFor="wre-method">Modo de preparo</label>
                  <p className="wre-hint" id="wre-method-hint">
                    Texto contínuo. Você pode numerar se quiser; o sistema não reparte em passos.
                  </p>
                  <textarea
                    id="wre-method"
                    className="wre-method"
                    rows={14}
                    aria-describedby="wre-method-hint"
                    value={draft.methodText}
                    onChange={(event) => update("methodText", event.target.value)}
                  />
                </div>
              </article>
              <article className="wre-block">
                <h2>Informações opcionais</h2>
                <div className="wre-pair">
                  <div className="wre-field">
                    <label htmlFor="wre-time">Tempo de preparo</label>
                    <input id="wre-time" value={draft.prep_time_text} maxLength={80} onChange={(event) => update("prep_time_text", event.target.value)} />
                  </div>
                  <div className="wre-field">
                    <label htmlFor="wre-yield">Rendimento</label>
                    <input id="wre-yield" value={draft.yield_text} maxLength={80} onChange={(event) => update("yield_text", event.target.value)} />
                  </div>
                </div>
                <details className="wre-frame" open={breadsOpen} onToggle={(event) => setBreadsOpen((event.target as HTMLDetailsElement).open)}>
                  <summary>Pães usados nesta receita (opcional)</summary>
                  <div className="wre-breads">
                    {(products?.items ?? []).map((product) => (
                      <label key={product.id} className="wre-bread">
                        <input
                          type="checkbox"
                          checked={draft.product_ids.includes(product.id)}
                          onChange={(event) => {
                            update(
                              "product_ids",
                              event.target.checked
                                ? [...draft.product_ids, product.id]
                                : draft.product_ids.filter((id) => id !== product.id),
                            );
                          }}
                        />
                        {product.name}
                      </label>
                    ))}
                  </div>
                </details>
              </article>
              <ActionBar className="wre-actions-end">{actions}</ActionBar>
            </div>
            <aside className="wre-photo wre-block">
              <h2>Foto de destaque</h2>
              <div className="wre-preview-frame">
                {photoUrl ? (
                  <img
                    src={photoUrl}
                    alt={draft.featured_image_alt || "Prévia da foto"}
                    style={{ objectPosition: `${draft.image_focus_x}% ${draft.image_focus_y}%` }}
                  />
                ) : (
                  <div className="wre-preview-empty">A foto preenche o cartão. Depois de escolher o arquivo, ajuste o enquadramento. Ela só substitui a imagem atual depois do envio bem-sucedido.</div>
                )}
              </div>
              {photoUrl ? (
                <fieldset className="wre-focus">
                  <legend>Ajustar enquadramento</legend>
                  <label>
                    Horizontal
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={draft.image_focus_x}
                      onChange={(event) => update("image_focus_x", Number(event.target.value))}
                    />
                  </label>
                  <label>
                    Vertical
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={draft.image_focus_y}
                      onChange={(event) => update("image_focus_y", Number(event.target.value))}
                    />
                  </label>
                  <p className="wre-hint">Arraste para escolher o que fica visível no cartão da home e na página da receita.</p>
                </fieldset>
              ) : null}
              <label className="wre-field">
                <span>{photoUrl ? "Substituir foto" : "Escolher foto"}</span>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    chooseFile(event.target.files?.[0]);
                    event.currentTarget.value = "";
                  }}
                />
              </label>
              <label className="wre-field">
                <span>Texto alternativo da foto</span>
                <input
                  value={draft.featured_image_alt}
                  maxLength={160}
                  onChange={(event) => update("featured_image_alt", event.target.value)}
                />
              </label>
              <label className="wre-field">
                <span>Legenda (opcional)</span>
                <input
                  value={draft.featured_image_caption}
                  maxLength={200}
                  onChange={(event) => update("featured_image_caption", event.target.value)}
                />
              </label>
            </aside>
          </div>
        </form>
      )}
    </section>
  );
}
