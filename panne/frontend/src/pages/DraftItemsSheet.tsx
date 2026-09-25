import { useEffect, useRef, useState } from "react";
import type { CatalogItem, IngredientCard } from "../api/types";
import {
  COMMERCIAL_UNITS,
  CONTENT_UNITS,
  commercialLabels,
  lineMeasure,
} from "./draftMeasure";
import { NewIngredientDialog, type PendingNewIngredient } from "./NewIngredientDialog";

export type DraftLine = {
  key: string;
  description: string;
  quantity: string;
  unit_code: string;
  unit_price: string;
  package_content_quantity: string;
  package_content_unit: string;
  ingredient_id: string;
  ingredient_label: string;
  ingredient_code: string;
  pendingNew: PendingNewIngredient | null;
};

export const EMPTY_DRAFT_LINE: DraftLine = {
  key: "new",
  description: "",
  quantity: "",
  unit_code: "",
  unit_price: "",
  package_content_quantity: "",
  package_content_unit: "",
  ingredient_id: "",
  ingredient_label: "",
  ingredient_code: "",
  pendingNew: null,
};

export type IngredientSearchStatus = "idle" | "buscando" | "ok" | "erro";

type FieldErrors = Partial<Record<string, string>>;

function IngredientPicker({
  line,
  disabled,
  canCreate,
  results,
  status,
  searchError,
  onSearch,
  onPick,
  onClear,
  onCreate,
}: {
  line: DraftLine;
  disabled: boolean;
  canCreate: boolean;
  results: IngredientCard[];
  status: IngredientSearchStatus;
  searchError: string;
  onSearch: (query: string) => void;
  onPick: (row: IngredientCard) => void;
  onClear: () => void;
  onCreate: () => void;
}) {
  const listId = `ing-list-${line.key}`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const chosen = line.pendingNew?.display_name || line.ingredient_label;
  const chosenCode = line.pendingNew?.code || line.ingredient_code;
  const pending = Boolean(line.pendingNew);
  const visibleStatus: IngredientSearchStatus =
    !query.trim() || !open ? "idle" : status === "idle" ? "buscando" : status;
  const showPanel = open && Boolean(query.trim());
  const showList = showPanel && visibleStatus === "ok" && results.length > 0;
  const activeId =
    showList && activeIndex >= 0 && results[activeIndex]
      ? `ing-opt-${line.key}-${results[activeIndex].id}`
      : undefined;

  useEffect(() => {
    if (!open) return;
    onSearch(query);
  }, [open, query, onSearch]);

  useEffect(() => {
    setActiveIndex(-1);
  }, [query, status, results]);

  useEffect(() => {
    if (!chosen && open) inputRef.current?.focus();
  }, [chosen, open]);

  function pick(row: IngredientCard) {
    onPick(row);
    setQuery("");
    setOpen(false);
    setActiveIndex(-1);
  }

  return (
    <div className="entry-field draft-item__ingredient">
      <label htmlFor={`item-ing-${line.key}`}>Buscar ingrediente existente</label>
      {chosen ? (
        <div className="draft-item__picked">
          <p>
            <strong>{chosen}</strong>
            {chosenCode ? <span className="meta"> · {chosenCode}</span> : null}
            {pending ? <span className="meta"> · novo, será cadastrado ao salvar os itens</span> : null}
          </p>
          <button
            type="button"
            className="ghost"
            disabled={disabled}
            onClick={() => {
              onClear();
              setQuery("");
              setOpen(true);
            }}
          >
            Trocar
          </button>
        </div>
      ) : (
        <>
          <input
            id={`item-ing-${line.key}`}
            ref={inputRef}
            value={query}
            autoComplete="off"
            disabled={disabled}
            placeholder="Ainda não associado"
            role="combobox"
            aria-expanded={showList}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={activeId}
            aria-busy={visibleStatus === "buscando" || undefined}
            onFocus={() => setOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setOpen(false);
                setActiveIndex(-1);
                return;
              }
              if (!showList) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActiveIndex((index) => (index + 1) % results.length);
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
              } else if (event.key === "Enter" && activeIndex >= 0 && results[activeIndex]) {
                event.preventDefault();
                pick(results[activeIndex]);
              }
            }}
          />
          {showPanel && visibleStatus === "buscando" ? (
            <p className="draft-item__suggest-status draft-item__suggest-status--buscando" role="status">
              Buscando…
            </p>
          ) : null}
          {showPanel && visibleStatus === "erro" ? (
            <p className="draft-item__suggest-status draft-item__suggest-status--erro" role="alert">
              {searchError || "Não foi possível consultar os ingredientes."}
            </p>
          ) : null}
          {showPanel && visibleStatus === "ok" && results.length === 0 ? (
            <p className="draft-item__suggest-status draft-item__suggest-status--vazio" role="status">
              Nenhum ingrediente com este nome ou código.
            </p>
          ) : null}
          {showList ? (
            <ul id={listId} className="draft-item__suggest" role="listbox">
              {results.map((row, index) => (
                <li key={row.id}>
                  <button
                    type="button"
                    id={`ing-opt-${line.key}-${row.id}`}
                    role="option"
                    aria-selected={index === activeIndex}
                    disabled={disabled}
                    onClick={() => pick(row)}
                  >
                    {row.display_name} <span className="meta">{row.code}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
      {canCreate && !chosen ? (
        <button type="button" className="ghost draft-item__create" disabled={disabled} onClick={onCreate}>
          Cadastrar novo ingrediente
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
  searchStatus,
  searchError,
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
  searchStatus: IngredientSearchStatus;
  searchError: string;
  onChange: (key: string, patch: Partial<DraftLine>) => void;
  onAdd: () => void;
  onRemove: (key: string) => void;
  onSave: () => void;
  onSearchIngredients: (query: string) => void;
}) {
  const empty = lines.length === 0;
  const [creatingKey, setCreatingKey] = useState<string | null>(null);
  const createReturn = useRef<HTMLButtonElement | null>(null);
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

      {lines.map((line, index) => {
        const labels = commercialLabels(line.unit_code);
        const measure = lineMeasure({
          quantity: line.quantity,
          unit: line.unit_code,
          content: line.package_content_quantity,
          contentUnit: line.package_content_unit,
          price: line.unit_price,
        });
        return (
          <div className="draft-item" key={line.key}>
            <h3>1. O que foi comprado</h3>
            <div className="entry-field">
              <label htmlFor={`item-desc-${line.key}`}>Descrição na nota</label>
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
            <div className="draft-item__measures">
              <div className="entry-field">
                <label htmlFor={`item-qty-${line.key}`}>{labels.quantity}</label>
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
                <label htmlFor={`item-unit-${line.key}`}>{labels.purchaseUnit}</label>
                <select
                  id={`item-unit-${line.key}`}
                  value={line.unit_code}
                  disabled={pending || !canEdit}
                  aria-invalid={errors[`unit-${line.key}`] ? true : undefined}
                  aria-describedby={errors[`unit-${line.key}`] ? `item-unit-erro-${line.key}` : undefined}
                  onChange={(event) => onChange(line.key, { unit_code: event.target.value })}
                >
                  <option value="">Informe a unidade da nota</option>
                  {COMMERCIAL_UNITS.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
                {errors[`unit-${line.key}`] ? (
                  <span id={`item-unit-erro-${line.key}`} className="error" role="alert">
                    {errors[`unit-${line.key}`]}
                  </span>
                ) : null}
              </div>
              <div className="entry-field">
                <label htmlFor={`item-price-${line.key}`}>{labels.price}</label>
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
            </div>

            <h3>2. Conteúdo de cada {commercialWordSafe(line.unit_code)}</h3>
            <div className="draft-item__measures draft-item__measures--pair">
              <div className="entry-field">
                <label htmlFor={`item-content-${line.key}`}>{labels.content}</label>
                <input
                  id={`item-content-${line.key}`}
                  value={line.package_content_quantity}
                  inputMode="decimal"
                  autoComplete="off"
                  disabled={pending || !canEdit}
                  aria-invalid={errors[`content-${line.key}`] ? true : undefined}
                  aria-describedby={errors[`content-${line.key}`] ? `item-content-erro-${line.key}` : undefined}
                  onChange={(event) => onChange(line.key, { package_content_quantity: event.target.value })}
                />
                {errors[`content-${line.key}`] ? (
                  <span id={`item-content-erro-${line.key}`} className="error" role="alert">
                    {errors[`content-${line.key}`]}
                  </span>
                ) : null}
              </div>
              <div className="entry-field">
                <label htmlFor={`item-content-unit-${line.key}`}>Unidade do conteúdo</label>
                <select
                  id={`item-content-unit-${line.key}`}
                  value={line.package_content_unit}
                  disabled={pending || !canEdit}
                  onChange={(event) => onChange(line.key, { package_content_unit: event.target.value })}
                >
                  <option value="">Informe a unidade do conteúdo</option>
                  {CONTENT_UNITS.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="draft-item__math" aria-live="polite">
              {measure.formula || "A conta da linha aparece quando quantidade, conteúdo e preço forem informados."}
            </p>

            <h3>3. Ingrediente na Panne</h3>
            <IngredientPicker
              line={line}
              disabled={pending || !canEdit}
              canCreate={canCreateIngredient}
              results={results}
              status={searchStatus}
              searchError={searchError}
              onSearch={onSearchIngredients}
              onPick={(row) =>
                onChange(line.key, {
                  ingredient_id: row.id,
                  ingredient_label: row.display_name,
                  ingredient_code: row.code,
                  pendingNew: null,
                })
              }
              onClear={() =>
                onChange(line.key, {
                  ingredient_id: "",
                  ingredient_label: "",
                  ingredient_code: "",
                  pendingNew: null,
                })
              }
              onCreate={() => {
                createReturn.current = window.document.activeElement as HTMLButtonElement | null;
                setCreatingKey(line.key);
              }}
            />
            {lines.length > 1 ? (
              <button
                type="button"
                className="ghost"
                disabled={pending || !canEdit}
                onClick={() => onRemove(line.key)}
              >
                Remover item {index + 1}
              </button>
            ) : null}
          </div>
        );
      })}

      {canEdit ? (
        <div className="draft-items__actions">
          <button type="button" className="ghost" disabled={pending} onClick={onAdd}>
            {empty ? "Adicionar item" : "Adicionar outro item"}
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
      <p className="meta">Salvar itens não movimenta o estoque. A confirmação de entrada continua depois.</p>

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
              ingredient_code: value.code,
              pendingNew: value,
            });
            closeDialog();
          }}
        />
      ) : null}
    </section>
  );
}

function commercialWordSafe(unit: string): string {
  const key = unit.trim().toLocaleLowerCase("pt-BR");
  if (key === "pacote" || key === "pacotes") return "pacote";
  if (key === "caixa" || key === "caixas") return "caixa";
  return "embalagem";
}
