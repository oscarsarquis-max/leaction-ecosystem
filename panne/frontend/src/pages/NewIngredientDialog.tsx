import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { CatalogItem, IngredientCard } from "../api/types";
import { ingredientTypeLabel } from "../language/ingredients";

export type PendingNewIngredient = {
  display_name: string;
  code: string;
  ingredient_type: string;
  nutrition_basis_unit_id: string;
};

const TYPES = ["simple", "composite", "preparation"] as const;

export function NewIngredientDialog({
  fiscalDescription,
  units,
  similar,
  onSearchSimilar,
  onCancel,
  onConfirm,
}: {
  fiscalDescription: string;
  units: CatalogItem[];
  similar: IngredientCard[];
  onSearchSimilar: (query: string) => void;
  onCancel: () => void;
  onConfirm: (value: PendingNewIngredient) => void;
}) {
  const titleId = useId();
  const nameRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [ingredientType, setIngredientType] = useState<string>("simple");
  const [unitId, setUnitId] = useState(units[0]?.id ?? "");
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!unitId && units[0]?.id) setUnitId(units[0].id);
  }, [unitId, units]);

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
    onSearchSimilar(name.trim().length >= 2 ? name.trim() : code.trim());
  }, [name, code, onSearchSimilar]);

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
    if (!code.trim()) next.code = "Informe o código do ingrediente.";
    if (!unitId) next.unit = "Informe a unidade deste cadastro.";
    setErrors(next);
    if (Object.keys(next).length) return;
    onConfirm({
      display_name: name.trim(),
      code: code.trim(),
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
        <p className="meta">O cadastro só é gravado ao salvar os itens desta nota.</p>

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
        <div className="entry-field">
          <label htmlFor="novo-ingrediente-codigo">Código</label>
          <input
            id="novo-ingrediente-codigo"
            value={code}
            autoComplete="off"
            aria-invalid={errors.code ? true : undefined}
            aria-describedby={errors.code ? "novo-ingrediente-codigo-erro" : undefined}
            onChange={(event) => setCode(event.target.value)}
          />
          {errors.code ? (
            <span id="novo-ingrediente-codigo-erro" className="error" role="alert">
              {errors.code}
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
            {units.length === 0 ? <option value="">Nenhuma unidade disponível</option> : null}
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
          <button type="button" className="primary manual-primary" onClick={confirm}>
            Usar este novo ingrediente
          </button>
        </div>
      </div>
    </div>
  );
}
