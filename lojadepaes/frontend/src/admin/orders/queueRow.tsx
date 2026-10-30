import { formatMoney, formatShortDay } from "../format";
import { bakeryTimeZone } from "../api";
import { Button } from "../shell/Button";
import { TrackChip } from "./TrackChip";
import type { NextAction, OrderListItem, OrderTracks, TrackChipData } from "../types";

const EMPTY: TrackChipData = { state: "not_applicable", label: "—", tone: "none", hint: "Não se aplica" };

export const TRACKS: Array<[keyof OrderTracks, string]> = [
  ["commercial", "Comercial"],
  ["payment", "Pagamento"],
  ["production", "Produção"],
  ["delivery", "Entrega"],
];

export function tracksOf(item: OrderListItem): OrderTracks {
  return (
    item.tracks ?? {
      commercial: EMPTY,
      payment: EMPTY,
      production: EMPTY,
      delivery: EMPTY,
    }
  );
}

export function actionOf(item: OrderListItem): NextAction {
  if (item.next_action) {
    return item.next_action;
  }
  if (
    item.source === "date_request" &&
    (item.status === "pending" || item.status === "alternative_proposed" || item.status === "awaiting_details")
  ) {
    return { code: "respond_date_request", label: "Avaliar e responder", primary: true };
  }
  return { code: "open", label: "Abrir", primary: false };
}

export function createdLine(value: string): string {
  const date = new Date(value);
  const time = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: bakeryTimeZone(),
  }).format(date);
  const key = new Intl.DateTimeFormat("en-CA", {
    timeZone: bakeryTimeZone(),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  if (key.format(date) === key.format(new Date())) {
    return `criado hoje, ${time}`;
  }
  return `criado ${formatShortDay(value)}, ${time}`;
}

export function fornadaLine(item: OrderListItem): string {
  if (item.source === "date_request") {
    return item.desired_date ? `pede ${formatShortDay(item.desired_date)}` : "pede data";
  }
  const day = item.production_local_date || item.proposed_production_date || item.desired_date;
  return day ? formatShortDay(day) : "sem data";
}

export function moneyLine(item: OrderListItem): string {
  if (item.source === "date_request" || item.total.cents == null) {
    return "—";
  }
  return formatMoney(item.total);
}

export function NextStep({
  item,
  onOpen,
}: {
  item: OrderListItem;
  onOpen: (item: OrderListItem) => void;
}) {
  const action = actionOf(item);
  return (
    <Button
      variant={action.primary ? "primary" : "secondary"}
      aria-label={`${action.label} — abrir ${item.public_reference}`}
      onClick={() => onOpen(item)}
    >
      {action.label}
    </Button>
  );
}

export function ReferenceLink({
  item,
  onOpen,
}: {
  item: OrderListItem;
  onOpen: (item: OrderListItem) => void;
}) {
  const href =
    item.source === "date_request" ? `/admin/pedidos/solicitacao/${item.id}` : `/admin/pedidos/${item.id}`;
  return (
    <a
      className="queue-ref"
      href={href}
      onClick={(event) => {
        event.preventDefault();
        onOpen(item);
      }}
    >
      {item.public_reference}
    </a>
  );
}

export function TrackList({ item }: { item: OrderListItem }) {
  const tracks = tracksOf(item);
  return (
    <>
      {TRACKS.map(([key, name]) => (
        <TrackChip key={key} name={name} track={tracks[key]} />
      ))}
    </>
  );
}
