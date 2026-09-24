import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { IngredientCard } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

type Place = { id: string; display_name: string };

function humanError(error: unknown): string {
  if (error instanceof ApiError && error.code === "conflito") {
    return "O estado do estoque mudou. Atualize e confirme de novo.";
  }
  if (error instanceof Error && error.message) return error.message;
  return "Não foi possível registrar a abertura.";
}

export function OpeningBalancePage() {
  const { api, active, hasPermission } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();
  const [ingredientId, setIngredientId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [occurredOn, setOccurredOn] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitCode, setUnitCode] = useState("un");
  const [lotCode, setLotCode] = useState("");
  const [origin, setOrigin] = useState("");
  const [costMode, setCostMode] = useState<"known" | "unknown" | "">("");
  const [unitCost, setUnitCost] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const ingredients = useAsyncResource(
    () => api.listIngredients({ limit: "50", offset: "0" }),
    [api, orgId],
    Boolean(orgId),
  );
  const locations = useAsyncResource(
    () => api.listInventory<Place>("/inventory/locations"),
    [api, orgId],
    Boolean(orgId),
  );

  const canAdjust = hasPermission("inventory.adjust");
  const destination = ingredients.state.kind === "ok"
    ? ingredients.state.data.items.find((row: IngredientCard) => row.id === ingredientId)
    : undefined;
  const place = locations.state.kind === "ok" ? locations.state.data.items.find((row) => row.id === locationId) : undefined;

  function validate(): string | null {
    if (!ingredientId) return "Escolha o ingrediente deste saldo.";
    if (!locationId) return "Escolha o lugar onde o saldo está.";
    if (!quantity.trim()) return "Informe a quantidade encontrada.";
    if (!unitCode.trim()) return "Informe a unidade desta quantidade.";
    if (!origin.trim()) return "Diga a origem ou o motivo desta abertura.";
    if (!costMode) return "Informe o custo unitário ou declare que o custo é desconhecido.";
    if (costMode === "known" && !unitCost.trim()) return "Informe o custo unitário desta abertura.";
    if (!reviewed) return "Revise os dados e marque que confirma esta abertura.";
    return null;
  }

  useEffect(() => {
    if (fieldError === null) return;
    const next = validate();
    if (next !== fieldError) setFieldError(next);
  }, [ingredientId, locationId, quantity, unitCode, origin, costMode, unitCost, reviewed, fieldError]);

  async function confirm() {
    const gap = validate();
    setFieldError(gap);
    if (gap || command.pending) return;
    try {
      await command.run(`opening:${ingredientId}:${locationId}:${quantity}:${unitCode}:${lotCode}:${origin}`, (key) =>
        api.openInventoryBalance(
          {
            ingredient_id: ingredientId,
            inventory_location_id: locationId,
            quantity: quantity.trim(),
            unit_code: unitCode,
            occurred_on: occurredOn || null,
            internal_lot_code: lotCode.trim() || null,
            origin: origin.trim(),
            reason: origin.trim(),
            unit_cost: costMode === "known" ? unitCost.trim() : null,
            cost_unknown: costMode === "unknown",
            confirmed: true,
          },
          key,
        ),
      );
      setSuccess(
        costMode === "unknown"
          ? "Abertura registrada com custo desconhecido. Custo e margem deste lote ficam incompletos."
          : "Abertura registrada com o custo informado. Isso não cria nota fiscal nem fornecedor.",
      );
    } catch {
      /* command.error */
    }
  }

  if (ingredients.state.kind === "carregando" && locations.state.kind === "carregando") {
    return <LoadingState />;
  }

  return (
    <div className="manual-path">
      <header className="manual-heading">
        <div>
          <p className="manual-kicker">Organização · {active?.display_name || "atual"}</p>
          <h1>Abrir saldo sem nota</h1>
          <p>
            Use quando o estoque físico já existe e não há documento fiscal. Nada é inventado: só entram valores que
            você confirma.
          </p>
        </div>
        <Link className="manual-quiet" to="/componentes/estoque">
          Voltar ao estoque
        </Link>
      </header>

      {ingredients.state.kind === "erro" ? <ErrorState error={ingredients.state.error} onRetry={ingredients.reload} /> : null}
      {locations.state.kind === "erro" ? <ErrorState error={locations.state.error} onRetry={locations.reload} /> : null}
      {command.error ? (
        <p className="error" role="alert">
          {humanError(command.error)}
        </p>
      ) : null}
      {success ? (
        <p className="manual-success" role="status">
          {success}
        </p>
      ) : null}

      <section className="manual-section">
        <h2>1. O que existe e onde</h2>
        <div className="manual-units">
          <label className="manual-label">
            Ingrediente
            <select value={ingredientId} onChange={(event) => setIngredientId(event.target.value)}>
              <option value="">Escolher…</option>
              {(ingredients.state.kind === "ok" ? ingredients.state.data.items : []).map((row: IngredientCard) => (
                <option key={row.id} value={row.id}>
                  {row.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="manual-label">
            Lugar
            <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
              <option value="">Escolher…</option>
              {(locations.state.kind === "ok" ? locations.state.data.items : []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="manual-label">
            Data da contagem
            <input type="date" value={occurredOn} onChange={(event) => setOccurredOn(event.target.value)} />
          </label>
        </div>
        <p>
          <Link to="/componentes/ingredientes/novo">Cadastrar ingrediente sem nota</Link>
          {" · "}o cadastro não cria estoque.
        </p>
      </section>

      <section className="manual-section">
        <h2>2. Quantidade, lote e origem</h2>
        <div className="manual-units">
          <label className="manual-label">
            Quantidade
            <input value={quantity} inputMode="decimal" onChange={(event) => setQuantity(event.target.value)} />
          </label>
          <label className="manual-label">
            Unidade
            <select value={unitCode} onChange={(event) => setUnitCode(event.target.value)}>
              <option value="un">un</option>
              <option value="g">g</option>
              <option value="kg">kg</option>
            </select>
          </label>
          <label className="manual-label">
            Lote ou identificação
            <input
              value={lotCode}
              onChange={(event) => setLotCode(event.target.value)}
              placeholder="Opcional"
            />
          </label>
        </div>
        <label className="manual-label">
          Origem ou motivo
          <input
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            placeholder="Ex.: contagem física da despensa"
          />
        </label>
      </section>

      <section className="manual-section">
        <h2>3. Custo desta abertura</h2>
        <div className="receipt-choices receipt-choices--pair" role="radiogroup" aria-label="Situação do custo">
          <label className="receipt-choice">
            <input
              type="radio"
              name="custo-abertura"
              checked={costMode === "known"}
              onChange={() => setCostMode("known")}
            />
            Custo unitário informado
          </label>
          <label className="receipt-choice">
            <input
              type="radio"
              name="custo-abertura"
              checked={costMode === "unknown"}
              onChange={() => {
                setCostMode("unknown");
                setUnitCost("");
              }}
            />
            Custo desconhecido
          </label>
        </div>
        {costMode === "known" ? (
          <label className="manual-label">
            Custo unitário (R$)
            <input value={unitCost} inputMode="decimal" onChange={(event) => setUnitCost(event.target.value)} />
          </label>
        ) : null}
        {costMode === "unknown" ? (
          <p className="manual-footnote">
            Recorte de custo: por lote. O desconhecido não vira zero. Custo e margem deste lote ficam incompletos até
            alguém informar um valor. Se o mesmo ingrediente tiver outro lote com custo conhecido, o cálculo completo
            não é apresentado.
          </p>
        ) : null}
        {fieldError ? (
          <p className="error" role="alert">
            {fieldError}
          </p>
        ) : null}
      </section>

      <section className="manual-section manual-final">
        <div>
          <h2>Revisar antes de confirmar</h2>
          <p>
            {destination && place
              ? `${quantity || "?"} ${unitCode} de ${destination.display_name} em ${place.display_name}${
                  lotCode ? ` · lote ${lotCode}` : ""
                }. ${
                  costMode === "unknown"
                    ? "Custo desconhecido."
                    : unitCost
                      ? `Custo informado: R$ ${unitCost}.`
                      : "Custo ainda não informado."
                } Isso não cria nota, fornecedor nem conversão.`
              : "Preencha o ingrediente, o lugar e a quantidade para ver o efeito."}
          </p>
          <label className="receipt-choice">
            <input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />
            Confirmo esta abertura com os valores acima
          </label>
        </div>
        <button
          type="button"
          className="manual-primary"
          disabled={!canAdjust || command.pending}
          onClick={() => void confirm()}
        >
          {command.pending ? "Registrando…" : "Confirmar abertura"}
        </button>
      </section>
    </div>
  );
}
