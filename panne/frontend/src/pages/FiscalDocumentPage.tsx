import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { CatalogItem, Envelope, FiscalDocument, FiscalDocumentItem, IngredientPage } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDate, formatDateTime } from "../format";
import { errorMessage } from "../api/errors";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  fiscalAttachmentLabel,
  fiscalDocumentTitle,
  fiscalItemTitle,
  fiscalMoney,
  fiscalOriginLabel,
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
  canCaptureFiscalDocument,
  canCheckFiscalItem,
  canConfirmFiscalReceipt,
  canMatchFiscalItem,
  canReadFiscalPrice,
} from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";
import {
  canonicalUnit,
  decimalText,
  linePlan,
  parseArrived,
  principalStockName,
  suggestControl,
} from "./receiptOperation";
import { DraftItemsSheet, EMPTY_DRAFT_LINE, type DraftLine } from "./DraftItemsSheet";
import { ReceiptSheet, type LineDraft } from "./ReceiptSheet";
import { purchaseCostCaption, receiptGaps, reviewGaps, sameUnit, type ReceiptGap } from "./receiptReview";

type StorageLocation = {
  id: string;
  display_name: string;
  status: string;
  establishment_id?: string;
};

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
  const persistedContent = item.package_content_quantity?.trim() || "";
  const persistedUnit = item.package_content_unit?.trim() || item.converted_unit_code || "";
  const stock = suggestControl({
    invoiceUnit: item.unit_code,
    existingUnit: item.stock_unit_code || persistedUnit || null,
    hint: null,
  });
  const reliable =
    (item.match.status === "matched" || item.match.status === "suggested") && Boolean(item.match.target_id);
  const recordedIssue = item.physical?.result && item.physical.result !== "ok" ? item.physical.result : "";
  const review = item.review;
  return {
    ingredientId: review?.suggested_ingredient_id || (reliable ? (item.match.target_id ?? "") : ""),
    creating: false,
    editingName: false,
    newName: review?.suggested_ingredient_name || (item.supplier_description ?? "").trim(),
    stockUnit: stock.unit,
    packageContent: persistedContent || stock.content || "",
    fromName: false,
    receivedText: review?.reviewed_quantity || item.invoiced_quantity || "",
    asExpected: review?.as_expected ?? !recordedIssue,
    issue: review?.issue || recordedIssue,
    showLot: Boolean(item.physical?.lot_code || item.physical?.expires_on || (item.lots && item.lots.length > 0)),
    lot: item.physical?.lot_code ?? "",
    expires: item.physical?.expires_on?.slice(0, 10) ?? "",
    lots:
      item.lots && item.lots.length > 0
        ? item.lots.map((row, index) => ({
            key: `saved-${item.id}-${index}`,
            quantity: row.quantity ?? "",
            lot: row.lot_code ?? "",
            expires: row.expires_on?.slice(0, 10) ?? "",
            expiryUninformed: Boolean(row.expiry_uninformed),
          }))
        : [
            {
              key: `lot-${item.id}`,
              quantity: review?.reviewed_quantity || item.invoiced_quantity || "",
              lot: item.physical?.lot_code ?? "",
              expires: item.physical?.expires_on?.slice(0, 10) ?? "",
              expiryUninformed: Boolean(item.physical?.expiry_uninformed),
            },
          ],
    notes: review?.notes || item.physical?.notes || "",
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
    editingName: partial.editingName ?? false,
    showLot: partial.showLot ?? base.showLot,
    lots: partial.lots ?? base.lots,
    fromName: partial.fromName ?? base.fromName,
  };
}

async function loadIngredientCatalog(api: {
  listIngredients: (query: Record<string, string>) => Promise<IngredientPage>;
}): Promise<IngredientPage> {
  const limit = 50;
  const first = await api.listIngredients({ limit: String(limit), offset: "0" });
  const items = [...first.items];
  let offset = items.length;
  while (offset < first.total && offset < 200) {
    const page = await api.listIngredients({ limit: String(limit), offset: String(offset) });
    if (page.items.length === 0) break;
    items.push(...page.items);
    offset += page.items.length;
  }
  return { ...first, items };
}

export function FiscalDocumentPage() {
  const { documentId } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();

  const [drafts, setDrafts] = useState<Record<string, LineDraft>>({});
  const [itemLines, setItemLines] = useState<DraftLine[]>([]);
  const [itemErrors, setItemErrors] = useState<Partial<Record<string, string>>>({});
  const [occupiedCodeError, setOccupiedCodeError] = useState<string | null>(null);
  const [locationId, setLocationId] = useState("");
  const [locationName, setLocationName] = useState("");
  const [editingPlace, setEditingPlace] = useState(false);
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
  const canEditItems = canCaptureFiscalDocument(hasPermission) && Boolean(document?.items_editable);
  // A API declara se este perfil recebeu os campos de custo; a permissão só evita pedir à toa.
  const showCosts = document ? document.cost_access : canReadFiscalPrice(hasPermission);

  const canCreateIngredient = hasPermission("ingredient.create");
  const canManageStock = hasPermission("inventory.item.manage");

  const { state: ingredientsState, reload: reloadIngredients } = useAsyncResource<IngredientPage>(
    () => loadIngredientCatalog(api),
    [api, orgId],
    Boolean(orgId) &&
      (canMatch || canCheck || canCaptureFiscalDocument(hasPermission)) &&
      hasPermission("ingredient.read"),
  );
  const ingredients = ingredientsState.kind === "ok" ? ingredientsState.data.items : [];
  const [ingredientQuery, setIngredientQuery] = useState("");
  const searchIngredients = useCallback((query: string) => {
    setIngredientQuery(query);
  }, []);
  const { state: ingredientSearchState } = useAsyncResource<IngredientPage>(
    () => api.listIngredients({ q: ingredientQuery.trim(), limit: "12", offset: "0" }),
    [api, orgId, ingredientQuery],
    Boolean(orgId) && hasPermission("ingredient.read") && ingredientQuery.trim().length >= 1,
  );
  const ingredientResults = ingredientSearchState.kind === "ok" ? ingredientSearchState.data.items : [];
  const ingredientSearchStatus =
    ingredientQuery.trim().length < 1
      ? "idle"
      : ingredientSearchState.kind === "carregando"
        ? "buscando"
        : ingredientSearchState.kind === "erro"
          ? "erro"
          : "ok";
  const ingredientSearchError =
    ingredientSearchState.kind === "erro"
      ? errorMessage(ingredientSearchState.error)
      : "";
  const { state: unitsState } = useAsyncResource<{ data: CatalogItem[] }>(
    () => api.getCatalogUnits(),
    [api, orgId],
    Boolean(orgId) && canCreateIngredient && hasPermission("ingredient.read"),
  );
  const units = unitsState.kind === "ok" ? unitsState.data.data : [];

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
    if (!document) return;
    setItemLines(
      document.items.length
        ? document.items.map((item) => ({
            key: item.id,
            description: item.supplier_description,
            quantity: item.invoiced_quantity ?? "",
            unit_code: item.unit_code || "",
            unit_price: item.invoice_unit_price ?? item.unit_cost ?? "",
            package_content_quantity: item.package_content_quantity ?? "",
            package_content_unit: item.package_content_unit ?? "",
            ingredient_id:
              item.match.target_kind === "ingredient" && item.match.target_id ? item.match.target_id : "",
            ingredient_label: item.match.target_label ?? "",
            ingredient_code: "",
            pendingNew: null,
          }))
        : [],
    );
    setItemErrors({});
  }, [document?.id, document?.row_version]);

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

  const loadSuggestedCode = useCallback(() => api.getSuggestedIngredientCode(), [api]);

  function patchDraft(itemId: string, patch: Partial<LineDraft>) {
    setDrafts((current) => {
      const base = current[itemId];
      if (!base) return current;
      const next = { ...base, ...patch };
      if (patch.receivedText != null && next.lots.length === 1) {
        next.lots = [{ ...next.lots[0], quantity: patch.receivedText }];
      }
      return { ...current, [itemId]: next };
    });
  }

  function patchItemLine(key: string, patch: Partial<DraftLine>) {
    setItemLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
    setItemErrors({});
  }

  async function saveItems() {
    if (!document || command.pending || !canEditItems) return;
    const usable = itemLines.filter((line) => line.description.trim() && line.quantity.trim());
    const errors: Partial<Record<string, string>> = {};
    if (!usable.length) errors.items = "Informe ao menos um item com descrição e quantidade.";
    for (const line of itemLines) {
      const started = Boolean(line.description.trim() || line.quantity.trim() || line.unit_code.trim());
      if (line.description.trim() && !line.quantity.trim()) {
        errors[`qty-${line.key}`] = "Informe quantos foram comprados.";
      }
      if (line.quantity.trim() && Number(line.quantity.replace(",", ".")) <= 0) {
        errors[`qty-${line.key}`] = "Informe uma quantidade maior que zero.";
      }
      if (started && !line.unit_code.trim()) {
        errors[`unit-${line.key}`] = "Informe a unidade de compra.";
      }
      const pack = line.unit_code.trim().toLocaleLowerCase("pt-BR");
      const needsContent = pack === "pacote" || pack === "caixa";
      if (needsContent && !line.package_content_quantity.trim()) {
        errors[`content-${line.key}`] = "Informe o conteúdo de cada embalagem.";
      }
      if (line.package_content_quantity.trim() && !line.package_content_unit.trim()) {
        errors[`content-${line.key}`] = "Informe a unidade do conteúdo.";
      }
    }
    setItemErrors(errors);
    if (Object.keys(errors).length) return;
    setOccupiedCodeError(null);
    try {
      await command.run(`fiscal-items:${document.id}:${document.row_version}`, (key) =>
        api.replaceFiscalItems(
          document.id,
          {
            expected_row_version: document.row_version,
            items: usable.map((line) => ({
              description: line.description.trim(),
              quantity: line.quantity.trim(),
              unit_code: line.unit_code.trim() || null,
              unit_price: line.unit_price.trim() || null,
              package_content_quantity: line.package_content_quantity.trim() || null,
              package_content_unit: line.package_content_unit.trim() || null,
              ingredient_id: line.pendingNew ? null : line.ingredient_id || null,
              new_ingredient: line.pendingNew,
            })),
          },
          key,
        ),
      );
      reload();
    } catch (caught) {
      const text = errorMessage(caught);
      if (/código interno já|já existe um registro com este código/i.test(text)) {
        setOccupiedCodeError(text);
      }
    }
  }

  async function saveReview() {
    if (!document || command.pending) return;
    try {
      await command.run(`fiscal-review:${document.id}`, async () => {
        const lines = document.items.map((item) => {
          const draft = completeDraft(item, drafts[item.id]);
          const arrived = parseArrived(draft.receivedText, item.unit_code || "");
          if (!arrived) {
            throw new Error(`Falta a quantidade conferida de ${item.supplier_description.trim() || "um item"}.`);
          }
          const name = draft.creating
            ? draft.newName.trim()
            : ingredients.find((row) => row.id === draft.ingredientId)?.display_name ||
              item.match.target_label ||
              draft.newName.trim() ||
              item.supplier_description.trim();
          if (!name) throw new Error("Escolha ou nomeie o insumo deste item.");
          return {
            item_id: item.id,
            suggested_ingredient_name: name,
            suggested_ingredient_id: draft.creating ? null : draft.ingredientId || item.match.target_id || null,
            reviewed_quantity: decimalText(arrived.amount),
            as_expected: draft.asExpected,
            issue: draft.asExpected ? null : draft.issue || null,
            notes: draft.notes.trim() || null,
          };
        });
        await api.saveFiscalReview(
          document.id,
          { expected_row_version: document.row_version, lines },
          stepKey(`${document.id}:review:${document.row_version}`),
        );
      });
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  async function confirmReceipt() {
    if (!document || command.pending) return;
    const divergent = document.items.some((item) => {
      const draft = completeDraft(item, drafts[item.id]);
      const plan = linePlan(item, draft);
      const invoiced = parseArrived(item.invoiced_quantity ?? "", item.unit_code || "");
      return !draft.asExpected || (plan.arrived != null && invoiced != null && plan.arrived.amount !== invoiced.amount);
    });
    try {
      await command.run(`fiscal-confirm:${document.id}`, async () => {
        if (!document.review_saved && document.status !== "reviewed") {
          throw new Error("Grave a nota revisada antes de lançar o estoque.");
        }
        if (!locationId && (!canManageStock || !document.establishment_id)) {
          throw new Error("Quem administra o estoque precisa criar o local antes desta confirmação.");
        }
        const lines = document.items.map((item) => {
          const draft = completeDraft(item, drafts[item.id]);
          const plan = linePlan(item, draft);
          if (!plan.arrived || plan.stock == null) {
            throw new Error(`Falta completar quanto chegou de ${item.supplier_description.trim() || "um item"}.`);
          }
          const stockQuantity = plan.stock;
          if (draft.creating && !canCreateIngredient) {
            throw new Error("Seu papel não cria insumos.");
          }
          const ingredientId = draft.creating ? "" : draft.ingredientId || item.match.target_id || "";
          if (!draft.creating && !ingredientId) throw new Error("Escolha ou crie o insumo deste item.");
          if (draft.creating && !draft.newName.trim()) throw new Error("Escolha ou crie o insumo deste item.");
          const requestedUnit = sameUnit(item.unit_code, draft.stockUnit)
            ? item.unit_code || draft.stockUnit
            : draft.stockUnit;
          const factorAmount = sameUnit(item.unit_code, requestedUnit)
            ? 1
            : parseArrived(draft.packageContent, requestedUnit)?.amount;
          if (factorAmount == null) {
            throw new Error(`Falta o conteúdo de cada embalagem de ${item.supplier_description.trim() || "um item"}.`);
          }
          return {
            item_id: item.id,
            ingredient_id: draft.creating ? null : ingredientId,
            create_ingredient: draft.creating,
            new_ingredient_name: draft.creating ? draft.newName.trim() : null,
            stock_unit: canonicalUnit(requestedUnit),
            conversion_factor: decimalText(factorAmount),
            received_quantity: decimalText(stockQuantity),
            result: draft.asExpected ? "ok" : draft.issue,
            supplier_lot_code: draft.lots[0]?.lot.trim() || null,
            expires_on: draft.lots[0]?.expiryUninformed ? null : draft.lots[0]?.expires || null,
            notes: draft.notes.trim() || null,
            lots: draft.lots.map((lot) => ({
              quantity: lot.quantity.trim() || decimalText(stockQuantity),
              supplier_lot_code: lot.lot.trim() || null,
              expires_on: lot.expiryUninformed ? null : lot.expires || null,
              expiry_uninformed: lot.expiryUninformed,
            })),
          };
        });
        await api.receiveFiscalReceipt(
          document.id,
          {
            inventory_location_id: locationId || null,
            new_location_name: locationId ? null : locationName.trim(),
            accept_divergence: divergent,
            lines,
          },
          stepKey(`${document.id}:receive`),
        );
      });
      reloadIngredients();
      reloadLocations();
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  const canSave = canMatch || canCheck;
  const reviewSaved = Boolean(document?.review_saved || document?.status === "reviewed");
  const title = document ? fiscalDocumentTitle(document) : "Entrada fiscal";
  const completedDrafts = document
    ? Object.fromEntries(document.items.map((item) => [item.id, completeDraft(item, drafts[item.id])]))
    : {};
  const noteGaps: ReceiptGap[] = document ? reviewGaps({ document, drafts: completedDrafts }) : [];
  const gaps: ReceiptGap[] = document
    ? receiptGaps({ document, locationId, locationName, drafts: completedDrafts })
    : [];
  const confirmBlocked = !reviewSaved || gaps.length > 0;
  const saveBlocked = noteGaps.length > 0;
  const actionGaps = reviewSaved ? gaps : noteGaps;

  const missingItems = Boolean(document && document.items.length === 0);
  const missingMatches = Boolean(
    document && document.items.some((item) => !item.match.target_id),
  );
  const nextSentence = !document
    ? undefined
    : document.stock_applied
      ? fiscalStockLabel(document.stock_applied, document.stock_summary)
      : missingItems
        ? "Inclua os itens nesta nota. O estoque ainda não será lançado."
        : missingMatches
          ? "Associe o ingrediente nesta mesma nota. O estoque continua bloqueado."
        : !reviewSaved
          ? saveBlocked
            ? noteGaps[0]?.text
            : "Grave a nota revisada. O estoque ainda não será lançado."
          : gaps.length > 0
            ? gaps[0].text
            : canConfirm
              ? "Nota gravada · estoque pendente. Confirme a entrada no estoque quando decidir."
              : "A entrada no estoque cabe a quem pode atualizar o estoque.";

  return (
    <div className="receipt-page">
      <ListLive
        kind={state.kind}
        entityLabel={title}
        status={document ? fiscalStatusLabel(document.status) : undefined}
        next={nextSentence}
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
              {document.stock_applied
                ? "O estoque desta nota já foi atualizado."
                : reviewSaved
                  ? "Nota gravada · estoque pendente."
                  : "Rascunho salvo · estoque ainda não atualizado."}
            </p>
            <div className="receipt-meta">
              <div>
                <span className="meta">Fornecedor</span>
                <strong>
                  {document.supplier?.id && hasPermission("supplier.read") ? (
                    <Link to={`/componentes/fornecedores/${document.supplier.id}`}>
                      {fiscalSupplierLabel(document.supplier)}
                    </Link>
                  ) : (
                    fiscalSupplierLabel(document.supplier)
                  )}
                </strong>
              </div>
              <div>
                <span className="meta">Emissão</span>
                <strong>{formatDate(document.issued_on)}</strong>
              </div>
              {showCosts ? (
                <div>
                  <span className="meta">Total da nota</span>
                  <strong>
                    {fiscalMoney(
                      document.costs?.document_total ?? document.document_total,
                      document.costs?.currency ?? document.currency,
                    )}
                  </strong>
                </div>
              ) : null}
            </div>

            {document.items_editable || missingItems ? (
              <DraftItemsSheet
                lines={itemLines}
                errors={itemErrors}
                pending={command.pending}
                canEdit={canEditItems}
                canCreateIngredient={canCreateIngredient}
                units={units}
                results={ingredientResults}
                similar={ingredientResults}
                searchStatus={ingredientSearchStatus}
                searchError={ingredientSearchError}
                onChange={patchItemLine}
                onAdd={() =>
                  setItemLines((current) => [
                    ...current,
                    { ...EMPTY_DRAFT_LINE, key: crypto.randomUUID() },
                  ])
                }
                onRemove={(key) => setItemLines((current) => current.filter((line) => line.key !== key))}
                onSave={() => void saveItems()}
                onSearchIngredients={searchIngredients}
                loadSuggestedCode={loadSuggestedCode}
                occupiedError={occupiedCodeError}
              />
            ) : null}

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

            <details className="receipt-fold">
              <summary>Documento, fornecedor e anexos</summary>
            <section>
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

            <section>
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
            </details>

            <ReceiptSheet
              document={document}
              title={title}
              drafts={completedDrafts}
              ingredients={ingredients}
              placeLocations={placeLocations}
              locationId={locationId}
              locationName={locationName}
              editingPlace={editingPlace}
              gaps={gaps}
              noteGaps={noteGaps}
              showCosts={showCosts}
              pending={command.pending}
              canCheck={canCheck}
              canSave={canSave && !missingItems}
              canConfirm={canConfirm && !missingItems}
              canCreateIngredient={canCreateIngredient}
              confirmBlocked={confirmBlocked || missingItems || missingMatches}
              saveBlocked={saveBlocked || missingItems}
              reviewSaved={reviewSaved}
              onPatch={patchDraft}
              onLocationId={setLocationId}
              onLocationName={setLocationName}
              onEditingPlace={setEditingPlace}
              onSave={() => void saveReview()}
              onConfirm={() => void confirmReceipt()}
            />

            {showCosts ? (
              <details className="receipt-fold">
                <summary>Quanto custou</summary>
              <section>
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
                  atualizado na entrada no estoque.
                </p>
              </section>
              </details>
            ) : (
              <details className="receipt-fold">
                <summary>Quanto custou</summary>
                <section>
                  <h2>Quanto custou</h2>
                  <p>Valores do documento ficam ocultos para o seu papel.</p>
                </section>
              </details>
            )}

            <details className="receipt-fold">
              <summary>Estoque desta entrada</summary>
            <section>
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
            </details>

            <section className="receipt-next">
              <h2>Próxima ação</h2>
              <p>{nextSentence}</p>
              {actionGaps.length > 0 ? (
                <>
                  <p className="meta">Ainda falta completar:</p>
                  <ul>
                    {actionGaps.map((gap) => (
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
    </div>
  );
}

/**
 * O contrato ainda não devolve o nome do item ligado. Enquanto isso a tela diz o tipo do
 * vínculo em palavras, em vez de mostrar o identificador técnico.
 */
