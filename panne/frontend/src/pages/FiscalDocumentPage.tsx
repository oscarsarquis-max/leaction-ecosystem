import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Envelope, FiscalDocument, FiscalDocumentItem, IngredientPage } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDate, formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
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
  decimalText,
  linePlan,
  packageHintFromName,
  parseArrived,
  principalStockName,
  suggestControl,
} from "./receiptOperation";
import { ReceiptSheet, type LineDraft } from "./ReceiptSheet";
import { purchaseCostCaption, receiptGaps, sameUnit, type ReceiptGap } from "./receiptReview";

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
    editingName: false,
    newName: (item.supplier_description ?? "").trim(),
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
    editingName: partial.editingName ?? false,
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
        if (!locationId && (!canManageStock || !document.establishment_id)) {
          throw new Error("Quem administra o estoque precisa criar o local antes desta confirmação.");
        }
        const lines = document.items.map((item) => {
          const draft = completeDraft(item, drafts[item.id]);
          const plan = linePlan(item, draft);
          if (!plan.arrived || plan.stock == null) {
            throw new Error(`Falta completar quanto chegou de ${item.supplier_description.trim() || "um item"}.`);
          }
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
            new_ingredient_name: draft.creating ? draft.newName.trim() : null,
            stock_unit: requestedUnit,
            conversion_factor: decimalText(factorAmount),
            received_quantity: decimalText(plan.stock),
            result: draft.asExpected ? "ok" : draft.issue,
            supplier_lot_code: draft.showLot ? draft.lot.trim() || null : null,
            expires_on: draft.showLot ? draft.expires || null : null,
            notes: draft.notes.trim() || null,
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

            <ReceiptSheet
              document={document}
              title={title}
              drafts={Object.fromEntries(document.items.map((item) => [item.id, completeDraft(item, drafts[item.id])]))}
              ingredients={ingredients}
              placeLocations={placeLocations}
              locationId={locationId}
              locationName={locationName}
              editingPlace={editingPlace}
              gaps={gaps}
              showCosts={showCosts}
              pending={command.pending}
              canMatch={canMatch}
              canCheck={canCheck}
              canConfirm={canConfirm}
              canCreateIngredient={canCreateIngredient}
              confirmBlocked={confirmBlocked}
              onPatch={patchDraft}
              onLocationId={setLocationId}
              onLocationName={setLocationName}
              onEditingPlace={setEditingPlace}
              onConfirm={() => void confirmReceipt()}
            />

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
