import { useState, type FormEvent } from "react";
import { Button } from "../shell/Button";
import type { OrderFilters, QueueLens } from "../types";

export const PILL_KEYS = new Set([
  "vigentes",
  "work:needs_action",
  "stage:open",
  "stage:accepted",
  "stage:paid",
  "stage:in_production",
  "stage:delivered",
  "stage:cancelled",
  "all",
]);

type Props = {
  filters: OrderFilters;
  secondary: QueueLens[];
  loading: boolean;
  phone: boolean;
  onChange: (filters: OrderFilters) => void;
  onSubmit: (event: FormEvent) => void;
  onClear?: () => void;
};

function activeCount(filters: OrderFilters): number {
  let count = 0;
  if (filters.reference.trim()) count += 1;
  if (filters.modality) count += 1;
  if (filters.created_from) count += 1;
  if (filters.created_to) count += 1;
  if (filters.status || (filters.lens && !PILL_KEYS.has(filters.lens))) count += 1;
  return count;
}

export function QueueFilters({ filters, secondary, loading, phone, onChange, onSubmit, onClear }: Props) {
  const [open, setOpen] = useState(false);
  const count = activeCount(filters);
  const situation = filters.status || (filters.lens && !PILL_KEYS.has(filters.lens) ? filters.lens : "");
  const showClear = count > 0;
  return (
    <>
      {phone ? (
        <Button type="button" className="queue-filters-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          {count > 0 ? `Filtros (${count})` : "Filtros"}
        </Button>
      ) : null}
      <form className={phone && !open ? "queue-filters is-shut" : "queue-filters"} onSubmit={onSubmit}>
        <label>
          Buscar
          <input
            value={filters.reference}
            placeholder="Referência ou nome do cliente"
            maxLength={80}
            onChange={(event) => onChange({ ...filters, reference: event.target.value })}
          />
        </label>
        <label>
          Situação
          <select
            aria-label="Situação"
            value={situation}
            onChange={(event) => {
              const value = event.target.value;
              if (value === "date_pending") {
                onChange({ ...filters, status: value, lens: "" });
              } else if (value.startsWith("stage:") || value.includes(":")) {
                onChange({ ...filters, status: "", lens: value });
              } else {
                onChange({ ...filters, status: value, lens: "" });
              }
            }}
          >
            <option value="">Todas</option>
            {secondary.map((lens) => (
              <option key={lens.key} value={lens.key}>
                {lens.count > 0 || lens.key !== "date_pending" ? `${lens.label} (${lens.count})` : lens.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Recebimento
          <select
            aria-label="Recebimento"
            value={filters.modality}
            onChange={(event) => onChange({ ...filters, modality: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="pickup">Retirada (histórico)</option>
            <option value="delivery">Entrega</option>
          </select>
        </label>
        <label>
          Criado de
          <input
            type="date"
            aria-label="Criado de"
            value={filters.created_from}
            onChange={(event) => onChange({ ...filters, created_from: event.target.value })}
          />
        </label>
        <label>
          até
          <input
            type="date"
            aria-label="Criado até"
            value={filters.created_to}
            onChange={(event) => onChange({ ...filters, created_to: event.target.value })}
          />
        </label>
        <div className="queue-filter-actions">
          <Button variant="primary" type="submit" disabled={loading}>
            {loading ? "Atualizando…" : "Filtrar"}
          </Button>
          {showClear && onClear ? (
            <button type="button" className="queue-link" onClick={onClear}>
              Limpar
            </button>
          ) : null}
        </div>
      </form>
    </>
  );
}
