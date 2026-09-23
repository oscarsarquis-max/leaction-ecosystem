import type { FiscalDocument, FiscalDocumentItem } from "../api/types";
import {
  FISCAL_CHECK_LABEL,
  fiscalMoney,
  fiscalQuantityLabel,
} from "../language/fiscal";
import {
  choiceLabel,
  controlChoices,
  invoiceSays,
  linePlan,
  movementSentence,
  notesBesideExpected,
  packageHintFromName,
  previewStockUnitCost,
  selectedChoice,
  unitForChoice,
} from "./receiptOperation";
import { purchaseCostCaption, type ReceiptGap, sameUnit } from "./receiptReview";

export type LineDraft = {
  ingredientId: string;
  creating: boolean;
  newName: string;
  editingName: boolean;
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

type Place = { id: string; display_name: string };
type IngredientOption = { id: string; display_name: string };

function fieldGap(gaps: ReceiptGap[], anchor: string): string | null {
  return gaps.find((gap) => gap.anchor === anchor)?.text ?? null;
}

function ingredientName(item: FiscalDocumentItem, draft: LineDraft, ingredients: IngredientOption[]): string {
  if (draft.creating) return draft.newName.trim() || item.supplier_description.trim() || "Insumo";
  return (
    ingredients.find((row) => row.id === draft.ingredientId)?.display_name ||
    item.match.target_label ||
    "Insumo escolhido"
  );
}

export function ReceiptSheet({
  document,
  title,
  drafts,
  ingredients,
  placeLocations,
  locationId,
  locationName,
  editingPlace,
  gaps,
  showCosts,
  pending,
  canMatch,
  canCheck,
  canConfirm,
  canCreateIngredient,
  confirmBlocked,
  onPatch,
  onLocationId,
  onLocationName,
  onEditingPlace,
  onConfirm,
}: {
  document: FiscalDocument;
  title: string;
  drafts: Record<string, LineDraft>;
  ingredients: IngredientOption[];
  placeLocations: Place[];
  locationId: string;
  locationName: string;
  editingPlace: boolean;
  gaps: ReceiptGap[];
  showCosts: boolean;
  pending: boolean;
  canMatch: boolean;
  canCheck: boolean;
  canConfirm: boolean;
  canCreateIngredient: boolean;
  confirmBlocked: boolean;
  onPatch: (itemId: string, patch: Partial<LineDraft>) => void;
  onLocationId: (value: string) => void;
  onLocationName: (value: string) => void;
  onEditingPlace: (value: boolean) => void;
  onConfirm: () => void;
}) {
  const itemCount = document.items.length;
  const placeLabel = locationId
    ? placeLocations.find((row) => row.id === locationId)?.display_name || "Lugar escolhido"
    : locationName.trim();
  const newPlace = !locationId && Boolean(locationName.trim());
  const choosePlace = placeLocations.length > 1 && !locationId;

  return (
    <section className="panel receipt-sheet" aria-labelledby="revisao-entrada">
      <h2 id="revisao-entrada">Revisar recebimento</h2>
      <p className="meta">
        {title} · {itemCount === 1 ? "1 item" : `${itemCount} itens`}
      </p>
      <p className="meta">A nota permanece salva. O estoque só muda em Confirmar recebimento.</p>
      {document.supplier && !document.supplier.registered ? (
        <p>O emitente ainda não está no cadastro. Isso não impede o recebimento nem cria o fornecedor.</p>
      ) : null}
      {document.items.length === 0 ? <p>Este documento ainda não tem itens informados.</p> : null}

      {document.items.map((item) => {
        const draft = drafts[item.id];
        if (!draft) return null;
        const hint = packageHintFromName(item.supplier_description);
        const plan = linePlan(item, draft);
        const needsContent = !sameUnit(item.unit_code, draft.stockUnit);
        const movement =
          plan.arrived == null
            ? null
            : movementSentence(plan.arrived.amount, item.unit_code, draft.stockUnit, draft.packageContent);
        const currency = document.costs?.currency ?? document.currency;
        const name = ingredientName(item, draft, ingredients);
        const quantityError = draft.receivedText.trim() && !plan.arrived;
        const arrivedTyped = /[A-Za-zÀ-ÿ]/.test(draft.receivedText);
        const contentTyped = /[A-Za-zÀ-ÿ]/.test(draft.packageContent);
        const stockPreview = previewStockUnitCost(item.total_cost, plan.stock);
        const cost = purchaseCostCaption({
          invoiceUnitPrice: item.invoice_unit_price,
          invoiceUnit: item.unit_code,
          stockUnitCost: showCosts ? stockPreview : null,
          stockUnit: draft.stockUnit,
          currency,
        });
        const insumoGap = fieldGap(gaps, `item-${item.id}-insumo`);
        const contentGap = fieldGap(gaps, `item-${item.id}-conteudo`);
        const reasonGap = fieldGap(gaps, `item-${item.id}-motivo`);
        const description = item.supplier_description.trim();
        const showNameField = draft.editingName && draft.creating;
        const showIngredientList = draft.editingName && !draft.creating;

        return (
          <article key={item.id} className="receipt-line">
            <div className="receipt-invoice">
              <div>
                <span className="receipt-tag">Na nota</span>
                <strong>
                  {description || "Item sem descrição"}
                  {item.invoiced_quantity
                    ? ` · ${fiscalQuantityLabel(item.invoiced_quantity, item.unit_code)}`
                    : ""}
                </strong>
                <p className="meta">{invoiceSays({ ...item, currency })}</p>
                {item.supplier_sku ? <p className="meta">Referência do fornecedor: {item.supplier_sku}</p> : null}
              </div>
              {showCosts && (item.total_cost || item.invoice_unit_price) ? (
                <div>
                  <span className="receipt-tag">Valor</span>
                  <strong>{fiscalMoney(item.total_cost || item.invoice_unit_price, currency)}</strong>
                </div>
              ) : null}
            </div>

            {document.stock_applied ? (
              <p>
                Entrou {fiscalQuantityLabel(item.physical?.received_quantity, item.physical?.unit_code)}
                {document.storage_location_label ? ` em ${document.storage_location_label}` : ""}.
                {showCosts && cost.note ? ` Na nota, ${cost.note}.` : ""}
                {showCosts && cost.stock ? ` No estoque, ${cost.stock}.` : ""}
              </p>
            ) : (
              <>
                <section className="receipt-section" id={`item-${item.id}-insumo`}>
                  <h3>Qual insumo entrou?</h3>
                  {canMatch ? (
                    <>
                      <div className="receipt-suggestion">
                        <span className="receipt-tag">
                          {draft.creating ? "Sugestão da Panne · novo insumo" : "Insumo já cadastrado"}
                        </span>
                        {showNameField ? null : <strong>{name}</strong>}
                        <p className="meta">
                          {draft.creating
                            ? "Será cadastrado ao confirmar. A descrição da nota não muda."
                            : "Este insumo já existe. Você pode escolher outro."}
                        </p>
                        {draft.creating && !canCreateIngredient ? (
                          <p>Cadastrar este insumo cabe a quem pode incluir insumos.</p>
                        ) : null}
                        <button
                          type="button"
                          className="ghost"
                          disabled={pending}
                          onClick={() => {
                            const next = !draft.editingName;
                            onPatch(item.id, { editingName: next });
                            if (next) window.setTimeout(() => focusAnchor(`item-${item.id}-insumo`), 0);
                          }}
                        >
                          {draft.editingName ? "Concluir" : "Alterar"}
                        </button>
                      </div>
                      {showNameField ? (
                        <label className="receipt-field">
                          <span>Nome do insumo</span>
                          <input
                            value={draft.newName}
                            autoComplete="off"
                            disabled={pending}
                            aria-invalid={Boolean(insumoGap)}
                            onChange={(event) => onPatch(item.id, { creating: true, newName: event.target.value })}
                          />
                        </label>
                      ) : null}
                      {showNameField && ingredients.length > 0 ? (
                        <button
                          type="button"
                          className="ghost"
                          disabled={pending}
                          onClick={() => onPatch(item.id, { creating: false, editingName: true })}
                        >
                          Escolher um já cadastrado
                        </button>
                      ) : null}
                      {showIngredientList ? (
                        <label className="receipt-field">
                          <span>Insumo já cadastrado</span>
                          <select
                            value={draft.ingredientId}
                            disabled={pending}
                            onChange={(event) => {
                              const value = event.target.value;
                              if (value === "new") {
                                onPatch(item.id, {
                                  creating: true,
                                  editingName: true,
                                  ingredientId: "",
                                  newName: draft.newName.trim() || item.supplier_description.trim(),
                                });
                                return;
                              }
                              onPatch(item.id, { creating: false, ingredientId: value });
                            }}
                          >
                            <option value="">Escolher…</option>
                            {canCreateIngredient ? <option value="new">Cadastrar com outro nome</option> : null}
                            {ingredients.map((ingredient) => (
                              <option key={ingredient.id} value={ingredient.id}>
                                {ingredient.display_name}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : null}
                      {insumoGap ? (
                        <p className="error" role="alert">
                          {insumoGap}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <p>Definir o insumo cabe a quem revisa a entrada. A nota continua salva.</p>
                  )}
                </section>

                <section className="receipt-section">
                  <h3>Quanto chegou?</h3>
                  <div className="receipt-grid">
                    <div id={`item-${item.id}-chegou`}>
                      {canCheck ? (
                        <label className="receipt-field">
                          <span>Quantidade recebida</span>
                          <span className="receipt-affix">
                            <input
                              value={draft.receivedText}
                              autoComplete="off"
                              disabled={pending}
                              aria-label="Quantidade recebida"
                              aria-invalid={Boolean(quantityError)}
                              aria-describedby={quantityError ? `item-${item.id}-chegou-erro` : `item-${item.id}-unidade`}
                              onChange={(event) => onPatch(item.id, { receivedText: event.target.value })}
                            />
                            {arrivedTyped ? null : (
                              <span className="receipt-affix__unit" id={`item-${item.id}-unidade`}>
                                {item.unit_code || "UN"}
                              </span>
                            )}
                          </span>
                        </label>
                      ) : (
                        <p>Registrar o que chegou cabe a quem confere a entrada.</p>
                      )}
                      {quantityError ? (
                        <p className="error" id={`item-${item.id}-chegou-erro`} role="alert">
                          Use a quantidade na unidade da nota, por exemplo 1 ou 1 {item.unit_code || "UN"}.
                        </p>
                      ) : null}
                    </div>
                    {item.stock_unit_code ? (
                      <p>Este insumo já é controlado em {item.stock_unit_code}.</p>
                    ) : (
                      <div>
                        <span className="receipt-field-label" id={`controle-${item.id}`}>
                          Como controlar no estoque
                        </span>
                        <div
                          className="receipt-choices receipt-choices--three"
                          role="radiogroup"
                          aria-labelledby={`controle-${item.id}`}
                        >
                          {controlChoices(item.unit_code, hint).map((choice) => (
                            <label key={choice} className="receipt-choice">
                              <input
                                type="radio"
                                name={`controle-${item.id}`}
                                checked={selectedChoice(draft.stockUnit, item.unit_code) === choice}
                                disabled={pending || !canMatch}
                                onChange={() => {
                                  const unit = unitForChoice(choice, item.unit_code);
                                  const named =
                                    hint && !sameUnit(unit, item.unit_code) && sameUnit(hint.unit, unit)
                                      ? String(hint.amount).replace(".", ",")
                                      : "";
                                  onPatch(item.id, {
                                    stockUnit: unit,
                                    packageContent: named,
                                    fromName: Boolean(named),
                                  });
                                }}
                              />
                              {choiceLabel(choice)}
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  {needsContent ? (
                    <div id={`item-${item.id}-conteudo`}>
                      <label className="receipt-field">
                        <span>Conteúdo de cada embalagem</span>
                        <span className="receipt-affix">
                          <input
                            value={draft.packageContent}
                            inputMode="decimal"
                            autoComplete="off"
                            disabled={pending || !canMatch}
                            aria-label="Conteúdo de cada embalagem"
                            aria-invalid={Boolean(contentGap)}
                            onChange={(event) => onPatch(item.id, { packageContent: event.target.value, fromName: false })}
                          />
                          {contentTyped ? null : <span className="receipt-affix__unit">{draft.stockUnit}</span>}
                        </span>
                      </label>
                      {draft.fromName && hint ? (
                        <p className="meta">
                          Pista no nome do produto: {hint.amount} {hint.unit}. Isso não é um dado separado da nota;
                          confirme se for o conteúdo de cada embalagem.
                        </p>
                      ) : (
                        <p className="meta">A nota não informa esse conteúdo. Informe só este dado.</p>
                      )}
                      {contentGap ? (
                        <p className="error" role="alert">
                          {contentGap}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                  {movement || (showCosts && (cost.note || cost.stock)) ? (
                    <p className="receipt-calc" aria-live="polite">
                      {[
                        movement,
                        showCosts && cost.note ? `${cost.note} na nota` : null,
                        showCosts && cost.stock ? `${cost.stock} no estoque` : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  ) : null}
                </section>

                {canCheck ? (
                  <section className="receipt-section">
                    <h3>Chegou como esperado?</h3>
                    <div className="receipt-choices receipt-choices--pair" role="radiogroup" aria-label="Chegou como esperado?">
                      <label className="receipt-choice">
                        <input
                          type="radio"
                          name={`esperado-${item.id}`}
                          checked={draft.asExpected}
                          disabled={pending}
                          onChange={() => onPatch(item.id, { asExpected: true, issue: "" })}
                        />
                        Sim
                      </label>
                      <label className="receipt-choice">
                        <input
                          type="radio"
                          name={`esperado-${item.id}`}
                          checked={!draft.asExpected}
                          disabled={pending}
                          onChange={() => onPatch(item.id, { asExpected: false })}
                        />
                        Não
                      </label>
                    </div>
                    {!draft.asExpected ? (
                      <label className="receipt-field" id={`item-${item.id}-motivo`}>
                        <span>O que houve?</span>
                        <select
                          value={draft.issue}
                          disabled={pending}
                          aria-invalid={Boolean(reasonGap)}
                          onChange={(event) => onPatch(item.id, { issue: event.target.value })}
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
                    {reasonGap ? (
                      <p className="error" role="alert">
                        {reasonGap}
                      </p>
                    ) : null}
                    {!draft.asExpected &&
                    (draft.issue === "shortage" || draft.issue === "excess" || draft.issue === "missing") ? (
                      <p className="meta">A quantidade acima é a que veio de fato.</p>
                    ) : null}
                    <details className="receipt-optional">
                      <summary>Lote, validade ou observação</summary>
                      <div className="receipt-grid">
                        <label className="receipt-field">
                          <span>Lote, se houver</span>
                          <input
                            value={draft.lot}
                            autoComplete="off"
                            disabled={pending}
                            onChange={(event) => onPatch(item.id, { lot: event.target.value, showLot: true })}
                          />
                        </label>
                        <label className="receipt-field">
                          <span>Validade, se houver</span>
                          <input
                            type="date"
                            value={draft.expires}
                            disabled={pending}
                            onChange={(event) => onPatch(item.id, { expires: event.target.value, showLot: true })}
                          />
                        </label>
                      </div>
                      <label className="receipt-field">
                        <span>Observação</span>
                        <textarea
                          value={draft.notes}
                          disabled={pending}
                          onChange={(event) => onPatch(item.id, { notes: event.target.value })}
                        />
                      </label>
                    </details>
                    {notesBesideExpected(draft.asExpected, draft.notes) ? (
                      <p className="meta">{notesBesideExpected(draft.asExpected, draft.notes)}</p>
                    ) : null}
                  </section>
                ) : null}
              </>
            )}
          </article>
        );
      })}

      <section className="receipt-section" id="local-estoque">
        <h3>Onde guardar?</h3>
        {document.stock_applied ? (
          <p>{document.storage_location_label?.trim() || "A mercadoria já foi lançada no estoque desta entrada."}</p>
        ) : !canConfirm ? (
          <p>A escolha do lugar cabe a quem confirma o recebimento.</p>
        ) : (
          <>
            <div className="receipt-suggestion">
              {choosePlace && !editingPlace ? null : editingPlace && !locationId && placeLocations.length === 0 ? null : (
                <strong>{placeLabel || "Escolha o lugar desta nota"}</strong>
              )}
              <p className="meta">
                {newPlace
                  ? "Novo local sugerido; será criado na confirmação."
                  : choosePlace
                    ? "Escolha um lugar deste estabelecimento. Toda a nota entra no mesmo lugar."
                    : "Toda esta nota entra no mesmo lugar."}
              </p>
              <button type="button" className="ghost" disabled={pending} onClick={() => onEditingPlace(!editingPlace)}>
                {editingPlace ? "Concluir" : "Alterar"}
              </button>
            </div>
            {editingPlace && placeLocations.length > 0 ? (
              <label className="receipt-field">
                <span>Lugar que vai receber</span>
                <select value={locationId} disabled={pending} onChange={(event) => onLocationId(event.target.value)}>
                  <option value="">Escolher o lugar…</option>
                  {placeLocations.map((location) => (
                    <option key={location.id} value={location.id}>
                      {location.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {editingPlace && placeLocations.length === 0 ? (
              <label className="receipt-field">
                <span>Nome do lugar</span>
                <input
                  value={locationName}
                  autoComplete="off"
                  disabled={pending}
                  onChange={(event) => onLocationName(event.target.value)}
                />
              </label>
            ) : null}
            {fieldGap(gaps, "local-estoque") ? (
              <p className="error" role="alert">
                {fieldGap(gaps, "local-estoque")}
              </p>
            ) : null}
          </>
        )}
      </section>

      {!document.stock_applied && document.items.length > 0 ? (
        <div className="receipt-summary">
          <strong>Ao confirmar</strong>
          {document.items.map((item) => {
            const draft = drafts[item.id];
            if (!draft) return null;
            const plan = linePlan(item, draft);
            const movement =
              plan.arrived == null
                ? "quantidade incompleta"
                : movementSentence(plan.arrived.amount, item.unit_code, draft.stockUnit, draft.packageContent) ||
                  "conta incompleta";
            const stockPreview = previewStockUnitCost(item.total_cost, plan.stock);
            const cost = purchaseCostCaption({
              invoiceUnitPrice: item.invoice_unit_price,
              invoiceUnit: item.unit_code,
              stockUnitCost: showCosts ? stockPreview : null,
              stockUnit: draft.stockUnit,
              currency: document.costs?.currency ?? document.currency,
            });
            return (
              <div key={item.id} className="receipt-summary__row">
                <span>{ingredientName(item, draft, ingredients)}</span>
                <span>
                  {draft.creating ? "Será cadastrado" : "Já cadastrado"}
                  {` · ${movement}`}
                  {showCosts && cost.stock ? ` · ${cost.stock}` : ""}
                </span>
              </div>
            );
          })}
          <div className="receipt-summary__row">
            <span>Local</span>
            <span>{newPlace ? `${placeLabel} · será cadastrado` : placeLabel || "Ainda sem lugar"}</span>
          </div>
          {document.stock_policy_ready === false ? (
            <div className="receipt-summary__row">
              <span>Política de estoque</span>
              <span>Será registrada uma política inicial</span>
            </div>
          ) : null}
        </div>
      ) : null}

      {!document.stock_applied ? (
        canConfirm ? (
          <button
            type="button"
            className="primary receipt-primary"
            disabled={pending || confirmBlocked || document.items.length === 0}
            onClick={onConfirm}
          >
            Confirmar recebimento
          </button>
        ) : (
          <p>A confirmação cabe a quem pode atualizar o estoque.</p>
        )
      ) : null}
    </section>
  );
}

function focusAnchor(anchor: string) {
  const node = window.document.getElementById(anchor);
  if (!node) return;
  const field = node.querySelector("input, select, textarea");
  if (field instanceof HTMLElement) field.focus();
}
