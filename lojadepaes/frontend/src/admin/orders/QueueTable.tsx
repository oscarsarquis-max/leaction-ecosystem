import type { OrderListItem } from "../types";
import { TrackChip } from "./TrackChip";
import { NextStep, ReferenceLink, TRACKS, createdLine, fornadaLine, moneyLine, tracksOf } from "./queueRow";

type Props = {
  items: OrderListItem[];
  onOpen: (item: OrderListItem) => void;
};

export function QueueTable({ items, onOpen }: Props) {
  return (
    <div className="queue-table-wrap" data-queue="table">
      <table className="queue-table">
        <caption className="queue-caption">Fila de pedidos</caption>
        <thead>
          <tr>
            <th scope="col">Pedido</th>
            <th scope="col">Cliente</th>
            <th scope="col">Total</th>
            {TRACKS.map(([, name]) => (
              <th key={name} scope="col">
                {name}
              </th>
            ))}
            <th scope="col">Próximo passo</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const tracks = tracksOf(item);
            return (
              <tr key={item.row_key || item.id}>
                <td>
                  <ReferenceLink item={item} onOpen={onOpen} />
                  {item.source === "date_request" ? <span className="queue-kind">SOLICITAÇÃO DE DATA</span> : null}
                  <span className="queue-sub">{fornadaLine(item)}</span>
                  <span className="queue-sub">{createdLine(item.created_at)}</span>
                </td>
                <td>
                  <span className="queue-client">{item.customer_name ?? "Visitante sem nome"}</span>
                  {item.items_summary ? <span className="queue-sub">{item.items_summary}</span> : null}
                  {item.attention ? <span className="queue-attention">{item.attention}</span> : null}
                </td>
                <td className="queue-money">{moneyLine(item)}</td>
                {TRACKS.map(([key, name]) => (
                  <td key={key}>
                    <TrackChip name={name} track={tracks[key]} />
                  </td>
                ))}
                <td className="queue-action">
                  <NextStep item={item} onOpen={onOpen} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
