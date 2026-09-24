import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { IngredientCard, LinkableEntry } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { fiscalMoney } from "../language/fiscal";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

function humanError(error: unknown): string {
  if (error instanceof ApiError && error.code === "conflito") {
    return "Outra pessoa alterou este ingrediente. Atualize a página e confirme de novo.";
  }
  if (
    error instanceof ApiError &&
    /conteúdo da embalagem não pode mudar retroativamente/i.test(error.message)
  ) {
    return error.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Não foi possível confirmar os vínculos.";
}

function entryTitle(entry: LinkableEntry): string {
  return entry.description?.trim() || entry.current_ingredient_name || "Entrada sem descrição fiscal";
}

function entryMeta(entry: LinkableEntry): string {
  const parts = [
    entry.document_number ? `Nota ${entry.document_number}` : "Sem número de nota",
    entry.internal_lot_code ? `Lote ${entry.internal_lot_code}` : "Sem lote interno",
    entry.gtin ? `GTIN ${entry.gtin}` : "Sem GTIN",
  ];
  if (entry.current_ingredient_name) parts.push(`Hoje em ${entry.current_ingredient_name}`);
  return parts.join(" · ");
}

export function ConsolidateIngredientPage() {
  const { api, active, hasPermission } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();
  const [destinationId, setDestinationId] = useState("");
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [contentByLot, setContentByLot] = useState<Record<string, { quantity: string; unit: string }>>({});
  const [success, setSuccess] = useState<string | null>(null);

  const ingredients = useAsyncResource(
    () => api.listIngredients({ limit: "50", offset: "0" }),
    [api, orgId],
    Boolean(orgId),
  );
  const entries = useAsyncResource(
    () => api.listLinkableEntries(destinationId || undefined),
    [api, orgId, destinationId],
    Boolean(orgId),
  );

  const destination = useMemo(
    () => ingredients.state.kind === "ok" ? ingredients.state.data.items.find((row) => row.id === destinationId) ?? null : null,
    [ingredients.state, destinationId],
  );
  const rows = entries.state.kind === "ok" ? entries.state.data.items : [];
  const chosen = rows.filter((row) => selected[row.inventory_lot_id]);
  const canConfirm =
    hasPermission("ingredient.update_draft") &&
    hasPermission("inventory.item.manage") &&
    Boolean(destinationId) &&
    chosen.length > 0;

  const totalQty = chosen.reduce((sum, row) => sum + Number(row.quantity || 0), 0);
  const units = Array.from(new Set(chosen.map((row) => row.unit_code))).join(" / ");
  const mixedContent = chosen.some((row, _, all) => {
    const first = all[0];
    return row.package_content_quantity !== first.package_content_quantity || row.package_content_unit !== first.package_content_unit;
  });
  const unknownCostLots = chosen.filter((row) => row.cost_status === "unknown");
  const usedLots = chosen.filter((row) => row.has_downstream_use);

  function toggle(lotId: string) {
    setSelected((current) => ({ ...current, [lotId]: !current[lotId] }));
    setSuccess(null);
  }

  async function confirm() {
    if (!destination || command.pending) return;
    try {
      const result = await command.run(`consolidate:${destination.id}:${chosen.map((row) => row.inventory_lot_id).join(",")}`, (key) =>
        api.consolidateIngredientLinks(
          destination.id,
          {
            expected_row_version: destination.row_version,
            entries: chosen.map((row) => ({
              inventory_lot_id: row.inventory_lot_id,
              fiscal_inbound_item_id: row.fiscal_inbound_item_id,
              package_content_quantity: contentByLot[row.inventory_lot_id]?.quantity || row.package_content_quantity,
              package_content_unit: contentByLot[row.inventory_lot_id]?.unit || row.package_content_unit,
            })),
          },
          key,
        ),
      );
      if (!result) return;
      setSuccess(
        result.replayed
          ? "Esta confirmação já tinha sido registrada. Nada foi duplicado."
          : `${result.destination_name || destination.display_name} recebeu ${result.linked.length} vínculo(s). Notas, lotes, saldos e custos permaneceram iguais.`,
      );
      ingredients.reload();
      entries.reload();
    } catch {
      /* command.error */
    }
  }

  if (ingredients.state.kind === "carregando" && entries.state.kind === "carregando") {
    return <LoadingState />;
  }

  return (
    <div className="manual-path">
      <header className="manual-heading">
        <div>
          <p className="manual-kicker">Organização · {active?.display_name || "atual"}</p>
          <h1>Consolidar insumo</h1>
          <p>Associe compras e lotes a um ingrediente. Nada será unido sem sua confirmação.</p>
        </div>
        <Link className="manual-quiet" to="/componentes/ingredientes">
          Voltar aos ingredientes
        </Link>
      </header>

      {ingredients.state.kind === "erro" ? <ErrorState error={ingredients.state.error} onRetry={ingredients.reload} /> : null}
      {entries.state.kind === "erro" ? <ErrorState error={entries.state.error} onRetry={entries.reload} /> : null}
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
        <h2>1. Ingrediente que será usado na receita</h2>
        <div className="manual-pick">
          <label className="manual-label">
            Ingrediente de destino
            <select
              value={destinationId}
              onChange={(event) => {
                setDestinationId(event.target.value);
                setSelected({});
                setSuccess(null);
              }}
            >
              <option value="">Escolher…</option>
              {(ingredients.state.kind === "ok" ? ingredients.state.data.items : []).map((row: IngredientCard) => (
                <option key={row.id} value={row.id}>
                  {row.display_name}
                </option>
              ))}
            </select>
          </label>
          <p>Este é o nome técnico visto nas receitas. A descrição das notas continua preservada.</p>
          <p>
            <Link to="/componentes/ingredientes/novo">Cadastrar outro ingrediente</Link>
            {" · "}o cadastro é separado desta associação.
          </p>
        </div>
      </section>

      <section className="manual-section">
        <h2>2. Compras que você quer associar</h2>
        <p>Marque apenas as entradas que representam este ingrediente. A nota e o lote permanecem separados.</p>
        {entries.state.kind === "carregando" ? <LoadingState /> : null}
        {rows.length === 0 && entries.state.kind === "ok" ? (
          <p>Não há lotes nesta organização para associar.</p>
        ) : null}
        <div className="manual-purchases">
          {rows.map((entry) => {
            const checked = Boolean(selected[entry.inventory_lot_id]);
            return (
              <label className="manual-row" key={entry.inventory_lot_id}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(entry.inventory_lot_id)}
                  aria-label={`Associar ${entryTitle(entry)}`}
                />
                <span className="manual-row-main">
                  <strong>{entryTitle(entry)}</strong>
                  <small>{entryMeta(entry)}</small>
                  {entry.unit_cost ? <small>Custo da linha: {fiscalMoney(entry.unit_cost, "BRL")}</small> : null}
                  {entry.cost_status === "unknown" ? <small>Custo deste lote: desconhecido. Recorte: por lote.</small> : null}
                  {entry.already_linked ? <small>Já ligado a este destino.</small> : null}
                  {entry.has_downstream_use ? <small>Já houve uso neste lote. O conteúdo não muda retroativamente.</small> : null}
                </span>
                <span>
                  {entry.quantity} {entry.unit_code}
                </span>
              </label>
            );
          })}
        </div>
        <p className="manual-footnote">
          {chosen.length === 0
            ? "Nenhuma entrada selecionada."
            : `Selecionadas: ${chosen.length} ${chosen.length === 1 ? "entrada" : "entradas"}, ${chosen.length} ${
                chosen.length === 1 ? "lote" : "lotes"
              }, ${totalQty} ${units || "embalagens"}. Os custos de cada entrada continuam separados.`}
        </p>
      </section>

      <section className="manual-section">
        <h2>3. Unidade para a receita</h2>
        <p>
          Confirme no rótulo: a Panne não deduz o conteúdo do nome da nota. Se o conteúdo for diferente entre lotes,
          informe-o por entrada.
        </p>
        {mixedContent ? (
          <p className="manual-footnote">Os lotes selecionados já têm conteúdos diferentes. Confirme um a um.</p>
        ) : null}
        {unknownCostLots.length > 0 ? (
          <p className="manual-footnote">
            Recorte de custo: por lote. {unknownCostLots.length === 1 ? "Há 1 lote" : `Há ${unknownCostLots.length} lotes`} com
            custo desconhecido. Isso não vira zero e o custo/margem deste recorte ficam incompletos.
          </p>
        ) : null}
        {usedLots.length > 0 ? (
          <p className="manual-footnote">
            Lote já usado, reservado ou ajustado não aceita mudança de conteúdo. Só a repetição idêntica é aceita.
          </p>
        ) : null}
        {chosen.length === 0 ? <p>Selecione entradas para declarar o conteúdo da embalagem, se necessário.</p> : null}
        {chosen.map((entry) => {
          const current = contentByLot[entry.inventory_lot_id] || {
            quantity: entry.package_content_quantity || "",
            unit: entry.package_content_unit || "kg",
          };
          return (
            <div className="manual-units" key={entry.inventory_lot_id}>
              <div>
                <label className="manual-label">
                  Conteúdo de {entry.internal_lot_code || "este lote"}
                  <input
                    value={current.quantity}
                    inputMode="decimal"
                    disabled={Boolean(entry.has_downstream_use)}
                    onChange={(event) =>
                      setContentByLot((map) => ({
                        ...map,
                        [entry.inventory_lot_id]: { ...current, quantity: event.target.value },
                      }))
                    }
                  />
                </label>
              </div>
              <div>
                <label className="manual-label">
                  Unidade
                  <select
                    value={current.unit}
                    disabled={Boolean(entry.has_downstream_use)}
                    onChange={(event) =>
                      setContentByLot((map) => ({
                        ...map,
                        [entry.inventory_lot_id]: { ...current, unit: event.target.value },
                      }))
                    }
                  >
                    <option value="kg">kg</option>
                    <option value="g">g</option>
                    <option value="un">un</option>
                  </select>
                </label>
              </div>
              <div className="manual-result">
                <span>Registro original</span>
                <strong>
                  {entry.quantity} {entry.unit_code}
                  {current.quantity
                    ? ` · ${current.quantity} ${current.unit} por ${entry.unit_code}`
                    : " · conteúdo ainda não declarado"}
                </strong>
              </div>
            </div>
          );
        })}
      </section>

      <section className="manual-section manual-final">
        <div>
          <h2>Revisar antes de confirmar</h2>
          <p>
            {destination
              ? `O ingrediente ${destination.display_name} receberá o vínculo com ${chosen.length || "as"} ${
                  chosen.length === 1 ? "entrada selecionada" : "entradas selecionadas"
                }. Notas, lotes, saldos e custos não serão apagados nem somados em um novo lançamento.`
              : "Escolha o ingrediente de destino e as entradas antes de confirmar."}
          </p>
        </div>
        <button type="button" className="manual-primary" disabled={!canConfirm || command.pending} onClick={() => void confirm()}>
          {command.pending ? "Confirmando…" : "Confirmar vínculos"}
        </button>
      </section>
    </div>
  );
}
