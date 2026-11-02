import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { QueueLens } from "../types";

type Group = "progress" | "history";

export const PROGRESS_KEYS = [
  "vigentes",
  "work:needs_action",
  "stage:open",
  "stage:accepted",
  "stage:paid",
  "stage:in_production",
] as const;

export const HISTORY_KEYS = [
  "history:all",
  "stage:delivered",
  "stage:finalized",
  "stage:cancelled",
  "stage:rejected",
] as const;

const DEFAULTS: Record<Group, string> = { progress: "vigentes", history: "history:all" };

const FALLBACK_LABELS: Record<string, string> = {
  vigentes: "Vigentes",
  "work:needs_action": "Precisa de ação",
  "stage:open": "Abertos",
  "stage:accepted": "A pagar",
  "stage:paid": "Pagos",
  "stage:in_production": "Em produção",
  "history:all": "Todos do histórico",
  "stage:delivered": "Entregues",
  "stage:finalized": "Finalizados",
  "stage:cancelled": "Cancelados",
  "stage:rejected": "Rejeitadas",
};

export function groupOfLens(key: string): Group | null {
  if ((PROGRESS_KEYS as readonly string[]).includes(key)) return "progress";
  if ((HISTORY_KEYS as readonly string[]).includes(key)) return "history";
  return null;
}

type Props = {
  lenses?: QueueLens[];
  pressed: string;
  onSelect: (key: string) => void;
};

function registros(total: number): string {
  return total === 1 ? "1 registro no total" : `${total} registros no total`;
}

export function QueueLenses({ lenses, pressed, onSelect }: Props) {
  const loaded = Boolean(lenses?.length);
  const byKey = new Map((lenses ?? []).map((lens) => [lens.key, lens]));
  const [group, setGroup] = useState<Group>(groupOfLens(pressed) ?? "progress");
  const strip = useRef<HTMLDivElement | null>(null);
  const [fade, setFade] = useState({ start: false, end: false });

  useEffect(() => {
    const next = groupOfLens(pressed);
    if (next) setGroup(next);
  }, [pressed]);

  const measure = useCallback(() => {
    const node = strip.current;
    if (!node) return;
    const start = node.scrollLeft > 1;
    const end = node.scrollWidth - node.clientWidth - node.scrollLeft > 1;
    setFade((current) => (current.start === start && current.end === end ? current : { start, end }));
  }, []);

  useLayoutEffect(() => {
    measure();
    const node = strip.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [measure, group, lenses]);

  const keys: readonly string[] = group === "progress" ? PROGRESS_KEYS : HISTORY_KEYS;
  const total =
    byKey.get("all")?.count ??
    (lenses ?? []).filter((lens) => lens.partition).reduce((sum, lens) => sum + lens.count, 0);

  function pill(key: string) {
    const lens = byKey.get(key);
    const label = lens?.label ?? FALLBACK_LABELS[key] ?? key;
    return (
      <button
        key={key}
        type="button"
        className={pressed === key ? "queue-lens is-on" : "queue-lens"}
        aria-pressed={pressed === key}
        onClick={() => onSelect(key)}
      >
        {label}
        {loaded ? <b>{lens?.count ?? 0}</b> : <span className="queue-lens-skel" aria-hidden="true" />}
      </button>
    );
  }

  const stripClass = ["queue-lenses", fade.start ? "fade-start" : "", fade.end ? "fade-end" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="queue-lens-block">
      <div className="queue-segments" role="tablist" aria-label="Grupo da fila">
        {(
          [
            ["progress", "Em andamento"],
            ["history", "Histórico"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`queue-tab-${id}`}
            aria-selected={group === id}
            aria-controls="queue-lens-panel"
            className={group === id ? "queue-segment is-on" : "queue-segment"}
            onClick={() => {
              if (group === id) return;
              setGroup(id);
              onSelect(DEFAULTS[id]);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {group === "history" && loaded ? <p className="queue-total">{registros(total)}</p> : null}
      <div id="queue-lens-panel" role="tabpanel" aria-labelledby={`queue-tab-${group}`} className="queue-lens-panel">
        <div
          className={stripClass}
          role="group"
          aria-label="Lentes da fila"
          data-scroll-x="lenses"
          ref={strip}
          onScroll={measure}
        >
          {keys.map((key, index) => (
            <span key={key} className="queue-lens-slot" data-divider={group === "progress" && index === 1 ? "true" : undefined}>
              {pill(key)}
            </span>
          ))}
        </div>
        {group === "progress" ? <p className="queue-lens-note">Todas fazem parte de Vigentes</p> : null}
      </div>
    </div>
  );
}
