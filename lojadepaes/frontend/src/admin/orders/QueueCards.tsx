import type { OrderListItem } from "../types";
import { TrackChip } from "./TrackChip";
import { NextStep, ReferenceLink, TRACKS, fornadaLine, moneyLine, tracksOf } from "./queueRow";

type Props = {
  items: OrderListItem[];
  two: boolean;
  onOpen: (item: OrderListItem) => void;
};

export function QueueCards({ items, two, onOpen }: Props) {
  return (
    <div className={two ? "queue-cards is-two" : "queue-cards"} data-queue="cards">
      {items.map((item) => {
        const tracks = tracksOf(item);
        return (
          <article key={item.row_key || item.id} className="queue-card" data-queue="card">
            <div className="queue-card-top">
              <div>
                <ReferenceLink item={item} onOpen={onOpen} />
                {item.source === "date_request" ? <span className="queue-kind">SOLICITAÇÃO DE DATA</span> : null}
              </div>
              {item.visible_label ? (
                <span className={`admin-chip c-${stageTone(item.visible_stage)}`}>{item.visible_label}</span>
              ) : null}
            </div>
            <h2>{item.customer_name ?? "Visitante sem nome"}</h2>
            <p className="queue-card-meta">
              <span>
                {fornadaLine(item)}
                {item.items_summary ? ` · ${item.items_summary}` : ""} · {moneyLine(item)}
              </span>
            </p>
            <div className="queue-tracks">
              {TRACKS.map(([key, name]) => (
                <div key={key}>
                  <p>{name}</p>
                  <TrackChip name={name} track={tracks[key]} />
                </div>
              ))}
            </div>
            {item.attention ? <p className="queue-attention">{item.attention}</p> : null}
            <NextStep item={item} onOpen={onOpen} />
          </article>
        );
      })}
    </div>
  );
}

function stageTone(stage?: string | null): string {
  if (stage === "accepted") return "acc";
  if (stage === "paid") return "paid";
  if (stage === "in_production") return "prod";
  if (stage === "delivered") return "del";
  if (stage === "cancelled" || stage === "rejected") return "can";
  if (stage === "open") return "open";
  return "none";
}
