import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { CatalogItem } from "../api";

export function SearchableSelect({
  label,
  value,
  onChange,
  options,
  emptyLabel,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: CatalogItem[];
  emptyLabel: string;
  disabled?: boolean;
}) {
  const listId = useId();
  const inputId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const selected = options.find((item) => item.id === value);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return options.filter((item) => `${item.name} ${item.code}`.toLowerCase().includes(needle));
  }, [options, query]);
  const entries = useMemo(() => [{ id: "", name: emptyLabel, inactive: false }, ...filtered.map((item) => ({ id: item.id, name: item.name, inactive: item.active === false }))], [emptyLabel, filtered]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  const choose = (id: string) => {
    onChange(id);
    setOpen(false);
    setQuery("");
  };

  const display = open ? query : selected ? `${selected.name}${selected.active === false ? " (inativa)" : ""}` : emptyLabel;

  return (
    <div className="combo" ref={rootRef}>
      <label htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        value={display}
        disabled={disabled}
        placeholder={emptyLabel}
        onFocus={() => {
          if (disabled) {
            return;
          }
          setOpen(true);
          setQuery("");
          setActive(0);
        }}
        onChange={(event) => {
          setOpen(true);
          setQuery(event.target.value);
          setActive(0);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            setOpen(false);
            setQuery("");
            return;
          }
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setActive((index) => Math.min(index + 1, Math.max(entries.length - 1, 0)));
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((index) => Math.max(index - 1, 0));
            return;
          }
          if (event.key === "Enter" && open) {
            event.preventDefault();
            const entry = entries[active];
            if (entry) {
              choose(entry.id);
            }
          }
        }}
      />
      {open ? (
        <ul id={listId} className="combo-list" role="listbox" aria-label={label}>
          {entries.length === 1 && filtered.length === 0 && query.trim() ? (
            <li className="combo-empty" role="presentation">
              Nenhum resultado
            </li>
          ) : (
            entries.map((entry, index) => (
              <li
                key={entry.id || "empty"}
                role="option"
                id={`${listId}-${index}`}
                aria-selected={entry.id === value}
                className={index === active ? "active" : undefined}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(entry.id)}
              >
                <button type="button" tabIndex={-1}>
                  {entry.name}
                  {entry.inactive ? " (inativa)" : ""}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
