import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import type { Envelope, FiscalDocument, FiscalDocumentItem, IngredientPage } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDate, formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  FISCAL_CHECK_LABEL,
  fiscalAttachmentLabel,
  fiscalCheckLabel,
  fiscalDocumentTitle,
  fiscalItemTitle,
  fiscalMatchLabel,
  fiscalMatchTone,
  fiscalMoney,
  fiscalNextActionLabel,
  fiscalOriginLabel,
  fiscalProgressSentence,
  fiscalQuantityLabel,
  fiscalStatusLabel,
  fiscalStatusTone,
  fiscalStockLabel,
  fiscalSupplierLabel,
  fiscalSupplierRegistrationLabel,
  formatAccessKey,
  formatTaxId,
} from "../language/fiscal";
import { useCommand } from "../ops/useCommand";
import {
  canCheckFiscalItem,
  canConfirmFiscalReceipt,
  canMatchFiscalItem,
  canReadFiscalPrice,
} from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";
import {
  conversionPreview,
  factorIsUsable,
  purchaseCostCaption,
  receiptGaps,
  sameUnit,
  type ReceiptGap,
} from "./receiptReview";

const STOCK_UNITS = ["g", "kg", "un", "ml", "l"];

type LineDraft = {
  ingredientId: string;
  creating: boolean;
  newName: string;
  stockUnit: string;
  factor: string;
  received: string;
  result: string;
  lot: string;
  expires: string;
  notes: string;
};

type StorageLocation = {
  id: string;
  display_name: string;
  status: string;
  establishment_id?: string;
};

function codeFromName(name: string): string {
  const base = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return `${base || "item"}-${crypto.randomUUID().slice(0, 4)}`;
}

function costOf(item: FiscalDocumentItem, currency: string | null | undefined) {
  return purchaseCostCaption({
    invoiceUnitPrice: item.invoice_unit_price,
    invoiceUnit: item.unit_code,
    stockUnitCost: item.stock_unit_cost,
    stockUnit: item.stock_unit_code || item.converted_unit_code,
    fallbackUnitCost: item.stock_unit_cost ? null : item.unit_cost,
    currency,
  });
}

function CostCaption({
  item,
  currency,
}: {
  item: FiscalDocumentItem;
  currency?: string | null;
}) {
  const cost = costOf(item, currency);
  if (!cost.note && !cost.stock) return <p>Custo de compra ainda não informado nesta linha.</p>;
  return (
    <>
      {cost.note ? (
        <p>
          <strong>Na nota: </strong>
          {cost.note}
        </p>
      ) : null}
      {cost.stock ? (
        <p>
          <strong>No estoque: </strong>
          {cost.stock}
        </p>
      ) : null}
      {item.total_cost ? (
        <p>
          <strong>Total da linha: </strong>
          {fiscalMoney(item.total_cost, currency)}
        </p>
      ) : null}
    </>
  );
}

function CostCells({
  item,
  currency,
}: {
  item: FiscalDocumentItem;
  currency?: string | null;
}) {
  const cost = costOf(item, currency);
  return (
    <>
      <td>{cost.note ?? "Não informado"}</td>
      <td>{cost.stock ?? "Registrado na confirmação"}</td>
    </>
  );
}

function ResultCost({
  item,
  currency,
}: {
  item: FiscalDocumentItem;
  currency?: string | null;
}) {
  const cost = costOf(item, currency);
  const parts = [
    cost.note ? `na nota ${cost.note}` : null,
    cost.stock ? `no estoque ${cost.stock}` : null,
  ].filter((part): part is string => Boolean(part));
  if (parts.length === 0) return null;
  return <span>{` · ${parts.join(" · ")}`}</span>;
}

function focusAnchor(anchor: string) {
  const node = window.document.getElementById(anchor);
  if (!node) return;
  node.scrollIntoView({ block: "center" });
  const field = node.querySelector("input, select, textarea, button");
  if (field instanceof HTMLElement) field.focus();
}

function draftFromItem(item: FiscalDocumentItem): LineDraft {
  const stockUnit = item.stock_unit_code || item.converted_unit_code || item.unit_code || "";
  const savedFactor = item.conversion_factor ?? "";
  return {
    ingredientId: item.match.status === "matched" ? (item.match.target_id ?? "") : "",
    creating: false,
    newName: "",
    stockUnit,
    factor: sameUnit(item.unit_code, stockUnit) ? "" : savedFactor,
    received: item.physical?.received_quantity ?? "",
    result: item.physical?.result ?? "ok",
    lot: item.physical?.lot_code ?? "",
    expires: item.physical?.expires_on?.slice(0, 10) ?? "",
    notes: item.physical?.notes ?? "",
  };
}

export function FiscalDocumentPage() {
  const { documentId } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();

  const [drafts, setDrafts] = useState<Record<string, LineDraft>>({});
  const [lineErrors, setLineErrors] = useState<Record<string, string>>({});
  const [locationId, setLocationId] = useState("");
  const [newLocationName, setNewLocationName] = useState("");
  const [acceptDivergence, setAcceptDivergence] = useState(false);
  const stepKeys = useRef<Record<string, string>>({});
  const skipDraftSave = useRef(true);

  const { state, reload } = useAsyncResource<Envelope<FiscalDocument>>(
    () => api.getFiscalDocument(documentId!),
    [api, documentId, orgId],
    Boolean(orgId && documentId),
  );

  const document = state.kind === "ok" ? state.data.data : null;
  const canMatch = canMatchFiscalItem(hasPermission);
  const canCheck = canCheckFiscalItem(hasPermission);
  const canConfirm = canConfirmFiscalReceipt(hasPermission);
  // A API declara se este perfil recebeu os campos de custo; a permissão só evita pedir à toa.
  const showCosts = document ? document.cost_access : canReadFiscalPrice(hasPermission);

  const canCreateIngredient = hasPermission("ingredient.create");
  const canManageStock = hasPermission("inventory.item.manage");

  const { state: ingredientsState, reload: reloadIngredients } = useAsyncResource<IngredientPage>(
    () => api.listIngredients({ limit: "200", offset: "0" }),
    [api, orgId],
    Boolean(orgId) && canMatch && hasPermission("ingredient.read"),
  );
  const ingredients = ingredientsState.kind === "ok" ? ingredientsState.data.items : [];

  const { state: locationsState, reload: reloadLocations } = useAsyncResource<{ items: StorageLocation[] }>(
    () => api.listInventory<StorageLocation>("/inventory/locations"),
    [api, orgId],
    Boolean(orgId) && hasPermission("inventory.read"),
  );
  const locations = locationsState.kind === "ok" ? locationsState.data.items : [];
  const placeLocations = locations.filter(
    (row) =>
      row.status !== "inactive" &&
      (!document?.establishment_id || row.establishment_id === document.establishment_id),
  );

  useEffect(() => {
    if (!documentId) return;
    const raw = sessionStorage.getItem(`panne-receipt:${documentId}`);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw) as {
        drafts?: Record<string, LineDraft>;
        locationId?: string;
        newLocationName?: string;
      };
      if (saved.drafts) setDrafts(saved.drafts);
      if (saved.locationId) setLocationId(saved.locationId);
      if (saved.newLocationName) setNewLocationName(saved.newLocationName);
    } catch {
      sessionStorage.removeItem(`panne-receipt:${documentId}`);
    }
  }, [documentId]);

  useEffect(() => {
    if (!documentId) return;
    if (skipDraftSave.current) {
      skipDraftSave.current = false;
      return;
    }
    sessionStorage.setItem(
      `panne-receipt:${documentId}`,
      JSON.stringify({ drafts, locationId, newLocationName }),
    );
  }, [documentId, drafts, locationId, newLocationName]);

  useEffect(() => {
    if (!document) return;
    setDrafts((current) => {
      const next = { ...current };
      for (const item of document.items) {
        if (!next[item.id]) next[item.id] = draftFromItem(item);
      }
      return next;
    });
  }, [document]);

  useEffect(() => {
    if (locationsState.kind !== "ok" || !locationId) return;
    if (!placeLocations.some((row) => row.id === locationId)) setLocationId("");
  }, [locationsState.kind, locationId, placeLocations]);

  useEffect(() => {
    if (!locationId && placeLocations.length === 1) setLocationId(placeLocations[0].id);
  }, [locationId, placeLocations]);

  function stepKey(name: string): string {
    if (!stepKeys.current[name]) stepKeys.current[name] = crypto.randomUUID();
    return stepKeys.current[name];
  }

  function patchDraft(itemId: string, patch: Partial<LineDraft>) {
    setDrafts((current) => {
      const base = current[itemId];
      if (!base) return current;
      return { ...current, [itemId]: { ...base, ...patch } };
    });
  }

  async function saveLine(item: FiscalDocumentItem) {
    if (!document || command.pending) return;
    const draft = drafts[item.id];
    if (!draft) return;
    const stockUnit = draft.stockUnit.trim() || item.unit_code || "";
    if (!factorIsUsable(item.unit_code, stockUnit, draft.factor)) {
      setLineErrors((current) => ({
        ...current,
        [item.id]:
          "Informe quantas unidades de estoque equivalem a 1 unidade da nota. Unidades diferentes não aceitam fator 1.",
      }));
      return;
    }
    const received = draft.received.trim().replace(",", ".");
    if (!received || Number(received) <= 0) {
      setLineErrors((current) => ({
        ...current,
        [item.id]: "Informe a quantidade que chegou. A quantidade da nota não entra no lugar dela.",
      }));
      return;
    }
    if (draft.creating && !draft.newName.trim()) {
      setLineErrors((current) => ({ ...current, [item.id]: "Dê um nome ao insumo antes de guardar." }));
      return;
    }
    if (!draft.creating && !draft.ingredientId && item.match.status !== "matched") {
      setLineErrors((current) => ({ ...current, [item.id]: "Escolha um insumo ou crie um nesta revisão." }));
      return;
    }
    try {
      await command.run(`fiscal-line:${item.id}`, async () => {
        let ingredientId = draft.creating ? "" : draft.ingredientId || item.match.target_id || "";
        if (draft.creating) {
          if (!canCreateIngredient) throw new Error("Seu papel não cria insumos.");
          const catalog = await api.getCatalogUnits();
          const gram = catalog.data.find((unit) => (unit.code ?? "").toLowerCase() === "g");
          if (!gram) throw new Error("O catálogo não tem a unidade grama para abrir o insumo.");
          const created = await api.catalogCommand<{ data: { id: string } }>("/ingredients", {
            body: {
              code: codeFromName(draft.newName),
              display_name: draft.newName.trim(),
              ingredient_type: "simple",
              nutrition_basis_unit_id: gram.id,
            },
            idempotencyKey: stepKey(`${item.id}:ingredient`),
          });
          ingredientId = created.data.id;
        }
        if (!ingredientId) throw new Error("Escolha ou crie o insumo deste item.");
        const listed = await api.listInventory<{ id: string; ingredient_id: string; unit_code: string }>(
          "/inventory/items",
        );
        let stock = listed.items.find((row) => row.ingredient_id === ingredientId);
        const requestedUnit = sameUnit(item.unit_code, stockUnit) ? item.unit_code || stockUnit : stockUnit;
        if (!stock) {
          if (!canManageStock) {
            throw new Error(
              "Este insumo ainda não está no estoque. Quem administra o estoque precisa concluir o cadastro.",
            );
          }
          const createdItem = await api.catalogCommand<{ data: { id: string; unit_code?: string } }>(
            "/inventory/items",
            {
              body: { ingredient_id: ingredientId, unit_code: requestedUnit, lot_control: "optional" },
              idempotencyKey: stepKey(`${item.id}:stock-item`),
            },
          );
          stock = {
            id: createdItem.data.id,
            ingredient_id: ingredientId,
            unit_code: createdItem.data.unit_code || requestedUnit,
          };
        }
        if (!sameUnit(requestedUnit, stock.unit_code)) {
          throw new Error(`Este insumo já é estocado em ${stock.unit_code}. Use essa unidade na conversão.`);
        }
        const factor = sameUnit(item.unit_code, stock.unit_code) ? "1" : String(Number(draft.factor.replace(",", ".")));
        await api.matchFiscalItem(
          document.id,
          item.id,
          {
            target_type: "ingredient",
            target_id: ingredientId,
            inventory_item_id: stock.id,
            unit_code: stock.unit_code,
            conversion_factor: factor,
          },
          stepKey(`${item.id}:match`),
        );
        await api.recordFiscalPhysical(
          document.id,
          item.id,
          {
            received_quantity: received,
            unit_code: stock.unit_code,
            result: draft.result,
            supplier_lot_code: draft.lot.trim() || null,
            expires_on: draft.expires || null,
            notes: draft.notes.trim() || null,
          },
          stepKey(`${item.id}:physical`),
        );
      });
      setLineErrors((current) => ({ ...current, [item.id]: "" }));
      reloadIngredients();
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  async function createLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!document?.establishment_id || command.pending || !newLocationName.trim()) return;
    if (!canManageStock) return;
    try {
      const created = await command.run(`fiscal-location:${document.id}`, (key) =>
        api.catalogCommand<{ data: { id: string } }>("/inventory/locations", {
          body: {
            establishment_id: document.establishment_id,
            code: codeFromName(newLocationName),
            display_name: newLocationName.trim(),
            kind: "warehouse",
          },
          idempotencyKey: key,
        }),
      );
      if (created?.data.id) setLocationId(created.data.id);
      setNewLocationName("");
      reloadLocations();
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  async function confirmReceipt() {
    if (!document || command.pending || !locationId) return;
    try {
      await command.run(`fiscal-confirm:${document.id}:${locationId}`, (key) =>
        api.confirmFiscalReceipt(
          document.id,
          { inventory_location_id: locationId, accept_divergence: acceptDivergence },
          key,
        ),
      );
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  const title = document ? fiscalDocumentTitle(document) : "Entrada fiscal";
  const gaps: ReceiptGap[] = document
    ? receiptGaps({ document, locationId, drafts, acceptDivergence })
    : [];
  const serverStillBlocks = Boolean(document && !document.stock_applied && document.pending_reasons.length > 0);
  const confirmBlocked = gaps.length > 0 || serverStillBlocks;

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        entityLabel={title}
        status={document ? fiscalStatusLabel(document.status) : undefined}
        next={document ? fiscalNextActionLabel(document.next_action, document.next_action_label) : undefined}
      />
      <div>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => reload()} /> : null}
        {document ? (
          <>
            <div className="page-head">
              <div>
                <h1>{title}</h1>
              </div>
            </div>
            <p className="lede">
              <StatusBadge
                tone={fiscalStatusTone(document.status)}
                label={document.status_label?.trim() || fiscalStatusLabel(document.status)}
              />{" "}
              {fiscalSupplierLabel(document.supplier)} · {fiscalProgressSentence(document)}
            </p>

            {(document.operational_notes ?? []).length > 0 ? (
              <section className="panel">
                <h2>O que ainda falta nesta fase</h2>
                <ul>
                  {(document.operational_notes ?? []).map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="panel">
              <h2>Qual é o documento</h2>
              <p>
                <strong>Identificação: </strong>
                {title}
              </p>
              <p>
                <strong>Chave de acesso: </strong>
                {formatAccessKey(document.access_key)}
              </p>
              <p>
                <strong>Emissão: </strong>
                {formatDate(document.issued_on)}
              </p>
              <p>
                <strong>Origem do registro: </strong>
                {fiscalOriginLabel(document.origin)}
              </p>
              <p>
                <strong>Anexos: </strong>
                {document.attachments.length === 0
                  ? "Nenhum arquivo anexado a esta entrada."
                  : null}
              </p>
              {document.attachments.length > 0 ? (
                <ul className="fiscal-attachments">
                  {document.attachments.map((attachment) => (
                    <li key={attachment.id}>
                      {attachment.filename?.trim() || fiscalAttachmentLabel(attachment.kind)}
                      <span className="meta">
                        {" "}
                        · {fiscalAttachmentLabel(attachment.kind)} · enviado em{" "}
                        {formatDateTime(attachment.uploaded_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {document.attachments.length > 0 ? (
                <p className="meta">
                  Os arquivos ficam guardados no armazenamento privado da organização e não abrem por
                  endereço público.
                </p>
              ) : null}
            </section>

            <section className="panel">
              <h2>Quem forneceu</h2>
              <p>
                <strong>Fornecedor: </strong>
                {document.supplier?.id && hasPermission("supplier.read") ? (
                  <Link to={`/componentes/fornecedores/${document.supplier.id}`}>
                    {fiscalSupplierLabel(document.supplier)}
                  </Link>
                ) : (
                  fiscalSupplierLabel(document.supplier)
                )}
              </p>
              <p>
                <strong>CNPJ: </strong>
                {formatTaxId(document.supplier?.tax_id)}
              </p>
              <p>{fiscalSupplierRegistrationLabel(document.supplier)}</p>
            </section>

            <section className="panel" aria-labelledby="revisao-entrada">
              <h2 id="revisao-entrada">Revisão do que chegou</h2>
              <p className="meta">
                A nota e o XML ficam como chegaram. Escolher ou criar insumo e local não movimenta
                estoque. A entrada só acontece em Confirmar entrada.
              </p>
              {document.establishment_name ? (
                <p>
                  <strong>Estabelecimento: </strong>
                  {document.establishment_name}. O local de estoque é o lugar dentro dele, não o
                  estabelecimento em si.
                </p>
              ) : null}
              {document.supplier && !document.supplier.registered ? (
                <p>
                  O emitente ainda não está no cadastro de fornecedores. Isso não impede a entrada
                  nem cria o fornecedor sozinho.
                </p>
              ) : null}
              {document.items.length === 0 ? (
                <p>Este documento ainda não tem itens informados.</p>
              ) : (
                document.items.map((item) => {
                  const draft = drafts[item.id] ?? draftFromItem(item);
                  const stockUnit = draft.stockUnit || item.unit_code || "";
                  const needsFactor = !sameUnit(item.unit_code, stockUnit);
                  const preview = conversionPreview(
                    item.invoiced_quantity,
                    item.unit_code,
                    draft.factor,
                    stockUnit,
                  );
                  const unitOptions = Array.from(
                    new Set(
                      [item.unit_code, stockUnit, ...STOCK_UNITS].filter(
                        (unit): unit is string => Boolean(unit && unit.trim()),
                      ),
                    ),
                  );
                  const suggested =
                    item.match.status === "suggested" &&
                    item.match.target_kind === "ingredient" &&
                    item.match.target_id;
                  return (
                    <article key={item.id} className="receipt-line">
                      <h3>{fiscalItemTitle(item)}</h3>
                      <p>
                        <strong>Na nota: </strong>
                        {fiscalQuantityLabel(item.invoiced_quantity, item.unit_code)}
                        {item.supplier_sku ? ` · referência ${item.supplier_sku}` : ""}
                      </p>
                      {showCosts ? (
                        <CostCaption
                          item={item}
                          currency={document.costs?.currency ?? document.currency}
                        />
                      ) : null}
                      <p>
                        <StatusBadge
                          tone={fiscalMatchTone(item.match.status)}
                          label={fiscalMatchLabel(item.match.status)}
                        />
                        {item.match.target_label ? ` · ${item.match.target_label}` : ""}
                      </p>
                      {item.converted_quantity && item.converted_unit_code ? (
                        <p className="meta">
                          Conta já guardada: {fiscalQuantityLabel(item.invoiced_quantity, item.unit_code)} ×{" "}
                          {item.conversion_factor} ={" "}
                          {fiscalQuantityLabel(item.converted_quantity, item.converted_unit_code)}
                        </p>
                      ) : null}
                      {document.stock_applied ? (
                        <p>
                          Entrou {fiscalQuantityLabel(item.physical?.received_quantity, item.physical?.unit_code)}
                          {document.storage_location_label
                            ? ` em ${document.storage_location_label}`
                            : ""}
                          .
                        </p>
                      ) : (
                        <div className="fiscal-check-form">
                          <div id={`item-${item.id}-insumo`}>
                            {canMatch ? (
                              <>
                                {suggested ? (
                                  <p>
                                    Há uma sugestão para este item
                                    {item.match.suggestion_reason ? `: ${item.match.suggestion_reason}` : ""}. Ela
                                    só vale se você usar.
                                    <button
                                      type="button"
                                      className="ghost"
                                      disabled={command.pending}
                                      onClick={() =>
                                        patchDraft(item.id, {
                                          creating: false,
                                          ingredientId: item.match.target_id ?? "",
                                        })
                                      }
                                    >
                                      Usar a sugestão
                                    </button>
                                  </p>
                                ) : null}
                                {!draft.creating && ingredients.length > 0 ? (
                                  <label>
                                    Insumo de destino
                                    <select
                                      value={draft.ingredientId}
                                      disabled={command.pending}
                                      onChange={(event) =>
                                        patchDraft(item.id, { ingredientId: event.target.value, creating: false })
                                      }
                                    >
                                      <option value="">Escolher insumo…</option>
                                      {draft.ingredientId &&
                                      !ingredients.some((row) => row.id === draft.ingredientId) ? (
                                        <option value={draft.ingredientId}>
                                          {item.match.target_label || "Insumo já escolhido"}
                                        </option>
                                      ) : null}
                                      {ingredients.map((ingredient) => (
                                        <option key={ingredient.id} value={ingredient.id}>
                                          {ingredient.display_name}
                                        </option>
                                      ))}
                                    </select>
                                  </label>
                                ) : null}
                                {canCreateIngredient ? (
                                  draft.creating || ingredients.length === 0 ? (
                                    <label>
                                      Nome do insumo novo
                                      <input
                                        value={draft.newName}
                                        autoComplete="off"
                                        disabled={command.pending}
                                        onChange={(event) =>
                                          patchDraft(item.id, { creating: true, newName: event.target.value })
                                        }
                                      />
                                    </label>
                                  ) : (
                                    <p>
                                      <button
                                        type="button"
                                        className="ghost"
                                        disabled={command.pending}
                                        onClick={() => patchDraft(item.id, { creating: true })}
                                      >
                                        Criar insumo nesta revisão
                                      </button>
                                    </p>
                                  )
                                ) : ingredients.length === 0 ? (
                                  <p>
                                    Não há insumo cadastrado. Quem cria insumos precisa abrir este item; a nota
                                    continua salva.
                                  </p>
                                ) : null}
                                {draft.creating && ingredients.length > 0 ? (
                                  <p>
                                    <button
                                      type="button"
                                      className="ghost"
                                      disabled={command.pending}
                                      onClick={() => patchDraft(item.id, { creating: false, newName: "" })}
                                    >
                                      Escolher um insumo existente
                                    </button>
                                  </p>
                                ) : null}
                              </>
                            ) : (
                              <p>Definir o insumo cabe a quem revisa a entrada. A nota continua salva.</p>
                            )}
                          </div>
                          <label>
                            Unidade de estoque
                            <select
                              value={stockUnit}
                              disabled={command.pending || !canMatch}
                              onChange={(event) =>
                                patchDraft(item.id, { stockUnit: event.target.value, factor: "" })
                              }
                            >
                              {unitOptions.map((unit) => (
                                <option key={unit} value={unit}>
                                  {unit}
                                </option>
                              ))}
                            </select>
                          </label>
                          {needsFactor ? (
                            <div id={`item-${item.id}-fator`}>
                              <label>
                                Quantas {stockUnit} equivalem a 1 {item.unit_code || "unidade da nota"}
                                <input
                                  value={draft.factor}
                                  inputMode="decimal"
                                  autoComplete="off"
                                  disabled={command.pending || !canMatch}
                                  onChange={(event) => patchDraft(item.id, { factor: event.target.value })}
                                />
                              </label>
                              {preview ? (
                                <p>
                                  Se a quantidade da nota chegar inteira: {preview}. A quantidade que chegou é a
                                  que você registrar abaixo.
                                </p>
                              ) : (
                                <p className="meta">
                                  A unidade da nota e a do estoque são diferentes. Informe o fator. O nome do
                                  produto não define essa conta.
                                </p>
                              )}
                            </div>
                          ) : null}
                          <div id={`item-${item.id}-chegou`}>
                            {canCheck ? (
                              <>
                                <label>
                                  Quantidade que chegou
                                  <input
                                    value={draft.received}
                                    inputMode="decimal"
                                    autoComplete="off"
                                    placeholder="Informe o que chegou"
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { received: event.target.value })}
                                  />
                                </label>
                                <label>
                                  Conferência
                                  <select
                                    value={draft.result}
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { result: event.target.value })}
                                  >
                                    {Object.keys(FISCAL_CHECK_LABEL).map((code) => (
                                      <option key={code} value={code}>
                                        {fiscalCheckLabel(code)}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                                <label>
                                  Lote do fornecedor, se houver
                                  <input
                                    value={draft.lot}
                                    autoComplete="off"
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { lot: event.target.value })}
                                  />
                                </label>
                                <label>
                                  Validade, se houver
                                  <input
                                    type="date"
                                    value={draft.expires}
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { expires: event.target.value })}
                                  />
                                </label>
                                <label>
                                  Observação
                                  <textarea
                                    value={draft.notes}
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { notes: event.target.value })}
                                  />
                                </label>
                              </>
                            ) : (
                              <p>Registrar o que chegou cabe a quem confere a entrada.</p>
                            )}
                          </div>
                          {lineErrors[item.id] ? (
                            <p className="error" role="alert">
                              {lineErrors[item.id]}
                            </p>
                          ) : null}
                          {canMatch && canCheck ? (
                            <p>
                              <button
                                type="button"
                                className="primary"
                                disabled={command.pending}
                                onClick={() => void saveLine(item)}
                              >
                                Guardar este item
                              </button>
                            </p>
                          ) : null}
                        </div>
                      )}
                    </article>
                  );
                })
              )}

              <div id="local-estoque">
                <h3>Local de estoque</h3>
                <p className="meta">
                  Toda esta nota entra no mesmo local. Itens com unidades diferentes usam cada um o seu fator.
                </p>
                {document.stock_applied ? (
                  <p>
                    {document.storage_location_label?.trim() ||
                      "A mercadoria já foi lançada no estoque desta entrada."}
                  </p>
                ) : !canConfirm ? (
                  <p>A escolha do local de estoque cabe a quem confirma a entrada.</p>
                ) : (
                  <>
                    {placeLocations.length > 0 ? (
                      <label>
                        Local que vai receber
                        <select
                          value={locationId}
                          onChange={(event) => setLocationId(event.target.value)}
                          disabled={command.pending}
                        >
                          <option value="">Escolher o local…</option>
                          {placeLocations.map((location) => (
                            <option key={location.id} value={location.id}>
                              {location.display_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <p role="status">Nenhum local de estoque neste estabelecimento.</p>
                    )}
                    {canManageStock && document.establishment_id ? (
                      <form onSubmit={(event) => void createLocation(event)}>
                        <label>
                          Nome do local novo
                          <input
                            value={newLocationName}
                            autoComplete="off"
                            disabled={command.pending}
                            onChange={(event) => setNewLocationName(event.target.value)}
                          />
                        </label>
                        <p>
                          <button type="submit" className="ghost" disabled={command.pending || !newLocationName.trim()}>
                            Criar local nesta revisão
                          </button>
                        </p>
                      </form>
                    ) : placeLocations.length === 0 ? (
                      <p>
                        Quem administra o estoque precisa cadastrar um local neste estabelecimento. A nota
                        continua salva.
                      </p>
                    ) : null}
                  </>
                )}
              </div>
            </section>

            {showCosts ? (
              <section className="panel">
                <h2>Quanto custou</h2>
                <p>
                  <strong>Total do documento: </strong>
                  {fiscalMoney(document.costs?.document_total ?? document.document_total, document.costs?.currency ?? document.currency)}
                </p>
                <p>
                  <strong>Itens: </strong>
                  {fiscalMoney(document.costs?.items_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Frete: </strong>
                  {fiscalMoney(document.costs?.freight_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Descontos: </strong>
                  {fiscalMoney(document.costs?.discount_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Tributos destacados: </strong>
                  {fiscalMoney(document.costs?.taxes_total, document.costs?.currency)}
                </p>
                {document.items.some((item) => item.unit_cost != null) ? (
                  <div className="table-wrap">
                    <table>
                      <caption>Custo por item do documento</caption>
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>Custo na nota</th>
                          <th>Custo no estoque</th>
                          <th>Custo total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {document.items.map((item) => (
                          <tr key={item.id}>
                            <td>{fiscalItemTitle(item)}</td>
                            <CostCells item={item} currency={document.costs?.currency ?? document.currency} />
                            <td>{fiscalMoney(item.total_cost, document.costs?.currency)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                <p className="meta">
                  Valor do documento não é preço vigente do ingrediente. O histórico de preço é
                  atualizado na confirmação da entrada.
                </p>
              </section>
            ) : (
              <section className="panel">
                <h2>Quanto custou</h2>
                <p>Valores do documento ficam ocultos para o seu papel.</p>
              </section>
            )}

            <section className="panel">
              <h2>O estoque já foi atualizado</h2>
              <p>
                <StatusBadge
                  tone={document.stock_applied ? "sucesso" : "atencao"}
                  label={document.stock_applied ? "Estoque atualizado" : "Estoque ainda não atualizado"}
                />{" "}
                {fiscalStockLabel(document.stock_applied, document.stock_summary)}
              </p>
              {document.stock_applied ? (
                <ul>
                  {document.items.map((item) => (
                    <li key={item.id}>
                      {item.match.target_label || fiscalItemTitle(item)}:{" "}
                      {fiscalQuantityLabel(item.physical?.received_quantity, item.physical?.unit_code)}
                      {document.storage_location_label ? ` em ${document.storage_location_label}` : ""}
                      {showCosts ? <ResultCost item={item} currency={document.costs?.currency ?? document.currency} /> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {document.stock_applied && hasPermission("inventory.read") ? (
                <p>
                  <Link className="ghost" to="/componentes/estoque/posicao">
                    Abrir posição de estoque
                  </Link>
                </p>
              ) : null}
            </section>

            <section className="panel">
              <h2>Próxima ação</h2>
              <p>{fiscalNextActionLabel(document.next_action, document.next_action_label)}</p>
              {gaps.length > 0 ? (
                <>
                  <p className="meta">Pendências que ainda seguram esta entrada:</p>
                  <ul>
                    {gaps.map((gap) => (
                      <li key={gap.key}>
                        {gap.text}{" "}
                        <button type="button" className="ghost" onClick={() => focusAnchor(gap.anchor)}>
                          Ir ao campo
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              ) : serverStillBlocks ? (
                <ul>
                  {document.pending_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              ) : null}
              {command.error ? (
                <p className="error" role="alert">
                  {command.error.message || "Não foi possível concluir a ação."}
                </p>
              ) : null}
              {canConfirm && !document.stock_applied && document.divergence_count > 0 ? (
                <label id="aceite-divergencia">
                  <input
                    type="checkbox"
                    checked={acceptDivergence}
                    onChange={(event) => setAcceptDivergence(event.target.checked)}
                    disabled={command.pending}
                  />{" "}
                  A divergência permanece na nota. Confirmo que a entrada pode ser concluída assim.
                </label>
              ) : null}
              <p>
                {canConfirm && !document.stock_applied ? (
                  <button
                    type="button"
                    className="primary"
                    disabled={command.pending || confirmBlocked || document.items.length === 0}
                    onClick={() => void confirmReceipt()}
                  >
                    Confirmar entrada e atualizar estoque
                  </button>
                ) : !document.stock_applied ? (
                  <span>A confirmação cabe a quem pode atualizar o estoque.</span>
                ) : null}{" "}
                <Link className="ghost" to="/gestao/compras/entradas">
                  Voltar às entradas fiscais
                </Link>
              </p>
            </section>

            <details className="fiscal-history">
              <summary>Histórico e auditoria desta entrada</summary>
              <p className="meta">
                Registro de quem fez o quê. Correção se faz por novo registro, nunca apagando o
                anterior.
              </p>
              {showCosts ? (
                <ul>
                  {document.items.map((item) => {
                    const cost = costOf(item, document.costs?.currency ?? document.currency);
                    if (!cost.note && !cost.stock) return null;
                    return (
                      <li key={item.id}>
                        {fiscalItemTitle(item)}
                        {cost.note ? ` · na nota ${cost.note}` : ""}
                        {cost.stock ? ` · no estoque ${cost.stock}` : ""}
                      </li>
                    );
                  })}
                </ul>
              ) : null}
              {document.history.length === 0 ? (
                <p>Ainda não há passos registrados nesta entrada.</p>
              ) : (
                <ol className="fiscal-history__list">
                  {document.history.map((event) => (
                    <li key={event.id}>
                      <strong>{event.action_label?.trim() || "Passo registrado"}</strong>
                      <span className="meta">
                        {" "}
                        {formatDateTime(event.occurred_at)}
                        {event.actor_label ? ` · ${event.actor_label}` : ""}
                      </span>
                      {event.detail ? <p>{event.detail}</p> : null}
                    </li>
                  ))}
                </ol>
              )}
              <TechnicalAuditDetails
                rows={[
                  { label: "Identificador da entrada", value: document.id, copyable: true },
                  { label: "Versão de linha", value: String(document.row_version) },
                  { label: "Atualizado em", value: formatDateTime(document.updated_at) },
                ]}
              />
            </details>
          </>
        ) : null}
      </div>
      <aside className="panel">
        <h2>A ordem importa</h2>
        <p>
          Importe a nota, revise o que chegou nesta tela e confirme a entrada. Criar insumo ou local
          não movimenta estoque. O saldo, o movimento e o custo de compra só nascem na confirmação.
        </p>
        <p>
          Divergência não bloqueia a operação: ela fica registrada e visível para quem negocia com o
          fornecedor.
        </p>
        <p className="meta">
          Confirmar a entrada cria lote, movimenta saldo e alimenta o histórico de preço de compra.
        </p>
      </aside>
    </div>
  );
}

/**
 * O contrato ainda não devolve o nome do item ligado. Enquanto isso a tela diz o tipo do
 * vínculo em palavras, em vez de mostrar o identificador técnico.
 */
