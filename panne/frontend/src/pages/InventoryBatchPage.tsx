import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { IngredientCard } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";
import {
  DEFAULT_REASON,
  MAX_LINES,
  buildBatch,
  clearDraft,
  controlUnitFor,
  draftKey,
  emptyRow,
  findIngredient,
  headerIssues,
  isBlankRow,
  loadDraft,
  mapServerErrors,
  newRowId,
  normalizeText,
  parsePaste,
  rowIssues,
  saveDraft,
  summarize,
  summaryText,
  todayIso,
  type BatchHeader,
  type BatchRow,
  type FieldIssues,
  type FieldKey,
  type IngredientRef,
  type PackUnit,
  type ServerRowErrors,
  type StockItemRef,
  type UnitChoice,
} from "./inventoryBatch";

type Place = { id: string; display_name: string; status?: string };
type Catalog = { ingredients: IngredientRef[]; items: StockItemRef[]; places: Place[] };
type Done = { count: number; created: number; place: string };
type FocusTarget = { rowId: string; field: string };

const FIELD_ORDER: FieldKey[] = ["ingredient", "quantity", "unit", "packQty", "expires", "lot", "cost"];

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

async function loadCatalog(
  api: ReturnType<typeof useOrganization>["api"],
): Promise<Catalog> {
  const ingredients: IngredientRef[] = [];
  let offset = 0;
  for (let page = 0; page < 40; page += 1) {
    const result = await api.listIngredients({ limit: "50", offset: String(offset) });
    const rows = result.items as IngredientCard[];
    for (const row of rows) {
      if (row.status === "active" || row.status === undefined) {
        ingredients.push({ id: row.id, display_name: row.display_name });
      }
    }
    offset += rows.length;
    if (rows.length === 0 || offset >= result.total) break;
  }
  const places = await api.listInventory<Place>("/inventory/locations");
  let items: StockItemRef[] = [];
  try {
    const stock = await api.listInventory<StockItemRef>("/inventory/items");
    items = stock.items.map((row) => ({ ingredient_id: row.ingredient_id, unit_code: row.unit_code }));
  } catch {
    items = [];
  }
  ingredients.sort((a, b) => a.display_name.localeCompare(b.display_name, "pt-BR"));
  return { ingredients, items, places: places.items.filter((row) => row.status !== "inactive") };
}

export function InventoryBatchPage() {
  const { api, active, hasPermission } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();
  const today = todayIso();
  const catalog = useAsyncResource(() => loadCatalog(api), [api, orgId], Boolean(orgId));

  const [header, setHeader] = useState<BatchHeader>({ locationId: "", date: today, reason: DEFAULT_REASON });
  const [rows, setRows] = useState<BatchRow[]>(() => [emptyRow()]);
  const [pasteText, setPasteText] = useState("");
  const [pasteNote, setPasteNote] = useState<string | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [serverErrors, setServerErrors] = useState<ServerRowErrors>({});
  const [general, setGeneral] = useState<string[]>([]);
  const [recovered, setRecovered] = useState(false);
  const [draftReady, setDraftReady] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const [focusTarget, setFocusTarget] = useState<FocusTarget | null>(null);
  const refs = useRef(new Map<string, HTMLElement>());
  const rowsRef = useRef(rows);
  rowsRef.current = rows;

  const places = useMemo(() => (catalog.state.kind === "ok" ? catalog.state.data.places : []), [catalog.state]);
  const ingredients = useMemo(
    () => (catalog.state.kind === "ok" ? catalog.state.data.ingredients : []),
    [catalog.state],
  );
  const items = useMemo(() => (catalog.state.kind === "ok" ? catalog.state.data.items : []), [catalog.state]);
  const canCreate = hasPermission("ingredient.create");
  const canAdjust = hasPermission("inventory.adjust");

  // Rascunho: volta do navegador uma vez por organização.
  useEffect(() => {
    if (!orgId) return;
    setDraftReady(false);
    const draft = loadDraft(draftKey(orgId));
    if (draft) {
      setHeader({ ...draft.header, date: draft.header.date || today });
      setRows([...draft.rows, emptyRow()]);
      setRecovered(true);
    } else {
      setRecovered(false);
    }
    setDraftReady(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  // Um único local: já vem escolhido.
  useEffect(() => {
    if (header.locationId || places.length !== 1) return;
    setHeader((current) => ({ ...current, locationId: places[0].id }));
  }, [places, header.locationId]);

  // Salva o rascunho pouco depois da última mudança.
  useEffect(() => {
    if (!orgId || !draftReady || done) return;
    const timer = window.setTimeout(() => saveDraft(draftKey(orgId), header, rows), 250);
    return () => window.clearTimeout(timer);
  }, [orgId, draftReady, header, rows, done]);

  // Sempre existe uma linha vazia no fim: é ela que "cria sozinha" a próxima.
  useEffect(() => {
    const filled = rows.filter((row) => !isBlankRow(row)).length;
    if (done || filled >= MAX_LINES) return;
    if (rows.length === 0 || !isBlankRow(rows[rows.length - 1])) {
      setRows((current) => [...current, emptyRow()]);
    }
  }, [rows, done]);

  useEffect(() => {
    if (!focusTarget) return;
    const element = refs.current.get(`${focusTarget.rowId}:${focusTarget.field}`);
    if (element) {
      element.focus();
      setFocusTarget(null);
    }
  }, [focusTarget, rows]);

  const register = useCallback(
    (rowId: string, field: string) => (element: HTMLElement | null) => {
      const key = `${rowId}:${field}`;
      if (element) refs.current.set(key, element);
      else refs.current.delete(key);
    },
    [],
  );

  const ctx = useMemo(() => ({ items, today }), [items, today]);
  const summary = useMemo(() => summarize(rows), [rows]);
  const filledRows = rows.filter((row) => !isBlankRow(row));
  const headerProblems = showValidation ? headerIssues(header, today) : {};

  function updateRow(rowId: string, patch: Partial<BatchRow>, touched: FieldKey[] = []) {
    setRows((current) =>
      current.map((row) => {
        if (row.id !== rowId) return row;
        const issues = { ...row.issues };
        for (const field of touched) delete issues[field];
        return { ...row, ...patch, issues };
      }),
    );
    if (touched.length > 0) {
      setServerErrors((current) => {
        const own = current[rowId];
        if (!own) return current;
        const next = { ...own };
        for (const field of touched) delete next[field];
        return { ...current, [rowId]: next };
      });
    }
    setGeneral([]);
  }

  function goNext(rowId: string, field = "ingredient") {
    const current = rowsRef.current;
    const index = current.findIndex((row) => row.id === rowId);
    const next = current[index + 1];
    if (next) {
      setFocusTarget({ rowId: next.id, field });
      return;
    }
    const created = emptyRow();
    setRows([...current, created]);
    setFocusTarget({ rowId: created.id, field });
  }

  function duplicateRow(rowId: string) {
    setRows((current) => {
      const index = current.findIndex((row) => row.id === rowId);
      if (index < 0) return current;
      const copy: BatchRow = { ...current[index], id: newRowId(), issues: {} };
      return [...current.slice(0, index + 1), copy, ...current.slice(index + 1)];
    });
  }

  function removeRow(rowId: string) {
    setRows((current) => {
      const next = current.filter((row) => row.id !== rowId);
      return next.length > 0 ? next : [emptyRow()];
    });
    setServerErrors((current) => {
      const rest = { ...current };
      delete rest[rowId];
      return rest;
    });
  }

  function applyPaste(text: string, afterRowId: string | null) {
    const parsed = parsePaste(text, ingredients, items);
    if (parsed.rows.length === 0) {
      setPasteNote("Não encontrei linhas para preencher. Copie as células da planilha e cole de novo.");
      return;
    }
    setRows((current) => {
      const index = afterRowId ? current.findIndex((row) => row.id === afterRowId) : -1;
      // Da caixa de colar (ou de uma linha que sumiu): entra no fim, sem deixar linha em branco no meio.
      if (index < 0) return [...current.filter((row) => !isBlankRow(row)), ...parsed.rows];
      // Colado numa linha em branco: ocupa o lugar dela. Numa linha cheia: entra logo abaixo.
      const at = isBlankRow(current[index]) ? index : index + 1;
      const head = current.slice(0, at);
      const tail = current.slice(at).filter((row) => !isBlankRow(row));
      return [...head, ...parsed.rows, ...tail];
    });
    const fresh = parsed.rows.filter((row) => row.isNew).length;
    setPasteNote(
      `${plural(parsed.rows.length, "linha preenchida", "linhas preenchidas")}` +
        (fresh > 0 ? `, ${plural(fresh, "nome novo marcado", "nomes novos marcados")}.` : ".") +
        " Confira antes de gravar.",
    );
    setGeneral([]);
  }

  function onGridPaste(event: React.ClipboardEvent<HTMLElement>) {
    const target = event.target as HTMLElement;
    if (target.tagName === "TEXTAREA") return;
    const text = event.clipboardData.getData("text");
    if (!/[\t\n]/.test(text)) return;
    event.preventDefault();
    const owner = target.closest("[data-row-id]") as HTMLElement | null;
    applyPaste(text, owner?.dataset.rowId ?? null);
  }

  function focusFirstProblem(ids: string[]) {
    const first = ids[0];
    if (!first) return;
    const element = document.querySelector<HTMLElement>(`[data-row-id="${first}"]`);
    element?.scrollIntoView?.({ block: "center" });
  }

  async function save() {
    setShowValidation(true);
    setServerErrors({});
    const problems = headerIssues(header, today);
    const filled = rows.filter((row) => !isBlankRow(row));
    const bad = filled.filter((row) => Object.keys(rowIssues(row, ctx)).length > 0);
    const messages: string[] = [];
    if (filled.length === 0) messages.push("Digite ou cole ao menos um item antes de gravar.");
    if (filled.length > MAX_LINES) messages.push("O inventário aceita até 200 itens por vez. Grave em mais de uma remessa.");
    if (Object.keys(problems).length > 0) messages.push("Confira o local, a data e o motivo no topo.");
    if (bad.length > 0) messages.push(`Corrija ${plural(bad.length, "linha marcada", "linhas marcadas")} abaixo.`);
    if (messages.length > 0) {
      setGeneral(messages);
      focusFirstProblem(bad.map((row) => row.id));
      return;
    }
    if (command.pending) return;
    const built = buildBatch(header, rows);
    try {
      const result = await command.run(JSON.stringify(built.body), (key) => api.openInventoryBatch(built.body, key));
      if (!result) return;
      const place = places.find((row) => row.id === header.locationId)?.display_name ?? "o local escolhido";
      if (orgId) clearDraft(draftKey(orgId));
      setGeneral([]);
      setDone({
        count: result.data.line_count,
        created: result.data.created_ingredients ?? summary.newIngredients,
        place,
      });
    } catch (error) {
      if (error instanceof ApiError && error.lineErrors.length > 0) {
        const mapped = mapServerErrors(error.lineErrors, built.rowIds);
        setServerErrors(mapped.rows);
        setGeneral([
          "Nada foi gravado. Corrija as linhas marcadas e grave de novo. O que você digitou continua aqui.",
          ...mapped.general,
        ]);
        focusFirstProblem(Object.keys(mapped.rows));
      } else if (error instanceof ApiError && error.code === "conflito") {
        setGeneral(["O estoque mudou enquanto você digitava. Grave de novo; nada foi duplicado."]);
      } else {
        setGeneral([error instanceof Error && error.message ? error.message : "Não foi possível gravar o inventário."]);
      }
    }
  }

  function startOver() {
    setDone(null);
    setRows([emptyRow()]);
    setShowValidation(false);
    setServerErrors({});
    setGeneral([]);
    setRecovered(false);
    setPasteNote(null);
    setPasteText("");
  }

  function discardDraft() {
    if (orgId) clearDraft(draftKey(orgId));
    setRows([emptyRow()]);
    setRecovered(false);
    setServerErrors({});
    setGeneral([]);
    setShowValidation(false);
  }

  if (catalog.state.kind === "carregando") return <LoadingState />;

  if (done) {
    return (
      <div className="manual-path inv-batch" data-testid="inventario-gravado">
        <header className="inv-batch__head">
          <p className="manual-kicker">Organização · {active?.display_name || "atual"}</p>
          <h1>Inventário gravado</h1>
        </header>
        <section className="inv-batch__panel" role="status">
          <p>
            {plural(done.count, "item lançado", "itens lançados")} em {done.place}.
            {done.created > 0
              ? ` ${plural(done.created, "ingrediente novo foi cadastrado", "ingredientes novos foram cadastrados")}.`
              : ""}
          </p>
          <p className="inv-batch__hint">Nada virou nota fiscal, compra ou fornecedor. O saldo já aparece no estoque.</p>
          <div className="inv-batch__actions">
            <Link className="manual-primary" to="/componentes/estoque">
              Abrir a Visão geral do estoque
            </Link>
            <button type="button" className="manual-quiet" onClick={startOver}>
              Lançar outro inventário
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="manual-path inv-batch" onPaste={onGridPaste}>
      <header className="inv-batch__head">
        <div>
          <p className="manual-kicker">Organização · {active?.display_name || "atual"}</p>
          <h1>Inventário inicial</h1>
          <p>
            Lance todo o estoque de uma vez: digite as linhas ou cole da planilha. Nada vira nota fiscal nem compra.
          </p>
        </div>
        <Link className="manual-quiet" to="/componentes/estoque">
          Voltar ao estoque
        </Link>
      </header>

      {catalog.state.kind === "erro" ? <ErrorState error={catalog.state.error} onRetry={catalog.reload} /> : null}
      {!canAdjust ? (
        <p className="error" role="alert">
          Você não tem permissão para lançar estoque.
        </p>
      ) : null}
      {recovered ? (
        <p className="inv-batch__note" role="status">
          Recuperamos o rascunho que você deixou aqui.{" "}
          <button type="button" className="inv-batch__link" onClick={discardDraft}>
            Descartar rascunho
          </button>
        </p>
      ) : null}

      <section className="inv-batch__panel inv-batch__top" aria-label="Dados da contagem">
        <label className="manual-label">
          Local do estoque
          <select
            value={header.locationId}
            onChange={(event) => setHeader({ ...header, locationId: event.target.value })}
            aria-invalid={Boolean(headerProblems.location)}
          >
            <option value="">Escolher…</option>
            {places.map((row) => (
              <option key={row.id} value={row.id}>
                {row.display_name}
              </option>
            ))}
          </select>
          {headerProblems.location ? <span className="inv-batch__error">{headerProblems.location}</span> : null}
        </label>
        <label className="manual-label">
          Data da contagem
          <input
            type="date"
            value={header.date}
            max={today}
            onChange={(event) => setHeader({ ...header, date: event.target.value })}
            aria-invalid={Boolean(headerProblems.date)}
          />
          {headerProblems.date ? <span className="inv-batch__error">{headerProblems.date}</span> : null}
        </label>
        <label className="manual-label">
          Motivo
          <input
            value={header.reason}
            onChange={(event) => setHeader({ ...header, reason: event.target.value })}
            aria-invalid={Boolean(headerProblems.reason)}
          />
          {headerProblems.reason ? <span className="inv-batch__error">{headerProblems.reason}</span> : null}
        </label>
      </section>

      <section className="inv-batch__panel inv-batch__paste" aria-label="Colar da planilha">
        <label className="manual-label" htmlFor="inv-paste-area">
          Colar da planilha
        </label>
        <p className="inv-batch__hint" id="inv-paste-hint">
          Copie as linhas no Excel ou no Sheets, na ordem: nome, quantidade, unidade, validade, custo. Cole aqui ou
          direto na tabela.
        </p>
        <textarea
          id="inv-paste-area"
          rows={3}
          value={pasteText}
          aria-describedby="inv-paste-hint"
          placeholder={"Farinha de trigo\t25\tkg\t15/03/2027\t4,80"}
          onChange={(event) => setPasteText(event.target.value)}
        />
        <div className="inv-batch__actions">
          <button
            type="button"
            className="manual-quiet"
            disabled={!pasteText.trim()}
            onClick={() => {
              applyPaste(pasteText, null);
              setPasteText("");
            }}
          >
            Preencher a tabela
          </button>
          {pasteNote ? (
            <span role="status" className="inv-batch__hint">
              {pasteNote}
            </span>
          ) : null}
        </div>
      </section>

      <section className="inv-batch__table" aria-label="Itens do inventário">
        <p className="inv-batch__hint">
          Enter vai para a linha de baixo. Tab muda de campo. Deixe o custo em branco quando não souber, e a validade
          em branco quando o item não vence.
        </p>
        <div className="inv-grid" role="group" aria-label="Itens contados">
          <div className="inv-grid__head" aria-hidden="true">
            <span>Nº</span>
            <span>Ingrediente</span>
            <span>Quantidade</span>
            <span>Unidade</span>
            <span>Conteúdo da embalagem</span>
            <span>Validade</span>
            <span>Lote</span>
            <span>Custo unitário (R$)</span>
            <span>Linha</span>
          </div>
          <ol className="inv-grid__rows">
            {rows.map((row, index) => (
              <BatchRowEditor
                key={row.id}
                row={row}
                number={index + 1}
                ingredients={ingredients}
                items={items}
                canCreate={canCreate}
                issues={displayIssues(row, ctx, showValidation, serverErrors[row.id])}
                register={register}
                onChange={updateRow}
                onEnter={goNext}
                onFocusField={(rowId, field) => setFocusTarget({ rowId, field })}
                onDuplicate={duplicateRow}
                onRemove={removeRow}
              />
            ))}
          </ol>
        </div>
      </section>

      <section className="inv-batch__panel inv-batch__review" aria-label="Revisão">
        <div>
          <h2>Revisão</h2>
          <p className="inv-batch__summary" data-testid="resumo-inventario">
            {summaryText(summary)}
          </p>
          {general.length > 0 ? (
            <div className="error inv-batch__alert" role="alert">
              {general.map((message) => (
                <p key={message}>{message}</p>
              ))}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="manual-primary inv-batch__save"
          disabled={!canAdjust || command.pending || filledRows.length === 0}
          onClick={() => void save()}
        >
          {command.pending ? "Gravando…" : "Gravar inventário"}
        </button>
      </section>
    </div>
  );
}

function displayIssues(
  row: BatchRow,
  ctx: { items: StockItemRef[]; today: string },
  showValidation: boolean,
  server: FieldIssues | undefined,
): FieldIssues {
  const base = showValidation ? rowIssues(row, ctx) : row.issues;
  return { ...base, ...(server ?? {}) };
}

type RowEditorProps = {
  row: BatchRow;
  number: number;
  ingredients: IngredientRef[];
  items: StockItemRef[];
  canCreate: boolean;
  issues: FieldIssues;
  register: (rowId: string, field: string) => (element: HTMLElement | null) => void;
  onChange: (rowId: string, patch: Partial<BatchRow>, touched?: FieldKey[]) => void;
  onEnter: (rowId: string, field?: string) => void;
  onFocusField: (rowId: string, field: string) => void;
  onDuplicate: (rowId: string) => void;
  onRemove: (rowId: string) => void;
};

function BatchRowEditor({
  row,
  number,
  ingredients,
  items,
  canCreate,
  issues,
  register,
  onChange,
  onEnter,
  onFocusField,
  onDuplicate,
  onRemove,
}: RowEditorProps) {
  const errorId = `inv-row-error-${row.id}`;
  const messages = FIELD_ORDER.map((field) => issues[field]).filter((value): value is string => Boolean(value));
  const invalid = (field: FieldKey) => (issues[field] ? true : undefined);
  const describedBy = messages.length > 0 ? errorId : undefined;
  const control = row.ingredientId ? controlUnitFor(row.ingredientId, items) : null;

  function enterNext(event: React.KeyboardEvent) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    onEnter(row.id);
  }

  return (
    <li className={`inv-row${messages.length > 0 ? " inv-row--problem" : ""}`} data-row-id={row.id}>
      <span className="inv-row__n" aria-hidden="true">
        {number}
      </span>
      <div className="inv-field inv-field--ingredient">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-ingredient`}>
          Ingrediente<span className="visually-hidden"> da linha {number}</span>
        </label>
        <IngredientCombo
          row={row}
          ingredients={ingredients}
          canCreate={canCreate}
          inputId={`inv-${row.id}-ingredient`}
          describedBy={describedBy}
          invalid={invalid("ingredient")}
          registerInput={register(row.id, "ingredient")}
          onPick={(patch, moveOn) => {
            const known = patch.ingredientId ? controlUnitFor(patch.ingredientId, items) : null;
            const unit: UnitChoice = known ?? row.unit;
            onChange(row.id, { ...patch, unit }, ["ingredient", "unit"]);
            if (moveOn) onFocusField(row.id, "quantity");
          }}
          onText={(name) => onChange(row.id, { name, ingredientId: "", isNew: false }, ["ingredient"])}
          onEnter={() => onEnter(row.id)}
        />
        {row.isNew && !row.ingredientId ? <span className="inv-badge">novo</span> : null}
        {control ? <span className="inv-field__hint">Estoque em {control === "un" ? "unidade" : control}</span> : null}
      </div>
      <div className="inv-field inv-field--qty">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-quantity`}>
          Quantidade<span className="visually-hidden"> da linha {number}</span>
        </label>
        <input
          id={`inv-${row.id}-quantity`}
          ref={register(row.id, "quantity")}
          value={row.quantity}
          inputMode="decimal"
          aria-invalid={invalid("quantity")}
          aria-describedby={describedBy}
          onChange={(event) => onChange(row.id, { quantity: event.target.value }, ["quantity"])}
          onKeyDown={enterNext}
        />
      </div>
      <div className="inv-field inv-field--unit">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-unit`}>
          Unidade<span className="visually-hidden"> da linha {number}</span>
        </label>
        <select
          id={`inv-${row.id}-unit`}
          ref={register(row.id, "unit")}
          value={row.unit}
          aria-invalid={invalid("unit")}
          aria-describedby={describedBy}
          onChange={(event) => onChange(row.id, { unit: event.target.value as UnitChoice }, ["unit", "packQty"])}
          onKeyDown={enterNext}
        >
          <option value="">Escolher…</option>
          <option value="kg">kg (quilos)</option>
          <option value="g">g (gramas)</option>
          <option value="un">unidade</option>
          <option value="emb">embalagem</option>
        </select>
      </div>
      <div className="inv-field inv-field--pack">
        {row.unit === "emb" ? (
          <>
            <label className="inv-field__label" htmlFor={`inv-${row.id}-pack`}>
              Conteúdo de cada embalagem<span className="visually-hidden"> da linha {number}</span>
            </label>
            <div className="inv-pack">
              <input
                id={`inv-${row.id}-pack`}
                ref={register(row.id, "packQty")}
                value={row.packQty}
                inputMode="decimal"
                aria-invalid={invalid("packQty")}
                aria-describedby={describedBy}
                onChange={(event) => onChange(row.id, { packQty: event.target.value }, ["packQty"])}
                onKeyDown={enterNext}
              />
              <select
                aria-label={`Unidade do conteúdo da linha ${number}`}
                value={row.packUnit}
                onChange={(event) => onChange(row.id, { packUnit: event.target.value as PackUnit })}
                onKeyDown={enterNext}
              >
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="l">l</option>
              </select>
            </div>
          </>
        ) : null}
      </div>
      <div className="inv-field inv-field--expires">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-expires`}>
          Validade<span className="visually-hidden"> da linha {number}</span>
        </label>
        <input
          id={`inv-${row.id}-expires`}
          ref={register(row.id, "expires")}
          type="date"
          value={row.expires}
          aria-invalid={invalid("expires")}
          aria-describedby={describedBy}
          onChange={(event) => onChange(row.id, { expires: event.target.value }, ["expires"])}
          onKeyDown={enterNext}
        />
      </div>
      <div className="inv-field inv-field--lot">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-lot`}>
          Lote<span className="visually-hidden"> da linha {number}</span>
        </label>
        <input
          id={`inv-${row.id}-lot`}
          ref={register(row.id, "lot")}
          value={row.lot}
          aria-invalid={invalid("lot")}
          aria-describedby={describedBy}
          onChange={(event) => onChange(row.id, { lot: event.target.value }, ["lot"])}
          onKeyDown={enterNext}
        />
      </div>
      <div className="inv-field inv-field--cost">
        <label className="inv-field__label" htmlFor={`inv-${row.id}-cost`}>
          Custo unitário (R$)<span className="visually-hidden"> da linha {number}</span>
        </label>
        <input
          id={`inv-${row.id}-cost`}
          ref={register(row.id, "cost")}
          value={row.cost}
          inputMode="decimal"
          placeholder="Não sei"
          aria-invalid={invalid("cost")}
          aria-describedby={describedBy}
          onChange={(event) => onChange(row.id, { cost: event.target.value }, ["cost"])}
          onKeyDown={enterNext}
        />
      </div>
      <div className="inv-row__actions">
        <button type="button" className="inv-icon" onClick={() => onDuplicate(row.id)}>
          Duplicar<span className="visually-hidden"> linha {number}</span>
        </button>
        <button type="button" className="inv-icon" onClick={() => onRemove(row.id)}>
          Remover<span className="visually-hidden"> linha {number}</span>
        </button>
      </div>
      {messages.length > 0 ? (
        <ul className="inv-row__errors" id={errorId}>
          {messages.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

type ComboOption =
  | { kind: "existing"; id: string; label: string }
  | { kind: "new"; label: string; name: string };

function IngredientCombo({
  row,
  ingredients,
  canCreate,
  inputId,
  describedBy,
  invalid,
  registerInput,
  onPick,
  onText,
  onEnter,
}: {
  row: BatchRow;
  ingredients: IngredientRef[];
  canCreate: boolean;
  inputId: string;
  describedBy: string | undefined;
  invalid: true | undefined;
  registerInput: (element: HTMLElement | null) => void;
  onPick: (patch: Partial<BatchRow>, moveOn?: boolean) => void;
  onText: (name: string) => void;
  onEnter: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const selected = Boolean(row.ingredientId) || row.isNew;
  const listId = `${inputId}-lista`;

  const options = useMemo<ComboOption[]>(() => {
    const query = normalizeText(row.name);
    if (!query || selected) return [];
    const matches = ingredients
      .filter((item) => normalizeText(item.display_name).includes(query))
      .sort((a, b) => {
        const left = normalizeText(a.display_name).startsWith(query) ? 0 : 1;
        const right = normalizeText(b.display_name).startsWith(query) ? 0 : 1;
        return left - right || a.display_name.localeCompare(b.display_name, "pt-BR");
      });
    const list: ComboOption[] = matches
      .slice(0, 8)
      .map((item) => ({ kind: "existing", id: item.id, label: item.display_name }));
    const exact = matches.some((item) => normalizeText(item.display_name) === query);
    if (canCreate && !exact) {
      const name = row.name.replace(/\s+/g, " ").trim();
      list.push({ kind: "new", label: `Criar "${name}"`, name });
    }
    return list;
  }, [row.name, selected, ingredients, canCreate]);

  const visible = open && options.length > 0;

  function choose(option: ComboOption) {
    if (option.kind === "existing") onPick({ ingredientId: option.id, name: option.label, isNew: false }, true);
    else onPick({ ingredientId: "", name: option.name, isNew: true }, true);
    setOpen(false);
    setActiveIndex(0);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => Math.min(current + 1, Math.max(options.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Escape") {
      setOpen(false);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (visible) choose(options[Math.min(activeIndex, options.length - 1)]);
      else onEnter();
    }
  }

  function onBlur() {
    setOpen(false);
    if (selected) return;
    const exact = findIngredient(row.name, ingredients);
    if (exact) onPick({ ingredientId: exact.id, name: exact.display_name, isNew: false });
  }

  return (
    <div className="inv-combo">
      <input
        id={inputId}
        ref={registerInput}
        role="combobox"
        aria-expanded={visible}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={visible ? `${listId}-${activeIndex}` : undefined}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        autoComplete="off"
        value={row.name}
        placeholder="Digite para buscar"
        onChange={(event) => {
          onText(event.target.value);
          setOpen(true);
          setActiveIndex(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
      />
      {visible ? (
        <ul className="inv-combo__list" role="listbox" id={listId}>
          {options.map((option, index) => (
            <li
              key={option.kind === "existing" ? option.id : "novo"}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={option.kind === "new" ? "inv-combo__new" : undefined}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(option);
              }}
              onMouseEnter={() => setActiveIndex(index)}
            >
              {option.label}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
