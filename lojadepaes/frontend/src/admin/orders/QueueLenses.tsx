import type { QueueLens } from "../types";

const ORDER = [
  "vigentes",
  "work:needs_action",
  "stage:open",
  "stage:accepted",
  "stage:paid",
  "stage:in_production",
  "stage:delivered",
  "stage:cancelled",
  "all",
];

type Props = {
  lenses: QueueLens[];
  pressed: string;
  onSelect: (key: string) => void;
};

export function QueueLenses({ lenses, pressed, onSelect }: Props) {
  const byKey = new Map(lenses.map((lens) => [lens.key, lens]));
  return (
    <div className="queue-lenses" role="group" aria-label="Lentes da fila" data-scroll-x="lenses">
      {ORDER.map((key) => {
        const lens = byKey.get(key) ?? { key, label: key, count: 0 };
        return (
          <button
            key={key}
            type="button"
            className={pressed === key ? "queue-lens is-on" : "queue-lens"}
            aria-pressed={pressed === key}
            onClick={() => onSelect(key)}
          >
            {lens.label}
            <b>{lens.count}</b>
          </button>
        );
      })}
    </div>
  );
}
