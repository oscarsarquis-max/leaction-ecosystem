import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type {
  ApprovalRow,
  Completeness,
  NutritionPreview,
  RecipeItem,
  RecipeStep,
  RecipeVersion,
  ScaleRow,
  TrialRow,
} from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { RecipeAssistant } from "../components/RecipeAssistant";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatOperationalQuantity } from "../language/quantities";
import {
  formatBakersPercentage,
  formatScaleFactor,
  formatYieldSummary,
  ingredientLineLabel,
  recipeApprovalLabel,
  recipeStatusTone,
  recipeTrialLabel,
  recipeVersionLabel,
  unitDisplayCode,
} from "../language/recipes";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeEditorPage() {
  const { recipeId } = useParams();
  const isNew = !recipeId;
  const { api, hasPermission, active } = useOrganization();
  const navigate = useNavigate();
  const command = useCommand();
  const [error, setError] = useState<unknown>(null);
  const [assistant, setAssistant] = useState<"open" | "min" | "off">("open");
  const [identity, setIdentity] = useState({ code: "", display_name: "", row_version: 1 });
  const [versions, setVersions] = useState<RecipeVersion[]>([]);
  const [version, setVersion] = useState<RecipeVersion | null>(null);
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [items, setItems] = useState<RecipeItem[]>([]);
  const [steps, setSteps] = useState<RecipeStep[]>([]);
  const [flourMass, setFlourMass] = useState<string | null>(null);
  const [flourAbsence, setFlourAbsence] = useState(false);
  const [approvals, setApprovals] = useState<ApprovalRow[]>([]);
  const [trials, setTrials] = useState<TrialRow[]>([]);
  const [nutrition, setNutrition] = useState<NutritionPreview | null>(null);
  const [scales, setScales] = useState<ScaleRow[]>([]);
  const [ingredientVersionId, setIngredientVersionId] = useState("");
  const [netQuantity, setNetQuantity] = useState("");
  const [isFlour, setIsFlour] = useState(false);
  const [stepTitle, setStepTitle] = useState("");
  const [stepInstructions, setStepInstructions] = useState("");
  const [yieldUnits, setYieldUnits] = useState("");
  const [unitWeight, setUnitWeight] = useState("");
  const [loss, setLoss] = useState("");
  const [scaleMass, setScaleMass] = useState("");
  const [trialCode, setTrialCode] = useState("");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [refTitle, setRefTitle] = useState("");
  const [loading, setLoading] = useState(!isNew);

  const canEdit = hasPermission("recipe.update_draft") && version?.status === "draft";

  const reload = useCallback(
    async (id: string, preferredVersion?: string) => {
      const detail = await api.getRecipe(id);
      setIdentity({
        code: detail.data.code,
        display_name: detail.data.display_name,
        row_version: detail.data.row_version,
      });
      setVersions(detail.data.versions);
      const current =
        detail.data.versions.find((item) => item.id === preferredVersion) ?? detail.data.versions[0];
      if (!current) return;
      const dossier = await api.getRecipeVersion(id, current.id);
      setVersion(dossier.data.version);
      setCompleteness(dossier.data.completeness);
      setItems(dossier.data.items);
      setSteps(dossier.data.steps);
      setFlourMass(dossier.data.bakers.flour_mass);
      setFlourAbsence(dossier.data.bakers.explained_absence);
      setYieldUnits(dossier.data.yield.yield_units ? String(dossier.data.yield.yield_units) : "");
      setUnitWeight(dossier.data.yield.target_unit_weight_g ?? "");
      setLoss(dossier.data.yield.expected_bake_loss_rate ?? "");
      const [trialPage, nutritionPage, approvalPage, scalePage] = await Promise.all([
        api.getRecipeTrials(id, current.id).catch(() => ({ data: [] })),
        api.getRecipeNutrition(id, current.id).catch(() => ({ data: null })),
        api.getRecipeApprovals(id, current.id).catch(() => ({ data: [] })),
        api.getRecipeScales(id, current.id).catch(() => ({ data: [] })),
      ]);
      setTrials(Array.isArray(trialPage.data) ? trialPage.data : []);
      setNutrition(nutritionPage.data ?? null);
      setApprovals(Array.isArray(approvalPage.data) ? approvalPage.data : []);
      setScales(Array.isArray(scalePage.data) ? scalePage.data : []);
    },
    [api],
  );

  useEffect(() => {
    if (!active?.organization_id || isNew) return;
    let alive = true;
    setLoading(true);
    setError(null);
    setIdentity({ code: "", display_name: "", row_version: 1 });
    setVersions([]);
    setVersion(null);
    setItems([]);
    setSteps([]);
    setTrials([]);
    setScales([]);
    setApprovals([]);
    setNutrition(null);
    setCompleteness(null);
    setFlourMass(null);
    reload(recipeId)
      .catch((err) => {
        if (alive) setError(err);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [active?.organization_id, isNew, recipeId, reload]);

  async function createRecipe(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const created = await command.run("create", (key) =>
        api.catalogCommand<{ data: { id: string } }>("/recipes", {
          body: {
            code: String(data.get("code") ?? ""),
            display_name: String(data.get("display_name") ?? ""),
          },
          idempotencyKey: key,
        }),
      );
      if (created?.data.id) navigate(`/receitas/${created.data.id}`);
    } catch (err) {
      setError(err);
    }
  }

  async function run(name: string, action: (key: string) => Promise<unknown>) {
    try {
      await command.run(name, action);
      setError(null);
      if (recipeId) await reload(recipeId, version?.id);
    } catch (err) {
      setError(err);
    }
  }

  if (isNew) {
    return (
      <div className="stage">
        <div>
          <h1>Nova receita</h1>
          <p className="lede">Cria produto técnico, formulação e primeira versão em rascunho.</p>
          {error ? <ErrorState error={error instanceof ApiError ? error : new Error("Falha")} /> : null}
          <form onSubmit={(event) => void createRecipe(event)}>
            <label>
              Código
              <input name="code" required />
            </label>
            <label>
              Nome
              <input name="display_name" required />
            </label>
            <button type="submit" className="primary">
              Criar rascunho
            </button>
          </form>
        </div>
        <aside className="panel">
          <RecipeAssistant completeness={null} minimized={false} onMinimize={() => undefined} onDismiss={() => undefined} />
        </aside>
      </div>
    );
  }

  if (loading) return <LoadingState />;
  if (error && !version) {
    return <ErrorState error={error instanceof ApiError ? error : new Error("Falha ao carregar")} />;
  }

  const latestDecision = approvals[0]?.decision;
  const pendingTrial = trials.find((item) => item.status === "planned" || item.status === "in_progress");

  return (
    <div className="stage">
      <div>
        <h1>{identity.display_name}</h1>
        <p className="lede">
          {identity.code}{" "}
          {version ? (
            <StatusBadge tone={recipeStatusTone(version.status)} label={recipeVersionLabel(version.status)} />
          ) : null}{" "}
          {latestDecision ? (
            <StatusBadge tone={recipeStatusTone(latestDecision)} label={recipeApprovalLabel(latestDecision)} />
          ) : null}{" "}
          {pendingTrial ? (
            <StatusBadge tone="atencao" label={recipeTrialLabel(pendingTrial.status)} />
          ) : trials.some((item) => item.status === "completed") ? (
            <StatusBadge tone="sucesso" label="Ensaio concluído" />
          ) : null}{" "}
          {nutrition == null ? <StatusBadge tone="atencao" label="Nutrição incompleta" /> : null}{" "}
          {completeness?.ready_to_publish ? (
            <StatusBadge tone="sucesso" label="Pronta para publicar" />
          ) : (
            <StatusBadge tone="info" label="Prontidão incompleta" />
          )}
        </p>
        {error ? <ErrorState error={error instanceof ApiError ? error : new Error("Falha")} /> : null}

        <section>
          <h2>Componentes</h2>
          <p>Bruto e percentual vêm do servidor. Sem conversão massa-volume.</p>
          <table>
            <thead>
              <tr>
                <th>Seq.</th>
                <th>Ingrediente</th>
                <th>Líquido</th>
                <th>Bruto</th>
                <th>% padeiro</th>
                <th>Farinha-base</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const unit = unitDisplayCode(item.unit);
                return (
                  <tr key={item.id}>
                    <td>{item.sequence}</td>
                    <td>{ingredientLineLabel(item)}</td>
                    <td>{formatOperationalQuantity(item.net_quantity, unit)}</td>
                    <td>{formatOperationalQuantity(item.gross_quantity, unit)}</td>
                    <td>{formatBakersPercentage(item.bakers_percentage)}</td>
                    <td>{item.is_flour_basis ? "Sim" : "Não"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <TechnicalAuditDetails
            title="Identificadores dos componentes"
            purpose="IDs internos das versões de ingrediente desta receita."
            rows={items.map((item) => ({
              label: ingredientLineLabel(item),
              value: item.ingredient_version_id,
              copyable: true,
            }))}
          />
          {canEdit ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (!version || !recipeId) return;
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/items`, {
                    body: {
                      ingredient_version_id: ingredientVersionId,
                      sequence: items.length + 1,
                      net_quantity: netQuantity,
                      measurement_unit_id: "u1",
                      is_flour_basis: isFlour,
                      role: "ingredient",
                    },
                    ifMatch: version.row_version,
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Versão do ingrediente
                <input value={ingredientVersionId} onChange={(event) => setIngredientVersionId(event.target.value)} />
              </label>
              <label>
                Quantidade líquida
                <input value={netQuantity} onChange={(event) => setNetQuantity(event.target.value)} />
              </label>
              <label>
                <input type="checkbox" checked={isFlour} onChange={(event) => setIsFlour(event.target.checked)} />
                Farinha-base explícita
              </label>
              <button type="submit" className="primary">
                Incluir componente
              </button>
            </form>
          ) : null}
        </section>

        <section>
          <h2>Percentual do padeiro</h2>
          <p>Total de farinha: {flourMass ? formatOperationalQuantity(flourMass, "g") : "ausente"}.</p>
          {flourAbsence ? (
            <p>Sem farinha-base marcada: o percentual do padeiro não se aplica. Isso é válido e precisa ser explicado.</p>
          ) : (
            <p>A soma dos componentes não precisa resultar em 100%.</p>
          )}
        </section>

        <section>
          <h2>Processo</h2>
          <ol>
            {steps.map((step) => (
              <li key={step.id}>
                <strong>{step.title}</strong> — {step.instructions}
              </li>
            ))}
          </ol>
          {canEdit ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (!version || !recipeId) return;
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/steps`, {
                    body: {
                      sequence: steps.length + 1,
                      title: stepTitle,
                      instructions: stepInstructions,
                    },
                    ifMatch: version.row_version,
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Título
                <input value={stepTitle} onChange={(event) => setStepTitle(event.target.value)} />
              </label>
              <label>
                Instrução
                <textarea value={stepInstructions} onChange={(event) => setStepInstructions(event.target.value)} />
              </label>
              <button type="submit" className="primary">
                Incluir etapa
              </button>
            </form>
          ) : null}
        </section>

        <section>
          <h2>Rendimento e porção</h2>
          {canEdit ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (!version || !recipeId) return;
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}`, {
                    method: "PATCH",
                    body: {
                      yield_units: yieldUnits ? Number(yieldUnits) : undefined,
                      target_unit_weight_g: unitWeight || undefined,
                      expected_bake_loss_rate: loss || undefined,
                    },
                    ifMatch: version.row_version,
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Unidades esperadas
                <input value={yieldUnits} onChange={(event) => setYieldUnits(event.target.value)} />
              </label>
              <label>
                Peso final por unidade (g)
                <input value={unitWeight} onChange={(event) => setUnitWeight(event.target.value)} />
              </label>
              <label>
                Perda prevista (taxa 0–1)
                <input value={loss} onChange={(event) => setLoss(event.target.value)} />
              </label>
              <button type="submit" className="primary">
                Guardar rendimento
              </button>
            </form>
          ) : (
            <p>
              {formatYieldSummary({
                yieldUnits,
                unitWeightG: unitWeight || null,
                lossRate: loss || null,
              })}
            </p>
          )}
        </section>

        <section>
          <h2>Escala</h2>
          <p className="meta">
            O fator multiplica a receita-base para atingir a massa total informada. A massa-base é a soma líquida
            dos componentes da versão.
          </p>
          {scales.length === 0 ? <p>Nenhuma escala gravada nesta versão.</p> : null}
          {scales.map((row) => {
            const places =
              typeof row.presentation_decimal_places === "number"
                ? row.presentation_decimal_places
                : 4;
            return (
              <p key={row.id ?? `${row.scale_factor}-${row.base_total_net_mass}`}>
                Fator de escala: {formatScaleFactor(row.scale_factor, Math.max(places, 4))} · Massa-base da
                receita: {formatOperationalQuantity(row.base_total_net_mass, "g")}
                {row.input_target_total_dough_mass
                  ? ` · Massa total alvo: ${formatOperationalQuantity(row.input_target_total_dough_mass, "g")}`
                  : ""}
              </p>
            );
          })}
          {hasPermission("recipe.scale") && version ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/scale`, {
                    body: { mode: "total_dough_mass", target_total_dough_mass: scaleMass },
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Massa total (g)
                <input
                  value={scaleMass}
                  onChange={(event) => setScaleMass(event.target.value)}
                  inputMode="decimal"
                  placeholder="Ex.: 3300"
                />
              </label>
              <button type="submit" className="primary">
                Gravar escala
              </button>
            </form>
          ) : null}
        </section>

        <section>
          <h2>Ensaios</h2>
          <p>Ensaio não é ordem de produção.</p>
          {trials.map((trial) => (
            <p key={trial.id}>
              {trial.code}{" "}
              <StatusBadge tone={recipeStatusTone(trial.status)} label={recipeTrialLabel(trial.status)} />
            </p>
          ))}
          {hasPermission("recipe.trial.manage") && version ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/trials`, {
                    body: { code: trialCode },
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Código do ensaio
                <input value={trialCode} onChange={(event) => setTrialCode(event.target.value)} />
              </label>
              <button type="submit" className="primary">
                Planejar ensaio
              </button>
            </form>
          ) : null}
        </section>

        <section>
          <h2>Nutrição técnica</h2>
          <p className="sheet-warning">Prévia técnica incompleta e não validada regulatoriamente.</p>
          {nutrition ? <p>Situação do cálculo: {nutrition.status}</p> : <p>Prévia ainda não calculada.</p>}
          {hasPermission("recipe.scale") && version ? (
            <button
              type="button"
              className="primary"
              onClick={() =>
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/nutrition`, {
                    idempotencyKey: key,
                  }),
                )
              }
            >
              Calcular prévia
            </button>
          ) : null}
        </section>

        <section>
          <h2>Referências</h2>
          {hasPermission("recipe.reference.manage") ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void run("acao", (key) =>
                  api.catalogCommand("/recipe-references", {
                    body: { title: refTitle, source_type: "internal" },
                    idempotencyKey: key,
                  }),
                );
              }}
            >
              <label>
                Título da referência
                <input value={refTitle} onChange={(event) => setRefTitle(event.target.value)} />
              </label>
              <button type="submit" className="primary">
                Registrar referência
              </button>
            </form>
          ) : (
            <p>Somente leitura das referências visíveis.</p>
          )}
        </section>

        <section>
          <h2>Revisão e aprovação</h2>
          {approvals.map((row) => (
            <p key={row.id}>
              <StatusBadge tone={recipeStatusTone(row.decision)} label={recipeApprovalLabel(row.decision)} /> {row.notes}
            </p>
          ))}
          <label>
            Comentário
            <textarea value={decisionNotes} onChange={(event) => setDecisionNotes(event.target.value)} />
          </label>
          {hasPermission("recipe.review") && version ? (
            <button
              type="button"
              onClick={() =>
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/approvals`, {
                    body: { decision: "submitted", notes: decisionNotes },
                    idempotencyKey: key,
                  }),
                )
              }
            >
              Enviar para revisão
            </button>
          ) : null}{" "}
          {hasPermission("recipe.approve") && version ? (
            <>
              <button
                type="button"
                className="primary"
                onClick={() =>
                  void run("acao", (key) =>
                    api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/approvals`, {
                      body: { decision: "approved", notes: decisionNotes },
                      idempotencyKey: key,
                    }),
                  )
                }
              >
                Aprovar
              </button>
              <button
                type="button"
                onClick={() =>
                  void run("acao", (key) =>
                    api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/approvals`, {
                      body: { decision: "rejected", notes: decisionNotes },
                      idempotencyKey: key,
                    }),
                  )
                }
              >
                Rejeitar
              </button>
            </>
          ) : null}
        </section>

        <section>
          <h2>Histórico</h2>
          <ol>
            {versions.map((item) => (
              <li key={item.id}>
                v{item.version_number}{" "}
                <StatusBadge tone={recipeStatusTone(item.status)} label={recipeVersionLabel(item.status)} />
              </li>
            ))}
          </ol>
          {hasPermission("recipe.version.create") && version ? (
            <button
              type="button"
              onClick={() =>
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions`, {
                    body: { source_version_id: version.id },
                    idempotencyKey: key,
                  }),
                )
              }
            >
              Criar nova versão
            </button>
          ) : null}{" "}
          {hasPermission("recipe.publish") && version?.status === "draft" ? (
            <button
              type="button"
              className="primary"
              onClick={() =>
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/publish`, {
                    idempotencyKey: key,
                    ifMatch: version.row_version,
                  }),
                )
              }
            >
              Publicar versão
            </button>
          ) : null}{" "}
          {hasPermission("recipe.retire") && version?.status === "published" ? (
            <button
              type="button"
              onClick={() =>
                void run("acao", (key) =>
                  api.catalogCommand(`/recipes/${recipeId}/versions/${version.id}/retire`, {
                    idempotencyKey: key,
                    ifMatch: version.row_version,
                  }),
                )
              }
            >
              Aposentar
            </button>
          ) : null}{" "}
          {hasPermission("recipe.technical_sheet.read") && version ? (
            <Link className="primary" to={`/receitas/${recipeId}/versoes/${version.id}/ficha`}>
              Ver ficha técnica
            </Link>
          ) : null}
        </section>
      </div>
      {assistant === "off" ? null : (
        <aside className="panel">
          <RecipeAssistant
            completeness={completeness}
            minimized={assistant === "min"}
            onMinimize={() => setAssistant((value) => (value === "min" ? "open" : "min"))}
            onDismiss={() => setAssistant("off")}
          />
        </aside>
      )}
    </div>
  );
}
