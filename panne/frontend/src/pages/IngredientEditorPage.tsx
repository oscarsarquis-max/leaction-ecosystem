import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ApiError, isCancelledError } from "../api/errors";
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
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import {
  allergenPresenceLabel,
  formatAllergenLine,
  formatMoneyAmount,
  formatNutrientLine,
  formatPackageQuantity,
  globalSourcesSummary,
  ingredientStatusTone,
  ingredientTypeLabel,
  ingredientVersionLabel,
  nutrientStatusLabel,
} from "../language/ingredients";
import { useCommand } from "../ops/useCommand";
import { safeReturnTo } from "../navigation/returnTo";
import { useOrganization } from "../session/OrganizationContext";

function clearDossierState(setters: {
  setIdentity: (v: {
    code: string;
    display_name: string;
    ingredient_type: string;
    row_version: number;
  }) => void;
  setVersions: (v: IngredientVersion[]) => void;
  setVersion: (v: IngredientVersion | null) => void;
  setCompleteness: (v: Completeness | null) => void;
  setComposition: (v: CompositionLine[]) => void;
  setNutrientRows: (v: NutrientLine[]) => void;
  setAllergenRows: (v: AllergenLine[]) => void;
  setItems: (v: SupplierItemCard[]) => void;
  setNotes: (v: string) => void;
  setSourceId: (v: string) => void;
}) {
  setters.setIdentity({ code: "", display_name: "", ingredient_type: "simple", row_version: 1 });
  setters.setVersions([]);
  setters.setVersion(null);
  setters.setCompleteness(null);
  setters.setComposition([]);
  setters.setNutrientRows([]);
  setters.setAllergenRows([]);
  setters.setItems([]);
  setters.setNotes("");
  setters.setSourceId("");
}

export function IngredientEditorPage() {
  const { ingredientId } = useParams();
  const isNew = !ingredientId;
  const [returnParams] = useSearchParams();
  const productReturn = safeReturnTo(returnParams.get("from"), "");
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
  const loadGeneration = useRef(0);
  const showPurchasePrice =
    hasPermission("supplier.price.record") ||
    hasPermission("costing.read") ||
    hasPermission("procurement.order.manage");

  const reload = useCallback(
    async (id: string, preferredVersion?: string, token?: number) => {
      const detail = await api.getIngredient(id);
      if (token != null && loadGeneration.current !== token) return;
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
      if (token != null && loadGeneration.current !== token) return;
      setVersion(dossier.data.version);
      setCompleteness(dossier.data.completeness);
      setComposition(dossier.data.composition);
      setNutrientRows(dossier.data.nutrients);
      setAllergenRows(dossier.data.allergens);
      setNotes(dossier.data.version.notes ?? "");
      setSourceId(dossier.data.version.data_source_id ?? "");
      try {
        const listed = await api.listIngredientItems(id);
        if (token != null && loadGeneration.current !== token) return;
        setItems(listed.data);
      } catch (caught) {
        if (isCancelledError(caught)) return;
        if (token != null && loadGeneration.current !== token) return;
        setItems([]);
      }
    },
    [api],
  );

  useEffect(() => {
    if (!active?.organization_id) return;
    setCandidates([]);
    void Promise.all([
      api.getCatalogUnits(),
      api.getCatalogNutrients(),
      api.getCatalogAllergens(),
      api.getCatalogSources(),
      api.listIngredients({ limit: "50" }),
    ])
      .then(([unitPage, nutrientPage, allergenPage, sourcePage, list]) => {
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
      })
      .catch((caught) => {
        if (isCancelledError(caught)) return;
      });
  }, [api, active?.organization_id, ingredientId]);

  useEffect(() => {
    if (!ingredientId || !active?.organization_id) return;
    const token = ++loadGeneration.current;
    setLoading(true);
    setError(null);
    clearDossierState({
      setIdentity,
      setVersions,
      setVersion,
      setCompleteness,
      setComposition,
      setNutrientRows,
      setAllergenRows,
      setItems,
      setNotes,
      setSourceId,
    });
    reload(ingredientId, undefined, token)
      .then(() => {
        if (loadGeneration.current === token) setLoading(false);
      })
      .catch((caught) => {
        if (loadGeneration.current !== token) return;
        if (isCancelledError(caught)) return;
        setError(caught);
        setLoading(false);
      });
  }, [api, ingredientId, active?.organization_id, reload]);

  async function run(name: string, action: (key: string) => Promise<unknown>) {
    try {
      await command.run(name, action);
      setDirty(false);
      setError(null);
      if (ingredientId) {
        const token = ++loadGeneration.current;
        await reload(ingredientId, version?.id, token);
      }
    } catch (caught) {
      if (isCancelledError(caught)) return;
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
      if (isCancelledError(caught)) return;
      setError(caught);
    }
  }

  const frozen = version?.status === "published";
  const canDraft = hasPermission("ingredient.update_draft") && !frozen;
  const presentableError = error && !isCancelledError(error) ? error : null;

  if (loading) return <LoadingState />;
  if (!isNew && presentableError && !identity.code && !dirty) {
    return (
      <ErrorState
        error={presentableError instanceof ApiError ? presentableError : new Error("Falha no dossiê")}
        onRetry={() => {
          setError(null);
          if (ingredientId) {
            const token = ++loadGeneration.current;
            setLoading(true);
            reload(ingredientId, undefined, token)
              .then(() => {
                if (loadGeneration.current === token) setLoading(false);
              })
              .catch((caught) => {
                if (loadGeneration.current !== token) return;
                if (isCancelledError(caught)) return;
                setError(caught);
                setLoading(false);
              });
          }
        }}
      />
    );
  }

  return (
    <>
      <div className="stage">
        <div>
          <h1>{isNew ? "Novo ingrediente" : identity.display_name || "Ingrediente"}</h1>
          {productReturn.startsWith("/produtos/") ? (
            <p>
              <Link to={productReturn}>Voltar ao produto</Link>
            </p>
          ) : null}
          <p className="lede">
            {version ? (
              <StatusBadge
                tone={ingredientStatusTone(version.status)}
                label={ingredientVersionLabel(version.status)}
              />
            ) : (
              <StatusBadge tone="atencao" label="Rascunho" />
            )}{" "}
            {dirty ? "Há alterações não salvas." : "Dossiê sincronizado."}
          </p>
          {presentableError instanceof ApiError ? (
            <p role="alert">
              {presentableError.code === "conflito"
                ? "O estado mudou. Recarregue e tente de novo."
                : presentableError.message}
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
                <option value="simple">{ingredientTypeLabel("simple")}</option>
                <option value="composite">{ingredientTypeLabel("composite")}</option>
                <option value="preparation">{ingredientTypeLabel("preparation")}</option>
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
                    if (!ingredientId) return;
                    const token = ++loadGeneration.current;
                    setLoading(true);
                    setError(null);
                    reload(ingredientId, event.target.value, token)
                      .then(() => {
                        if (loadGeneration.current === token) setLoading(false);
                      })
                      .catch((caught) => {
                        if (loadGeneration.current !== token) return;
                        if (isCancelledError(caught)) return;
                        setError(caught);
                        setLoading(false);
                      });
                  }}
                >
                  {versions.map((item) => (
                    <option key={item.id} value={item.id}>
                      v{item.version_number} · {ingredientVersionLabel(item.status)}
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
                    {line.component_type === "preparation" ? "Preparação" : "Constituinte"} ·{" "}
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
                      <option value="">Selecione</option>
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
                  <li key={row.id}>{formatNutrientLine(row)}</li>
                ))}
              </ul>
              {canDraft ? (
                <>
                  <label>
                    Nutriente
                    <select value={nutrientId} onChange={(event) => setNutrientId(event.target.value)}>
                      <option value="">Selecione</option>
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
                      <option value="measured">{nutrientStatusLabel("measured")}</option>
                      <option value="known_zero">{nutrientStatusLabel("known_zero")}</option>
                      <option value="below_loq">{nutrientStatusLabel("below_loq")}</option>
                      <option value="not_detected">{nutrientStatusLabel("not_detected")}</option>
                      <option value="unknown">{nutrientStatusLabel("unknown")}</option>
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
                  <li key={row.id}>{formatAllergenLine(row)}</li>
                ))}
              </ul>
              {canDraft ? (
                <>
                  <label>
                    Alergênico
                    <select value={allergenId} onChange={(event) => setAllergenId(event.target.value)}>
                      <option value="">Selecione</option>
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
                      <option value="contains">{allergenPresenceLabel("contains")}</option>
                      <option value="may_contain">{allergenPresenceLabel("may_contain")}</option>
                      <option value="not_declared">{allergenPresenceLabel("not_declared")}</option>
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
                {globalSourcesSummary(sources.length)}, somente leitura. Sem upload e sem consulta
                externa.
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
                  <option value="">Sem fonte</option>
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
                    <div>{item.supplier_sku}</div>
                    <div className="meta">
                      Embalagem: {formatPackageQuantity(item.package_quantity, item.unit)}
                      {item.supplier?.display_name ? ` · ${item.supplier.display_name}` : ""}
                    </div>
                    {showPurchasePrice && item.latest_purchase ? (
                      <div className="meta">
                        Último valor:{" "}
                        {formatMoneyAmount(
                          item.latest_purchase.unit_price,
                          item.latest_purchase.currency,
                        )}
                      </div>
                    ) : null}
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
              Organização soberana. Autor da versão:{" "}
              {version?.created_by_user_id ? "registrado (ver detalhes técnicos)" : "ainda sem publicação"}.
            </p>
            <TechnicalAuditDetails
              rows={[
                {
                  label: "Versão de linha",
                  value: String(version?.row_version ?? identity.row_version),
                },
                {
                  label: "Identificador do autor",
                  value: version?.created_by_user_id ?? "—",
                  copyable: Boolean(version?.created_by_user_id),
                },
                ...(completeness?.items ?? []).map((item) => ({
                  label: `Origem · ${item.code}`,
                  value: item.origin,
                })),
                ...nutrientRows.map((row) => ({
                  label: `Nutriente · ${row.nutrient?.code ?? row.nutrient_id}`,
                  value: row.nutrient_id,
                  copyable: true as const,
                })),
                ...allergenRows.map((row) => ({
                  label: `Alergênico · ${row.allergen?.code ?? row.allergen_id}`,
                  value: row.allergen_id,
                  copyable: true as const,
                })),
                ...items.flatMap((item) => {
                  const rows: Array<{ label: string; value: string; copyable?: boolean }> = [
                    { label: `SKU · ${item.supplier_sku}`, value: item.id, copyable: true },
                  ];
                  if (showPurchasePrice && item.latest_purchase) {
                    rows.push({
                      label: `Moeda ISO · ${item.supplier_sku}`,
                      value: item.latest_purchase.currency,
                      copyable: false,
                    });
                  }
                  return rows;
                }),
              ]}
            />
          </section>
        </div>
        <aside className="panel">
          <h2>Completude</h2>
          {completeness?.items.length ? (
            completeness.items.map((item) => (
              <p key={item.code}>
                <StatusBadge tone={item.blocking ? "erro" : "atencao"} label={item.label} />
              </p>
            ))
          ) : (
            <p>
              <StatusBadge tone="sucesso" label="Dossiê completo" />
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
