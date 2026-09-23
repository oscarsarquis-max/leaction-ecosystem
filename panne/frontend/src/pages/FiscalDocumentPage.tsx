import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Envelope, FiscalDocument, FiscalDocumentItem, IngredientPage } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDate, formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  FISCAL_CHECK_LABEL,
  fiscalAttachmentLabel,
  fiscalDocumentTitle,
  fiscalItemTitle,
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
  choiceLabel,
  controlChoices,
  decimalText,
  invoiceSays,
  linePlan,
  movementSentence,
  notesBesideExpected,
  packageHintFromName,
  parseArrived,
  previewStockUnitCost,
  principalStockName,
  selectedChoice,
  spokenUnit,
  suggestControl,
  unitForChoice,
} from "./receiptOperation";
import { purchaseCostCaption, receiptGaps, sameUnit, type ReceiptGap } from "./receiptReview";

type LineDraft = {
  ingredientId: string;
  creating: boolean;
  newName: string;
  stockUnit: string;
  packageContent: string;
  fromName: boolean;
  receivedText: string;
  asExpected: boolean;
  issue: string;
  showLot: boolean;
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
  const hint = packageHintFromName(item.supplier_description);
  const stock = suggestControl({
    invoiceUnit: item.unit_code,
    existingUnit: item.stock_unit_code,
    hint,
  });
  const reliable =
    (item.match.status === "matched" || item.match.status === "suggested") && Boolean(item.match.target_id);
  const recordedIssue = item.physical?.result && item.physical.result !== "ok" ? item.physical.result : "";
  return {
    ingredientId: reliable ? (item.match.target_id ?? "") : "",
    creating: !reliable,
    newName: item.supplier_description.trim(),
    stockUnit: stock.unit,
    packageContent: stock.content ?? "",
    fromName: stock.fromName,
    receivedText: item.invoiced_quantity ?? "",
    asExpected: !recordedIssue,
    issue: recordedIssue,
    showLot: Boolean(item.physical?.lot_code || item.physical?.expires_on),
    lot: item.physical?.lot_code ?? "",
    expires: item.physical?.expires_on?.slice(0, 10) ?? "",
    notes: item.physical?.notes ?? "",
  };
}

function completeDraft(item: FiscalDocumentItem, partial: Partial<LineDraft> | undefined): LineDraft {
  const base = draftFromItem(item);
  if (!partial) return base;
  const legacy = partial as Partial<LineDraft> & { received?: string; factor?: string };
  return {
    ...base,
    ...partial,
    receivedText: legacy.receivedText ?? legacy.received ?? base.receivedText,
    packageContent: legacy.packageContent ?? legacy.factor ?? base.packageContent,
    asExpected: partial.asExpected ?? base.asExpected,
    showLot: partial.showLot ?? base.showLot,
    fromName: partial.fromName ?? base.fromName,
  };
}

export function FiscalDocumentPage() {
  const { documentId } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();

  const [drafts, setDrafts] = useState<Record<string, LineDraft>>({});
  const [locationId, setLocationId] = useState("");
  const [locationName, setLocationName] = useState("");
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
        locationName?: string;
        newLocationName?: string;
      };
      if (saved.drafts) setDrafts(saved.drafts);
      if (saved.locationId) setLocationId(saved.locationId);
      if (saved.locationName || saved.newLocationName) setLocationName(saved.locationName || saved.newLocationName || "");
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
      JSON.stringify({ drafts, locationId, locationName }),
    );
  }, [documentId, drafts, locationId, locationName]);

  useEffect(() => {
    if (!document) return;
    setDrafts((current) => {
      let source = current;
      if (Object.keys(source).length === 0 && documentId) {
        try {
          const saved = JSON.parse(sessionStorage.getItem(`panne-receipt:${documentId}`) || "{}") as {
            drafts?: Record<string, Partial<LineDraft>>;
          };
          if (saved.drafts) source = saved.drafts as Record<string, LineDraft>;
        } catch {
          source = current;
        }
      }
      const next = { ...source };
      for (const item of document.items) {
        next[item.id] = completeDraft(item, next[item.id]);
      }
      return next;
    });
  }, [document, documentId]);

  useEffect(() => {
    if (locationsState.kind !== "ok" || !locationId) return;
    if (!placeLocations.some((row) => row.id === locationId)) setLocationId("");
  }, [locationsState.kind, locationId, placeLocations]);

  useEffect(() => {
    if (!locationId && placeLocations.length === 1) setLocationId(placeLocations[0].id);
  }, [locationId, placeLocations]);

  useEffect(() => {
    if (locationsState.kind !== "ok" || !document || locationName.trim()) return;
    if (placeLocations.length === 0) setLocationName(principalStockName(document.establishment_name));
  }, [locationsState.kind, document, locationName, placeLocations.length]);

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

  async function ensureIngredient(item: FiscalDocumentItem, draft: LineDraft): Promise<string> {
    if (!draft.creating) return draft.ingredientId || item.match.target_id || "";
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
    return created.data.id;
  }

  async function confirmReceipt() {
    if (!document || command.pending) return;
    const divergent = document.items.some((item) => {
      const draft = drafts[item.id];
      if (!draft) return false;
      const plan = linePlan(item, draft);
      const invoiced = parseArrived(item.invoiced_quantity ?? "", item.unit_code || "");
      return !draft.asExpected || (plan.arrived != null && invoiced != null && plan.arrived.amount !== invoiced.amount);
    });
    try {
      await command.run(`fiscal-confirm:${document.id}`, async () => {
        let destination = locationId;
        if (!destination) {
          if (!canManageStock || !document.establishment_id) {
            throw new Error("Quem administra o estoque precisa criar o local antes desta confirmação.");
          }
          const created = await api.catalogCommand<{ data: { id: string } }>("/inventory/locations", {
            body: {
              establishment_id: document.establishment_id,
              code: codeFromName(locationName),
              display_name: locationName.trim(),
              kind: "warehouse",
            },
            idempotencyKey: stepKey(`${document.id}:location`),
          });
          destination = created.data.id;
          setLocationId(destination);
        }
        for (const item of document.items) {
          const draft = drafts[item.id];
          if (!draft) throw new Error("A revisão deste item ainda não está pronta.");
          const plan = linePlan(item, draft);
          if (!plan.arrived || plan.stock == null) {
            throw new Error(`Falta completar quanto chegou de ${item.supplier_description.trim() || "um item"}.`);
          }
          const ingredientId = await ensureIngredient(item, draft);
          if (!ingredientId) throw new Error("Escolha ou crie o insumo deste item.");
          const listed = await api.listInventory<{ id: string; ingredient_id: string; unit_code: string }>(
            "/inventory/items",
          );
          let stock = listed.items.find((row) => row.ingredient_id === ingredientId);
          const requestedUnit = sameUnit(item.unit_code, draft.stockUnit)
            ? item.unit_code || draft.stockUnit
            : draft.stockUnit;
          if (!stock) {
            if (!canManageStock) {
              throw new Error("Este insumo ainda não está no estoque. Quem administra o estoque precisa concluir o cadastro.");
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
            throw new Error(`Este insumo já é controlado em ${stock.unit_code}. A revisão precisa usar essa unidade.`);
          }
          const factor = sameUnit(item.unit_code, stock.unit_code) ? "1" : decimalText(Number(draft.packageContent.replace(",", ".")));
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
              received_quantity: decimalText(plan.stock),
              unit_code: stock.unit_code,
              result: draft.asExpected ? "ok" : draft.issue,
              supplier_lot_code: draft.showLot ? draft.lot.trim() || null : null,
              expires_on: draft.showLot ? draft.expires || null : null,
              notes: draft.notes.trim() || null,
            },
            stepKey(`${item.id}:physical`),
          );
        }
        await api.confirmFiscalReceipt(
          document.id,
          { inventory_location_id: destination, accept_divergence: divergent },
          stepKey(`${document.id}:confirm`),
        );
      });
      reloadIngredients();
      reloadLocations();
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  const title = document ? fiscalDocumentTitle(document) : "Entrada fiscal";
  const gaps: ReceiptGap[] = document
    ? receiptGaps({ document, locationId, locationName, drafts })
    : [];
  const confirmBlocked = gaps.length > 0;

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
                A nota permanece salva. Ajuste só o que estiver diferente. O estoque só muda em
                Confirmar recebimento.
              </p>
              {document.establishment_name ? (
                <p>
                  <strong>Estabelecimento: </strong>
                  {document.establishment_name}. O lugar onde a compra será guardada fica dentro dele.
                </p>
              ) : null}
              {document.supplier && !document.supplier.registered ? (
                <p>
                  O emitente ainda não está no cadastro de fornecedores. Isso não impede o recebimento
                  nem cria o fornecedor sozinho.
                </p>
              ) : null}
              {document.items.length === 0 ? (
                <p>Este documento ainda não tem itens informados.</p>
              ) : (
                document.items.map((item) => {
                  const draft = drafts[item.id] ?? draftFromItem(item);
                  const hint = packageHintFromName(item.supplier_description);
                  const plan = linePlan(item, draft);
                  const needsContent = !sameUnit(item.unit_code, draft.stockUnit);
                  const movement =
                    plan.arrived == null
                      ? null
                      : movementSentence(
                          plan.arrived.amount,
                          item.unit_code,
                          draft.stockUnit,
                          draft.packageContent,
                        );
                  const currency = document.costs?.currency ?? document.currency;
                  const arrivedUnit = spokenUnit(item.unit_code, plan.arrived?.amount ?? 1);
                  return (
                    <article key={item.id} className="receipt-line">
                      <h3>{fiscalItemTitle(item)}</h3>
                      <p>{invoiceSays({ ...item, currency })}</p>
                      {item.supplier_sku ? <p className="meta">Referência do fornecedor: {item.supplier_sku}</p> : null}
                      {hint && needsContent ? (
                        <p>
                          Pista no nome do produto: {hint.amount} {hint.unit}. Isso não é um dado separado da
                          nota; confirme se for o conteúdo de cada embalagem.
                        </p>
                      ) : null}
                      {document.stock_applied ? (
                        <p>
                          Entrou {fiscalQuantityLabel(item.physical?.received_quantity, item.physical?.unit_code)}
                          {document.storage_location_label ? ` em ${document.storage_location_label}` : ""}.
                          {showCosts ? <ResultCost item={item} currency={currency} /> : null}
                        </p>
                      ) : (
                        <div className="fiscal-check-form">
                          <div id={`item-${item.id}-insumo`}>
                            {canMatch ? (
                              <>
                                <label>
                                  O que guardar
                                  <select
                                    value={draft.creating ? "new" : draft.ingredientId}
                                    disabled={command.pending}
                                    onChange={(event) => {
                                      const value = event.target.value;
                                      patchDraft(item.id, {
                                        creating: value === "new",
                                        ingredientId: value === "new" ? "" : value,
                                      });
                                    }}
                                  >
                                    <option value="new">
                                      Criar {draft.newName.trim() || item.supplier_description.trim() || "insumo novo"}
                                    </option>
                                    {ingredients.map((ingredient) => (
                                      <option key={ingredient.id} value={ingredient.id}>
                                        {ingredient.display_name}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                                {draft.creating && canCreateIngredient ? (
                                  <label>
                                    Nome do insumo
                                    <input
                                      value={draft.newName}
                                      autoComplete="off"
                                      disabled={command.pending}
                                      onChange={(event) =>
                                        patchDraft(item.id, { creating: true, newName: event.target.value })
                                      }
                                    />
                                  </label>
                                ) : null}
                              </>
                            ) : (
                              <p>Definir o insumo cabe a quem revisa a entrada. A nota continua salva.</p>
                            )}
                          </div>
                          {item.stock_unit_code ? (
                            <p>Este insumo já é controlado em {item.stock_unit_code}.</p>
                          ) : (
                            <fieldset>
                              <legend>Como controlar no estoque</legend>
                              {controlChoices(item.unit_code, hint).map((choice) => (
                                <label key={choice}>
                                  <input
                                    type="radio"
                                    name={`controle-${item.id}`}
                                    checked={selectedChoice(draft.stockUnit, item.unit_code) === choice}
                                    disabled={command.pending || !canMatch}
                                    onChange={() => {
                                      const unit = unitForChoice(choice, item.unit_code);
                                      const named =
                                        hint && !sameUnit(unit, item.unit_code) && sameUnit(hint.unit, unit)
                                          ? String(hint.amount).replace(".", ",")
                                          : "";
                                      patchDraft(item.id, {
                                        stockUnit: unit,
                                        packageContent: named,
                                        fromName: Boolean(named),
                                      });
                                    }}
                                  />{" "}
                                  {choiceLabel(choice)}
                                </label>
                              ))}
                            </fieldset>
                          )}
                          {needsContent ? (
                            <div id={`item-${item.id}-conteudo`}>
                              <label>
                                Quanto cabe em cada {spokenUnit(item.unit_code, 1)}
                                <input
                                  value={draft.packageContent}
                                  inputMode="decimal"
                                  autoComplete="off"
                                  disabled={command.pending || !canMatch}
                                  onChange={(event) =>
                                    patchDraft(item.id, { packageContent: event.target.value, fromName: false })
                                  }
                                />
                              </label>
                              <p className="meta">Em {draft.stockUnit}.</p>
                              {draft.fromName ? (
                                <p>Sugestão a partir do nome. Mude se o conteúdo for outro.</p>
                              ) : (
                                <p className="meta">A nota não informa esse conteúdo. Informe só este dado.</p>
                              )}
                              {movement ? <p>{movement}</p> : null}
                            </div>
                          ) : movement ? (
                            <p>{movement}</p>
                          ) : null}
                          <div id={`item-${item.id}-chegou`}>
                            {canCheck ? (
                              <>
                                <label>
                                  Quanto chegou?
                                  <input
                                    value={draft.receivedText}
                                    autoComplete="off"
                                    disabled={command.pending}
                                    onChange={(event) => patchDraft(item.id, { receivedText: event.target.value })}
                                  />
                                </label>
                                <p className="meta">
                                  Unidade deste campo: {arrivedUnit}. Quantidade da nota:{" "}
                                  {fiscalQuantityLabel(item.invoiced_quantity, item.unit_code)}. Este valor é o que
                                  você conferiu.
                                </p>
                                {draft.receivedText.trim() && !plan.arrived ? (
                                  <p className="error" role="alert">
                                    Use a quantidade na unidade da nota, por exemplo 1 ou 1 {item.unit_code || "UN"}.
                                  </p>
                                ) : null}
                                <fieldset>
                                  <legend>Chegou como esperado?</legend>
                                  <label>
                                    <input
                                      type="radio"
                                      name={`esperado-${item.id}`}
                                      checked={draft.asExpected}
                                      disabled={command.pending}
                                      onChange={() => patchDraft(item.id, { asExpected: true, issue: "" })}
                                    />{" "}
                                    Sim
                                  </label>
                                  <label>
                                    <input
                                      type="radio"
                                      name={`esperado-${item.id}`}
                                      checked={!draft.asExpected}
                                      disabled={command.pending}
                                      onChange={() => patchDraft(item.id, { asExpected: false })}
                                    />{" "}
                                    Não
                                  </label>
                                </fieldset>
                                {!draft.asExpected ? (
                                  <label id={`item-${item.id}-motivo`}>
                                    O que veio diferente
                                    <select
                                      value={draft.issue}
                                      disabled={command.pending}
                                      onChange={(event) => patchDraft(item.id, { issue: event.target.value })}
                                    >
                                      <option value="">Escolher…</option>
                                      {Object.entries(FISCAL_CHECK_LABEL)
                                        .filter(([code]) => code !== "ok")
                                        .map(([code, label]) => (
                                          <option key={code} value={code}>
                                            {label}
                                          </option>
                                        ))}
                                    </select>
                                  </label>
                                ) : null}
                                {!draft.asExpected &&
                                (draft.issue === "shortage" || draft.issue === "excess" || draft.issue === "missing") ? (
                                  <p>A quantidade acima é a que veio de fato.</p>
                                ) : null}
                                {draft.showLot ? (
                                  <>
                                    <label>
                                      Lote informado
                                      <input
                                        value={draft.lot}
                                        autoComplete="off"
                                        disabled={command.pending}
                                        onChange={(event) => patchDraft(item.id, { lot: event.target.value })}
                                      />
                                    </label>
                                    <label>
                                      Validade informada
                                      <input
                                        type="date"
                                        value={draft.expires}
                                        disabled={command.pending}
                                        onChange={(event) => patchDraft(item.id, { expires: event.target.value })}
                                      />
                                    </label>
                                  </>
                                ) : (
                                  <p>
                                    <button
                                      type="button"
                                      className="ghost"
                                      disabled={command.pending}
                                      onClick={() => patchDraft(item.id, { showLot: true })}
                                    >
                                      Registrar lote e validade
                                    </button>
                                  </p>
                                )}
                                <details>
                                  <summary>Registrar observação</summary>
                                  <label>
                                    Observação
                                    <textarea
                                      value={draft.notes}
                                      disabled={command.pending}
                                      onChange={(event) => patchDraft(item.id, { notes: event.target.value })}
                                    />
                                  </label>
                                </details>
                                {notesBesideExpected(draft.asExpected, draft.notes) ? (
                                  <p>{notesBesideExpected(draft.asExpected, draft.notes)}</p>
                                ) : null}
                              </>
                            ) : (
                              <p>Registrar o que chegou cabe a quem confere a entrada.</p>
                            )}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })
              )}

              <div id="local-estoque">
                <h3>Onde guardar</h3>
                <p className="meta">Toda esta nota entra no mesmo lugar.</p>
                {document.stock_applied ? (
                  <p>
                    {document.storage_location_label?.trim() ||
                      "A mercadoria já foi lançada no estoque desta entrada."}
                  </p>
                ) : !canConfirm ? (
                  <p>A escolha do lugar cabe a quem confirma o recebimento.</p>
                ) : placeLocations.length > 0 ? (
                  <label>
                    Lugar que vai receber
                    <select
                      value={locationId}
                      onChange={(event) => setLocationId(event.target.value)}
                      disabled={command.pending}
                    >
                      <option value="">Escolher o lugar…</option>
                      {placeLocations.map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.display_name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label>
                    Nome do lugar
                    <input
                      value={locationName}
                      autoComplete="off"
                      disabled={command.pending || !canManageStock}
                      onChange={(event) => setLocationName(event.target.value)}
                    />
                  </label>
                )}
                {!document.stock_applied && placeLocations.length === 0 && locationName.trim() ? (
                  <p>Ao confirmar, será criado o lugar “{locationName.trim()}”.</p>
                ) : null}
              </div>

              {!document.stock_applied && document.items.length > 0 ? (
                <div>
                  <h3>O que a confirmação vai fazer</h3>
                  <ul>
                    {document.items.map((item) => {
                      const draft = drafts[item.id] ?? draftFromItem(item);
                      const plan = linePlan(item, draft);
                      const movement =
                        plan.arrived == null
                          ? "quantidade ainda incompleta"
                          : movementSentence(
                              plan.arrived.amount,
                              item.unit_code,
                              draft.stockUnit,
                              draft.packageContent,
                            );
                      const name = draft.creating
                        ? draft.newName.trim() || item.supplier_description.trim()
                        : ingredients.find((row) => row.id === draft.ingredientId)?.display_name ||
                          item.match.target_label ||
                          "insumo escolhido";
                      const currency = document.costs?.currency ?? document.currency;
                      const stockCost = previewStockUnitCost(item.total_cost, plan.stock);
                      return (
                        <li key={item.id}>
                          {name}: {movement || "conta ainda incompleta"}.
                          {draft.creating ? " Será criado esse insumo." : ""}
                          {showCosts && item.invoice_unit_price
                            ? ` Na nota, ${fiscalMoney(item.invoice_unit_price, currency)} por ${item.unit_code || "unidade"}.`
                            : ""}
                          {showCosts && stockCost
                            ? ` No estoque, ${fiscalMoney(stockCost, currency)} por ${draft.stockUnit}.`
                            : ""}
                          {!draft.asExpected ? " A diferença fica registrada." : ""}
                        </li>
                      );
                    })}
                    <li>
                      Destino:{" "}
                      {locationId
                        ? placeLocations.find((row) => row.id === locationId)?.display_name || "lugar escolhido"
                        : locationName.trim() || "ainda sem lugar"}
                      {!locationId && locationName.trim() ? ", criado nesta confirmação." : "."}
                    </li>
                    {document.stock_policy_ready === false ? (
                      <li>Será registrada uma política inicial de estoque para poder guardar esta entrada.</li>
                    ) : null}
                  </ul>
                </div>
              ) : null}
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
                  <p className="meta">Ainda falta completar:</p>
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
              ) : null}
              {command.error ? (
                <p className="error" role="alert">
                  {command.error.message || "Não foi possível concluir a ação."}
                </p>
              ) : null}
              <p>
                {canConfirm && !document.stock_applied ? (
                  <button
                    type="button"
                    className="primary"
                    disabled={command.pending || confirmBlocked || document.items.length === 0}
                    onClick={() => void confirmReceipt()}
                  >
                    Confirmar recebimento
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
          Importe a nota, confira o que a tela já sugeriu e confirme o recebimento. Insumo e lugar
          novos, quando aparecerem no resumo, nascem nessa confirmação. O saldo só muda ali.
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
