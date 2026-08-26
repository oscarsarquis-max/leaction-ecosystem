import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type {
  AllergenLine,
  CatalogItem,
  Completeness,
  CompositionLine,
  IngredientVersion,
  NutrientLine,
  SupplierItemCard,
} from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { IngredientAssistant } from "../components/IngredientAssistant";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

function versionTone(status: string): "sucesso" | "atencao" | "neutro" | "info" {
  if (status === "published") return "sucesso";
  if (status === "draft") return "atencao";
  if (status === "retired") return "neutro";
  return "info";
}

function versionLabel(status: string): string {
  if (status === "published") return "publicado";
  if (status === "draft") return "rascunho";
  if (status === "retired") return "aposentado";
  return status;
}

export function IngredientEditorPage() {
  const { ingredientId } = useParams();
  const isNew = !ingredientId;
  const { api, hasPermission, active } = useOrganization();
  const navigate = useNavigate();
  const command = useCommand();
  const [units, setUnits] = useState<CatalogItem[]>([]);
  const [nutrients, setNutrients] = useState<CatalogItem[]>([]);
  const [allergens, setAllergens] = useState<CatalogItem[]>([]);
  const [sources, setSources] = useState<CatalogItem[]>([]);
  const [candidates, setCandidates] = useState<Array<{ id: string; label: string }>>([]);
  const [error, setError] = useState<unknown>(null);
  const [dirty, setDirty] = useState(false);
  const [assistant, setAssistant] = useState<"open" | "min" | "off">("open");
  const [identity, setIdentity] = useState({
    code: "",
    display_name: "",
    ingredient_type: "simple",
    row_version: 1,
  });
  const [versions, setVersions] = useState<IngredientVersion[]>([]);
  const [version, setVersion] = useState<IngredientVersion | null>(null);
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [composition, setComposition] = useState<CompositionLine[]>([]);
  const [nutrientRows, setNutrientRows] = useState<NutrientLine[]>([]);
  const [allergenRows, setAllergenRows] = useState<AllergenLine[]>([]);
  const [items, setItems] = useState<SupplierItemCard[]>([]);
  const [notes, setNotes] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [componentVersionId, setComponentVersionId] = useState("");
  const [componentQty, setComponentQty] = useState("");
  const [nutrientId, setNutrientId] = useState("");
  const [nutrientValue, setNutrientValue] = useState("");
  const [nutrientStatus, setNutrientStatus] = useState("measured");
  const [loq, setLoq] = useState("");
  const [allergenId, setAllergenId] = useState("");
  const [presence, setPresence] = useState("contains");
  const [evidence, setEvidence] = useState("");
  const [loading, setLoading] = useState(!isNew);

  const reload = useCallback(async (id: string, preferredVersion?: string) => {
    const detail = await api.getIngredient(id);
    setIdentity({
      code: detail.data.code,
      display_name: detail.data.display_name,
      ingredient_type: detail.data.ingredient_type,
      row_version: detail.data.row_version,
    });
    setVersions(detail.data.versions);
    const current =
      detail.data.versions.find((item) => item.id === preferredVersion) ?? detail.data.versions[0];
    if (!current) return;
    const dossier = await api.getIngredientVersion(id, current.id);
    setVersion(dossier.data.version);
    setCompleteness(dossier.data.completeness);
    setComposition(dossier.data.composition);
    setNutrientRows(dossier.data.nutrients);
    setAllergenRows(dossier.data.allergens);
    setNotes(dossier.data.version.notes ?? "");
    setSourceId(dossier.data.version.data_source_id ?? "");
    try {
      const listed = await api.listIngredientItems(id);
      setItems(listed.data);
    } catch {
      setItems([]);
    }
  }, [api]);

  useEffect(() => {
    if (!active) return;
    void Promise.all([
      api.getCatalogUnits(),
      api.getCatalogNutrients(),
      api.getCatalogAllergens(),
      api.getCatalogSources(),
      api.listIngredients({ limit: "50" }),
    ]).then(([unitPage, nutrientPage, allergenPage, sourcePage, list]) => {
      setUnits(unitPage.data);
      setNutrients(nutrientPage.data);
      setAllergens(allergenPage.data);
      setSources(sourcePage.data);
      setCandidates(
        list.items
          .filter((item) => item.id !== ingredientId && item.current_version)
          .map((item) => ({
            id: item.current_version!.id,
            label: `${item.display_name} (${item.code})`,
          })),
      );
    }).catch(() => undefined);
  }, [api, active, ingredientId]);

  useEffect(() => {
    if (!ingredientId || !active) return;
    setLoading(true);
    reload(ingredientId)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [api, ingredientId, active, reload]);

  async function run(name: string, action: (key: string) => Promise<unknown>) {
    try {
      await command.run(name, action);
      setDirty(false);
      setError(null);
      if (ingredientId) await reload(ingredientId, version?.id);
    } catch (caught) {
      setError(caught);
    }
  }

  async function saveNew() {
    const unit = units[0];
    if (!unit) return;
    try {
      const result = await command.run("create", (key) =>
        api.catalogCommand<{ data: { id: string } }>("/ingredients", {
          body: {
            code: identity.code,
            display_name: identity.display_name,
            ingredient_type: identity.ingredient_type,
            nutrition_basis_unit_id: unit.id,
          },
          idempotencyKey: key,
        }),
      );
      if (result?.data.id) navigate(`/componentes/ingredientes/${result.data.id}`);
    } catch (caught) {
      setError(caught);
    }
  }

  const frozen = version?.status === "published";
  const canDraft = hasPermission("ingredient.update_draft") && !frozen;

  if (loading) return <LoadingState />;
  if (!isNew && error && !identity.code && !dirty) {
    return (
      <ErrorState
        error={error instanceof ApiError ? error : new Error("Falha no dossiê")}
        onRetry={() => {
          setError(null);
          if (ingredientId) void reload(ingredientId);
        }}
      />
    );
  }

  return (
    <>
      <div className="stage">
        <div>
          <h1>{isNew ? "Novo ingrediente" : identity.display_name || "Ingrediente"}</h1>
          <p className="lede">
            {version ? (
              <StatusBadge tone={versionTone(version.status)} label={versionLabel(version.status)} />
            ) : (
              <StatusBadge tone="atencao" label="rascunho" />
            )}{" "}
            {dirty ? "Há alterações não salvas." : "Dossiê sincronizado."}
          </p>
          {error instanceof ApiError ? (
            <p role="alert">
              {error.code === "conflito"
                ? "O estado mudou. Recarregue e tente de novo."
                : error.message}
            </p>
          ) : null}

          <form
            className="panel"
            onSubmit={(event) => {
              event.preventDefault();
              void (isNew
                ? saveNew()
                : run("identity", () =>
                    api.catalogCommand(`/ingredients/${ingredientId}`, {
                      method: "PATCH",
                      body: { display_name: identity.display_name, code: identity.code },
                      ifMatch: identity.row_version,
                    }),
                  ));
            }}
          >
            <h2>Identificação</h2>
            <label>
              Código
              <input
                value={identity.code}
                onChange={(event) => {
                  setIdentity({ ...identity, code: event.target.value });
                  setDirty(true);
                }}
                disabled={!isNew && frozen}
              />
            </label>
            <label>
              Nome
              <input
                value={identity.display_name}
                onChange={(event) => {
                  setIdentity({ ...identity, display_name: event.target.value });
                  setDirty(true);
                }}
                disabled={!isNew && !hasPermission("ingredient.update_draft")}
              />
            </label>
            <label>
              Tipo
              <select
                value={identity.ingredient_type}
                onChange={(event) => {
                  setIdentity({ ...identity, ingredient_type: event.target.value });
                  setDirty(true);
                }}
                disabled={!isNew}
              >
                <option value="simple">simples</option>
                <option value="composite">composto</option>
                <option value="preparation">preparação</option>
              </select>
            </label>
            {isNew && hasPermission("ingredient.create") ? (
              <button type="submit" className="primary">
                Criar rascunho
              </button>
            ) : null}
            {!isNew && hasPermission("ingredient.update_draft") ? (
              <button type="submit" className="primary">
                Guardar identidade
              </button>
            ) : null}
          </form>

          {version ? (
            <section className="panel">
              <h2>Histórico de versões</h2>
              <label>
                Versão visível
                <select
                  value={version.id}
                  onChange={(event) => {
                    if (ingredientId) void reload(ingredientId, event.target.value);
                  }}
                >
                  {versions.map((item) => (
                    <option key={item.id} value={item.id}>
                      v{item.version_number} · {versionLabel(item.status)}
                    </option>
                  ))}
                </select>
              </label>
              {frozen ? (
                <p>Versão publicada é imutável. Crie outra versão para editar.</p>
              ) : null}
              {frozen && hasPermission("ingredient.update_draft") ? (
                <button
                  type="button"
                  className="primary"
                  onClick={() =>
                    void run("new-version", (key) =>
                      api.catalogCommand(`/ingredients/${ingredientId}/versions`, {
                        body: {
                          source_version_id: version.id,
                          nutrition_basis_unit_id: version.nutrition_basis_unit_id,
                        },
                        idempotencyKey: key,
                      }),
                    )
                  }
                >
                  Criar nova versão
                </button>
              ) : null}
              {version.status === "published" && hasPermission("ingredient.retire") ? (
                <button
                  type="button"
                  onClick={() =>
                    void run("retire", (key) =>
                      api.catalogCommand(`/ingredients/${ingredientId}/versions/${version.id}/retire`, {
                        idempotencyKey: key,
                        ifMatch: version.row_version,
                      }),
                    )
                  }
                >
                  Aposentar versão
                </button>
              ) : null}
            </section>
          ) : null}

          {version ? (
            <section className="panel">
              <h2>Composição</h2>
              {composition.length === 0 ? <p>Nenhum constituinte neste recorte.</p> : null}
              <ul>
                {composition.map((line) => (
                  <li key={line.id}>
                    {line.component_type === "preparation" ? "preparação" : "constituinte"} ·{" "}
                    {line.quantity} · seq {line.sequence}
                    {canDraft ? (
                      <>
                        {" "}
                        <button
                          type="button"
                          onClick={() =>
                            void run("remove-line", () =>
                              api.catalogCommand(
                                `/ingredients/${ingredientId}/versions/${version.id}/composition/${line.id}`,
                                { method: "DELETE", ifMatch: version.row_version },
                              ),
                            )
                          }
                        >
                          Remover
                        </button>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
              {canDraft ? (
                <>
                  <label>
                    Constituinte ou preparação
                    <select
                      value={componentVersionId}
                      onChange={(event) => setComponentVersionId(event.target.value)}
                    >
                      <option value="">selecione</option>
                      {candidates.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Quantidade (massa)
                    <input
                      value={componentQty}
                      inputMode="decimal"
                      onChange={(event) => setComponentQty(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="primary"
                    onClick={() =>
                      void run("composition", () =>
                        api.catalogCommand(
                          `/ingredients/${ingredientId}/versions/${version.id}/composition`,
                          {
                            body: {
                              component_version_id: componentVersionId,
                              component_type: "constituent",
                              quantity: componentQty,
                              measurement_unit_id: units[0]?.id,
                              sequence: composition.length + 1,
                            },
                            ifMatch: version.row_version,
                          },
                        ),
                      )
                    }
                  >
                    Guardar linha
                  </button>
                </>
              ) : null}
            </section>
          ) : null}

          {version ? (
            <section className="panel">
              <h2>Nutrição por 100 g</h2>
              <p className="meta">Ausência não é zero. Abaixo do LQ permanece abaixo do LQ.</p>
              <ul>
                {nutrientRows.map((row) => (
                  <li key={row.id}>
                    {row.value_status}
                    {row.value ? ` · ${row.value}` : ""}
                    {row.value_status === "below_loq" ? ` · LQ ${row.limit_of_quantification}` : ""}
                  </li>
                ))}
              </ul>
              {canDraft ? (
                <>
                  <label>
                    Nutriente
                    <select value={nutrientId} onChange={(event) => setNutrientId(event.target.value)}>
                      <option value="">selecione</option>
                      {nutrients.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name ?? item.code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Estado
                    <select
                      value={nutrientStatus}
                      onChange={(event) => setNutrientStatus(event.target.value)}
                    >
                      <option value="measured">medido</option>
                      <option value="known_zero">zero conhecido</option>
                      <option value="below_loq">abaixo do LQ</option>
                      <option value="not_detected">não detectado</option>
                      <option value="unknown">desconhecido</option>
                    </select>
                  </label>
                  <label>
                    Valor
                    <input
                      value={nutrientValue}
                      inputMode="decimal"
                      onChange={(event) => setNutrientValue(event.target.value)}
                    />
                  </label>
                  {nutrientStatus === "below_loq" ? (
                    <label>
                      Limite de quantificação
                      <input value={loq} inputMode="decimal" onChange={(event) => setLoq(event.target.value)} />
                    </label>
                  ) : null}
                  <button
                    type="button"
                    className="primary"
                    onClick={() =>
                      void run("nutrient", () =>
                        api.catalogCommand(`/ingredients/${ingredientId}/versions/${version.id}/nutrients`, {
                          body: {
                            nutrient_id: nutrientId,
                            value: nutrientValue,
                            value_status: nutrientStatus,
                            limit_of_quantification: loq || null,
                            loq_unit_id: nutrientStatus === "below_loq" ? units[0]?.id : null,
                          },
                          ifMatch: version.row_version,
                        }),
                      )
                    }
                  >
                    Guardar nutriente
                  </button>
                </>
              ) : null}
            </section>
          ) : null}

          {version ? (
            <section className="panel">
              <h2>Alergênicos</h2>
              <ul>
                {allergenRows.map((row) => (
                  <li key={row.id}>
                    {row.presence}
                    {row.evidence_note ? ` · ${row.evidence_note}` : ""}
                  </li>
                ))}
              </ul>
              {canDraft ? (
                <>
                  <label>
                    Alergênico
                    <select value={allergenId} onChange={(event) => setAllergenId(event.target.value)}>
                      <option value="">selecione</option>
                      {allergens.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name ?? item.code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Presença
                    <select value={presence} onChange={(event) => setPresence(event.target.value)}>
                      <option value="contains">contém</option>
                      <option value="may_contain">pode conter / traços</option>
                      <option value="not_declared">ausência conhecida / não declarado</option>
                    </select>
                  </label>
                  <label>
                    Fonte ou justificativa
                    <input value={evidence} onChange={(event) => setEvidence(event.target.value)} />
                  </label>
                  <button
                    type="button"
                    className="primary"
                    onClick={() =>
                      void run("allergen", () =>
                        api.catalogCommand(`/ingredients/${ingredientId}/versions/${version.id}/allergens`, {
                          body: { allergen_id: allergenId, presence, evidence_note: evidence },
                          ifMatch: version.row_version,
                        }),
                      )
                    }
                  >
                    Guardar alergênico
                  </button>
                </>
              ) : null}
            </section>
          ) : null}

          {version ? (
            <section className="panel">
              <h2>Fontes e evidências</h2>
              <p className="meta">
                Catálogo global visível: {sources.length} fonte(s), somente leitura. Sem upload e sem
                consulta externa.
              </p>
              <label>
                Fonte da versão
                <select
                  value={sourceId}
                  disabled={!canDraft}
                  onChange={(event) => {
                    setSourceId(event.target.value);
                    setDirty(true);
                  }}
                >
                  <option value="">sem fonte</option>
                  {sources.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title ?? item.code}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Notas de revisão
                <textarea
                  value={notes}
                  disabled={!canDraft}
                  onChange={(event) => {
                    setNotes(event.target.value);
                    setDirty(true);
                  }}
                />
              </label>
              {canDraft ? (
                <button
                  type="button"
                  className="primary"
                  onClick={() =>
                    void run("draft", () =>
                      api.catalogCommand(`/ingredients/${ingredientId}/versions/${version.id}`, {
                        method: "PATCH",
                        body: { notes, data_source_id: sourceId || null },
                        ifMatch: version.row_version,
                      }),
                    )
                  }
                >
                  Guardar revisão
                </button>
              ) : null}
            </section>
          ) : null}

          {ingredientId ? (
            <section className="panel">
              <h2>Fornecedores e valores de compra</h2>
              {items.length === 0 ? <p>Nenhum item comercial vinculado.</p> : null}
              <ul>
                {items.map((item) => (
                  <li key={item.id}>
                    {item.supplier_sku} · {item.package_quantity}
                    {item.latest_purchase
                      ? ` · último valor ${item.latest_purchase.unit_price} ${item.latest_purchase.currency}`
                      : ""}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {version && hasPermission("ingredient.publish") && version.status === "draft" ? (
            <button
              type="button"
              className="primary"
              onClick={() =>
                void run("publish", (key) =>
                  api.catalogCommand(`/ingredients/${ingredientId}/versions/${version.id}/publish`, {
                    idempotencyKey: key,
                    ifMatch: version.row_version,
                  }),
                )
              }
            >
              Publicar versão
            </button>
          ) : null}

          <section className="panel">
            <h2>Auditoria</h2>
            <p className="meta">
              Organização soberana. Versão de linha {version?.row_version ?? identity.row_version}. Autor
              da versão: {version?.created_by_user_id ?? "ainda sem publicação"}.
            </p>
          </section>
        </div>
        <aside className="panel">
          <h2>Completude</h2>
          {completeness?.items.length ? (
            completeness.items.map((item) => (
              <p key={item.code}>
                <StatusBadge tone={item.blocking ? "erro" : "atencao"} label={item.label} />
                <span className="meta"> origem: {item.origin}</span>
              </p>
            ))
          ) : (
            <p>
              <StatusBadge tone="sucesso" label="dossiê completo" />
            </p>
          )}
        </aside>
      </div>
      {assistant !== "off" ? (
        <IngredientAssistant
          completeness={completeness}
          minimized={assistant === "min"}
          onMinimize={() => setAssistant(assistant === "min" ? "open" : "min")}
          onDismiss={() => setAssistant("off")}
        />
      ) : (
        <p className="meta">
          <button type="button" className="ghost" onClick={() => setAssistant("open")}>
            Retomar assistente
          </button>
        </p>
      )}
    </>
  );
}
