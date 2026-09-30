import { useEffect, useId, useState } from "react";
import { LINE_QUANTITY_MAX } from "./selection";

type Props = {
  value: number;
  onChange: (quantity: number) => void;
  max?: number;
  disabled?: boolean;
};

function parseDraft(raw: string, max: number): number | null {
  if (raw.trim() === "") {
    return null;
  }
  const next = Number.parseInt(raw, 10);
  if (!Number.isInteger(next)) {
    return null;
  }
  return Math.min(max, Math.max(1, next));
}

export function QuantityField({ value, onChange, max = LINE_QUANTITY_MAX, disabled = false }: Props) {
  const labelId = useId();
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  function commit(raw: string) {
    const parsed = parseDraft(raw, max);
    const next = parsed ?? 1;
    setDraft(String(next));
    if (next !== value) {
      onChange(next);
    }
  }

  return (
    <div className="qty-field">
      <span id={labelId}>Quantidade</span>
      <div className="qty-field-controls">
        <button
          type="button"
          className="qty-step"
          aria-label="Diminuir quantidade"
          disabled={disabled || value <= 1}
          onClick={() => onChange(value - 1)}
        >
          −
        </button>
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={max}
          aria-labelledby={labelId}
          disabled={disabled}
          value={draft}
          onChange={(event) => {
            const raw = event.target.value;
            setDraft(raw);
            const parsed = parseDraft(raw, max);
            if (parsed !== null && parsed !== value) {
              onChange(parsed);
            }
          }}
          onBlur={(event) => commit(event.target.value)}
        />
        <button
          type="button"
          className="qty-step"
          aria-label="Aumentar quantidade"
          disabled={disabled || value >= max}
          onClick={() => onChange(value + 1)}
        >
          +
        </button>
      </div>
    </div>
  );
}
