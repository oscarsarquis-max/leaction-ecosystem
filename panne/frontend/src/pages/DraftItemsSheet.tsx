import { useEffect, useMemo, useRef, useState } from "react";
import type { CatalogItem, IngredientCard } from "../api/types";
import { NewIngredientDialog, type PendingNewIngredient } from "./NewIngredientDialog";

export type DraftLine = {
  key: string;
  description: string;
  quantity: string;
  unit_code: string;
  unit_price: string;
  ingredient_id: string;
  ingredient_label: string;
  pendingNew: PendingNewIngredient | null;
};

export const EMPTY_DRAFT_LINE: DraftLine = {
  key: "new",
  description: "",
  quantity: "",
  unit_code: "KG",
  unit_price: "",
  ingredient_id: "",
  ingredient_label: "",
  pendingNew: null,
};

type FieldErrors = Partial<Record<string, string>>;

function lineTotal(line: DraftLine): number | null {
  const qty = Number(line.quantity.replace(",", "."));
  const price = Number(line.unit_price.replace(",", "."));
  if (!Number.isFinite(qty) || !Number.isFinite(price) || line.unit_price.trim() === "") return null;
  return qty * price;
}

function IngredientPicker({
  line,
  disabled,
  canCreate,
  results,
  onSearch,
  onPick,
  onClear,
  onCreate,
}: {
  line: DraftLine;
  disabled: boolean;
  canCreate: boolean;
  results: IngredientCard[];
  onSearch: (query: string) => void;
  onPick: (row: IngredientCard) => void;
  onClear: () => void;
  onCreate: () => void;
}) {
  const listId = `ing-list-${line.key}`;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const chosen = line.pendingNew?.display_name || line.ingredient_label;
  const pending = Boolean(line.pendingNew);

  useEffect(() => {
    if (!open) return;
    onSearch(query);
  }, [open, query, onSearch]);

  return (
    <div className="entry-field draft-item__ingredient">
      <label htmlFor={`item-ing-${line.key}`}>Ingrediente na Panne</label>
      {chosen ? (
        <div className="draft-item__picked">
          <p>
            <strong>{chosen}</strong>
            {pending ? <span className="meta"> · novo, será cadastrado ao salvar os itens</span> : null}
            {line.pendingNew?.code ? <span className="meta"> · {line.pendingNew.code}</span> : null}
          </p>
          <button type="button" className="ghost" disabled={disabled} onClick={onClear}>
            Trocar
          </button>
        </div>
      ) : (
        <>
          <input
            id={`item-ing-${line.key}`}
            value={query}
            autoComplete="off"
            disabled={disabled}
            placeholder="Ainda não associado"
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            onFocus={() => setOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
            }}
          />
          {open && query.trim() ? (
            <ul id={listId} className="draft-item__suggest" role="listbox">
              {results.length === 0 ? (
                <li className="meta">Nenhum ingrediente com este nome ou código.</li>
              ) : (
                results.map((row) => (
                  <li key={row.id}>
                    <button
                      type="button"
                      role="option"
                      disabled={disabled}
                      onClick={() => {
                        onPick(row);
                        setQuery("");
                        setOpen(false);
                      }}
                    >
                      {row.display_name} <span className="meta">{row.code}</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </>
      )}
      {canCreate && !chosen ? (
        <button type="button" className="ghost" disabled={disabled} onClick={onCreate}>
          Criar novo
        </button>
      ) : null}
    </div>
  );
}

export function DraftItemsSheet({
  lines,
  errors,
  pending,
  canEdit,
  canCreateIngredient,
  units,
  results,
  similar,
  onChange,
  onAdd,
  onRemove,
  onSave,
  onSearchIngredients,
}: {
  lines: DraftLine[];
  errors: FieldErrors;
  pending: boolean;
  canEdit: boolean;
  canCreateIngredient: boolean;
  units: CatalogItem[];
  results: IngredientCard[];
  similar: IngredientCard[];
  onChange: (key: string, patch: Partial<DraftLine>) => void;
  onAdd: () => void;
  onRemove: (key: string) => void;
  onSave: () => void;
  onSearchIngredients: (query: string) => void;
}) {
  const empty = lines.length === 0;
  const [creatingKey, setCreatingKey] = useState<string | null>(null);
  const createReturn = useRef<HTMLButtonElement | null>(null);
  const totals = useMemo(() => {
    const values = lines.map(lineTotal);
    if (values.some((value) => value == null) || values.length === 0) return null;
    return values.reduce((sum, value) => (sum ?? 0) + (value ?? 0), 0);
  }, [lines]);
  const creating = lines.find((line) => line.key === creatingKey) ?? null;
  const missingLinks = lines.filter(
    (line) => line.description.trim() && !line.ingredient_id && !line.pendingNew,
  ).length;

  function closeDialog() {
    setCreatingKey(null);
    window.setTimeout(() => createReturn.current?.focus(), 0);
  }

  return (
    <section className="panel draft-items" aria-labelledby="itens-da-nota">
      <h2 id="itens-da-nota">Itens da nota</h2>
      {empty ? <p>Nenhum item informado.</p> : null}
      {errors.items ? (
        <p className="error" role="alert">
          {errors.items}
        </p>
      ) : null}
      {missingLinks > 0 ? (
        <p className="meta">
          {missingLinks === 1
            ? "Um item ainda não tem ingrediente associado. A nota pode permanecer pendente; o estoque continua bloqueado."
            : `${missingLinks} itens ainda não têm ingrediente associado. A nota pode permanecer pendente; o estoque continua bloqueado.`}
        </p>
      ) : null}

      {lines.map((line, index) => (
        <div className="draft-item" key={line.key}>
          <div className="entry-field">
            <label htmlFor={`item-desc-${line.key}`}>Descrição</label>
            <input
              id={`item-desc-${line.key}`}
              value={line.description}
              autoComplete="off"
              disabled={pending || !canEdit}
              aria-invalid={errors[`desc-${line.key}`] ? true : undefined}
              aria-describedby={errors[`desc-${line.key}`] ? `item-desc-erro-${line.key}` : undefined}
              onChange={(event) => onChange(line.key, { description: event.target.value })}
            />
            {errors[`desc-${line.key}`] ? (
              <span id={`item-desc-erro-${line.key}`} className="error" role="alert">
                {errors[`desc-${line.key}`]}
              </span>
            ) : null}
          </div>
          <IngredientPicker
            line={line}
            disabled={pending || !canEdit}
            canCreate={canCreateIngredient}
            results={results}
            onSearch={onSearchIngredients}
            onPick={(row) =>
              onChange(line.key, {
                ingredient_id: row.id,
                ingredient_label: row.display_name,
                pendingNew: null,
              })
            }
            onClear={() =>
              onChange(line.key, { ingredient_id: "", ingredient_label: "", pendingNew: null })
            }
            onCreate={() => {
              createReturn.current = window.document.activeElement as HTMLButtonElement | null;
              setCreatingKey(line.key);
            }}
          />
          <div className="draft-item__measures">
            <div className="entry-field">
              <label htmlFor={`item-qty-${line.key}`}>Quantidade</label>
              <input
                id={`item-qty-${line.key}`}
                value={line.quantity}
                inputMode="decimal"
                autoComplete="off"
                disabled={pending || !canEdit}
                aria-invalid={errors[`qty-${line.key}`] ? true : undefined}
                aria-describedby={errors[`qty-${line.key}`] ? `item-qty-erro-${line.key}` : undefined}
                onChange={(event) => onChange(line.key, { quantity: event.target.value })}
              />
              {errors[`qty-${line.key}`] ? (
                <span id={`item-qty-erro-${line.key}`} className="error" role="alert">
                  {errors[`qty-${line.key}`]}
                </span>
              ) : null}
            </div>
            <div className="entry-field">
              <label htmlFor={`item-unit-${line.key}`}>Unidade</label>
              <input
                id={`item-unit-${line.key}`}
                value={line.unit_code}
                autoComplete="off"
                disabled={pending || !canEdit}
                onChange={(event) => onChange(line.key, { unit_code: event.target.value })}
              />
            </div>
            <div className="entry-field">
              <label htmlFor={`item-price-${line.key}`}>Valor unitário</label>
              <input
                id={`item-price-${line.key}`}
                value={line.unit_price}
                inputMode="decimal"
                autoComplete="off"
                disabled={pending || !canEdit}
                aria-invalid={errors[`price-${line.key}`] ? true : undefined}
                aria-describedby={errors[`price-${line.key}`] ? `item-price-erro-${line.key}` : undefined}
                onChange={(event) => onChange(line.key, { unit_price: event.target.value })}
              />
              {errors[`price-${line.key}`] ? (
                <span id={`item-price-erro-${line.key}`} className="error" role="alert">
                  {errors[`price-${line.key}`]}
                </span>
              ) : null}
            </div>
            <p className="meta draft-item__total">
              Total da linha {index + 1}:{" "}
              {lineTotal(line) == null ? "não informado" : `R$ ${lineTotal(line)!.toFixed(2)}`}
            </p>
          </div>
          {lines.length > 1 ? (
            <button
              type="button"
              className="ghost"
              disabled={pending || !canEdit}
              onClick={() => onRemove(line.key)}
            >
              Remover item
            </button>
          ) : null}
        </div>
      ))}

      {canEdit ? (
        <div className="draft-items__actions">
          <button type="button" className="ghost" disabled={pending} onClick={onAdd}>
            {empty ? "Adicionar item" : "Adicionar outro"}
          </button>
          <button
            type="button"
            className="primary manual-primary"
            disabled={pending || empty}
            onClick={onSave}
          >
            Salvar itens da nota
          </button>
        </div>
      ) : null}
      {totals != null ? <p>Total informado: R$ {totals.toFixed(2)}</p> : null}
      <p className="meta">Salvar os itens não lança estoque. A confirmação de entrada continua depois.</p>

      {creating ? (
        <NewIngredientDialog
          fiscalDescription={creating.description}
          units={units}
          similar={similar}
          onSearchSimilar={onSearchIngredients}
          onCancel={closeDialog}
          onConfirm={(value) => {
            onChange(creating.key, {
              ingredient_id: "",
              ingredient_label: value.display_name,
              pendingNew: value,
            });
            closeDialog();
          }}
        />
      ) : null}
    </section>
  );
}
