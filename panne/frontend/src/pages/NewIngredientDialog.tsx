import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { CatalogItem, IngredientCard } from "../api/types";
import { ingredientTypeLabel } from "../language/ingredients";

export type PendingNewIngredient = {
  display_name: string;
  code: string;
  code_mode: "suggested" | "manual";
  ingredient_type: string;
  nutrition_basis_unit_id: string;
};

const TYPES = ["simple", "composite", "preparation"] as const;

export function NewIngredientDialog({
  fiscalDescription,
  units,
  similar,
  occupiedError,
  canEditCode = true,
  initialName = "",
  initialCode = "",
  initialUnit = "",
  initialType = "simple",
  initialCodeMode = "suggested",
  loadSuggestedCode,
  onSearchSimilar,
  onCancel,
  onConfirm,
}: {
  fiscalDescription: string;
  units: CatalogItem[];
  similar: IngredientCard[];
  occupiedError?: string | null;
  canEditCode?: boolean;
  initialName?: string;
  initialCode?: string;
  initialUnit?: string;
  initialType?: string;
  initialCodeMode?: "suggested" | "manual";
  loadSuggestedCode?: () => Promise<{ code: string }>;
  onSearchSimilar: (query: string) => void;
  onCancel: () => void;
  onConfirm: (value: PendingNewIngredient) => void;
}) {
  const titleId = useId();
  const nameRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState(initialName);
  const [code, setCode] = useState(initialCode);
  const [codeMode, setCodeMode] = useState<"suggested" | "manual">(initialCodeMode);
  const [editingCode, setEditingCode] = useState(Boolean(occupiedError) || initialCodeMode === "manual");
  const [suggestedBusy, setSuggestedBusy] = useState(Boolean(loadSuggestedCode) && !initialCode.trim());
  const [suggestedError, setSuggestedError] = useState<string | null>(null);
  const [ingredientType, setIngredientType] = useState<string>(initialType);
  const [unitId, setUnitId] = useState(initialUnit);
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const ready = Boolean(name.trim() && code.trim() && unitId && !suggestedBusy);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  useEffect(() => {
    let alive = true;
    if (!loadSuggestedCode || initialCode.trim()) {
      setSuggestedBusy(false);
      return;
    }
    setSuggestedBusy(true);
    loadSuggestedCode()
      .then((result) => {
        if (!alive) return;
        setCode((current) => (current.trim() ? current : result.code));
        setSuggestedError(null);
        setSuggestedBusy(false);
      })
      .catch(() => {
        if (!alive) return;
        setSuggestedError("Não foi possível sugerir o código interno.");
        setSuggestedBusy(false);
      });
    return () => {
      alive = false;
    };
  }, [loadSuggestedCode]);

  useEffect(() => {
    onSearchSimilar(name.trim().length >= 2 ? name.trim() : code.trim());
  }, [name, code, onSearchSimilar]);

  useEffect(() => {
    if (occupiedError) setErrors((current) => ({ ...current, code: occupiedError }));
  }, [occupiedError]);

  const duplicates = useMemo(() => {
    const nameKey = name.trim().toLocaleLowerCase("pt-BR");
    const codeKey = code.trim().toLocaleLowerCase("pt-BR");
    return similar.filter((row) => {
      const sameName = nameKey.length >= 2 && row.display_name.toLocaleLowerCase("pt-BR").includes(nameKey);
      const sameCode = codeKey.length >= 1 && row.code.toLocaleLowerCase("pt-BR") === codeKey;
      return sameName || sameCode;
    });
  }, [similar, name, code]);

  function confirm() {
    const next: Partial<Record<string, string>> = {};
    if (!name.trim()) next.name = "Informe o nome do ingrediente.";
    if (!code.trim()) next.code = "Informe o código interno do ingrediente.";
    if (!unitId) next.unit = "Informe a unidade deste cadastro.";
    setErrors(next);
    if (Object.keys(next).length) return;
    onConfirm({
      display_name: name.trim(),
      code: code.trim(),
      code_mode: editingCode ? "manual" : codeMode,
      ingredient_type: ingredientType,
      nutrition_basis_unit_id: unitId,
    });
  }

  return (
    <div className="draft-ingredient-dialog" role="presentation" onClick={onCancel}>
      <div
        className="draft-ingredient-dialog__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="draft-ingredient-dialog__body">
        <h3 id={titleId}>Criar ingrediente</h3>
        {fiscalDescription.trim() ? (
          <p className="meta">Descrição nesta nota: {fiscalDescription.trim()}</p>
        ) : null}
        <p className="meta">O cadastro só é gravado ao salvar os itens desta nota. Salvar os itens não movimenta o estoque.</p>

        <div className="entry-field">
          <label htmlFor="novo-ingrediente-nome">Nome do ingrediente</label>
          <input
            id="novo-ingrediente-nome"
            ref={nameRef}
            value={name}
            autoComplete="off"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? "novo-ingrediente-nome-erro" : undefined}
            onChange={(event) => setName(event.target.value)}
          />
          {errors.name ? (
            <span id="novo-ingrediente-nome-erro" className="error" role="alert">
              {errors.name}
            </span>
          ) : null}
        </div>
        <div className="entry-field entry-field--code">
          <label htmlFor="novo-ingrediente-codigo">Código interno sugerido</label>
          <div className="entry-field__code-row">
            <input
              id="novo-ingrediente-codigo"
              value={code}
              autoComplete="off"
              readOnly={!editingCode}
              aria-invalid={errors.code || suggestedError ? true : undefined}
              aria-describedby="novo-ingrediente-codigo-ajuda novo-ingrediente-codigo-erro"
              onChange={(event) => {
                setCode(event.target.value);
                setCodeMode("manual");
                setErrors((current) => ({ ...current, code: undefined }));
              }}
            />
            {canEditCode && !editingCode ? (
              <button
                type="button"
                className="ghost entry-field__edit-code"
                onClick={() => {
                  setEditingCode(true);
                  setCodeMode("manual");
                  window.setTimeout(() => window.document.getElementById("novo-ingrediente-codigo")?.focus(), 0);
                }}
              >
                Editar código
              </button>
            ) : null}
          </div>
          <p className="meta" id="novo-ingrediente-codigo-ajuda">
            Identificador interno da organização. Não é o código da nota nem GTIN.
          </p>
          {suggestedBusy ? <p className="meta">Sugerindo código interno…</p> : null}
          {errors.code || suggestedError ? (
            <span id="novo-ingrediente-codigo-erro" className="error" role="alert">
              {errors.code || suggestedError}
            </span>
          ) : null}
        </div>
        <div className="entry-field">
          <label htmlFor="novo-ingrediente-tipo">Tipo</label>
          <select
            id="novo-ingrediente-tipo"
            value={ingredientType}
            onChange={(event) => setIngredientType(event.target.value)}
          >
            {TYPES.map((type) => (
              <option key={type} value={type}>
                {ingredientTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>
        <div className="entry-field">
          <label htmlFor="novo-ingrediente-unidade">Unidade de base</label>
          <select
            id="novo-ingrediente-unidade"
            value={unitId}
            aria-invalid={errors.unit ? true : undefined}
            aria-describedby={errors.unit ? "novo-ingrediente-unidade-erro" : undefined}
            onChange={(event) => setUnitId(event.target.value)}
          >
            <option value="">{units.length === 0 ? "Nenhuma unidade disponível" : "Informe a unidade deste cadastro"}</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name || unit.title || unit.code || unit.id}
              </option>
            ))}
          </select>
          {errors.unit ? (
            <span id="novo-ingrediente-unidade-erro" className="error" role="alert">
              {errors.unit}
            </span>
          ) : null}
        </div>

        {duplicates.length > 0 ? (
          <div className="draft-ingredient-dialog__warn" role="status">
            <p>Já existe um ingrediente parecido nesta organização:</p>
            <ul>
              {duplicates.slice(0, 4).map((row) => (
                <li key={row.id}>
                  {row.display_name} ({row.code})
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        </div>

        <div className="draft-ingredient-dialog__actions">
          <button type="button" className="ghost" onClick={onCancel}>
            Voltar
          </button>
          <button type="button" className="primary manual-primary" disabled={!ready} onClick={confirm}>
            Usar este novo ingrediente
          </button>
        </div>
      </div>
    </div>
  );
}
