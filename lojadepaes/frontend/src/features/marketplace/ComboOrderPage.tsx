import { useEffect, useState } from "react";
import { StorefrontLayout } from "../../components/StorefrontLayout";
import { formatCents } from "../../lib/money";
import { PartnerMark } from "./PartnerBadge";
import { fetchComboOrder, type ComboOrderView, type PartnerOrderStatus } from "./comboApi";
import "./marketplace-public.css";
import "./combo.css";

type Props = { reference: string; token: string };

const PARTNER_STATUS: Record<PartnerOrderStatus, { label: string; tone: string; hint: string }> = {
  submitted: { label: "Aguardando o parceiro", tone: "is-wait", hint: "O parceiro confirma a data no mesmo prazo da Loja." },
  accepted: { label: "Confirmado", tone: "is-ok", hint: "O parceiro confirmou a entrega na data da fornada." },
  refused: { label: "Recusado", tone: "is-off", hint: "Este item não vai sair. O pão continua; se preferir, cancele o pão no pedido da Loja." },
  expired: { label: "Sem resposta no prazo", tone: "is-off", hint: "Este item não vai sair. O pão continua; se preferir, cancele o pão no pedido da Loja." },
  cancelled: { label: "Cancelado", tone: "is-off", hint: "Este item foi cancelado." },
  delivered: { label: "Entregue", tone: "is-ok", hint: "O parceiro registrou a entrega." },
};

const DATE_LABEL = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });

function dateLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return DATE_LABEL.format(new Date(Date.UTC(y, m - 1, d)));
}

export function ComboOrderPage({ reference, token }: Props) {
  const [data, setData] = useState<ComboOrderView | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");

  useEffect(() => {
    let cancelled = false;
    fetchComboOrder(reference, token)
      .then((view) => {
        if (cancelled) return;
        setData(view);
        setState("ready");
        document.title = "Sua combo — Loja de Pães";
      })
      .catch(() => {
        if (!cancelled) setState("missing");
      });
    return () => {
      cancelled = true;
    };
  }, [reference, token]);

  if (state === "loading") {
    return (
      <StorefrontLayout>
        <main className="cmb-page" aria-busy="true">
          <p className="mkp-muted">Carregando o seu pedido…</p>
        </main>
      </StorefrontLayout>
    );
  }

  if (state === "missing" || !data) {
    return (
      <StorefrontLayout>
        <main className="cmb-page">
          <h1 className="cmb-title">Não encontramos este pedido</h1>
          <p className="mkp-muted">Abra pelo link do e-mail que enviamos. Ele traz o acesso ao acompanhamento.</p>
        </main>
      </StorefrontLayout>
    );
  }

  return (
    <StorefrontLayout>
      <main className="cmb-page">
        <p className="eyebrow">Sua combo</p>
        <h1 className="cmb-title">Pedido recebido</h1>
        <p className="mkp-lead">
          Fornada de {dateLabel(data.requested_date)}. Cada parte é confirmada por quem entrega; os pagamentos chegam por
          e-mail depois do aceite.
        </p>

        <ol className="cmb-parts" aria-label="Partes da combo">
          <li className="cmb-part">
            <div className="cmb-part-head">
              <span className="cmb-house-mark" aria-hidden="true">
                LP
              </span>
              <div>
                <strong>Loja de Pães</strong>
                <span className="mkp-muted">Pão e entrega · pedido {data.house.public_reference}</span>
              </div>
              <span className="cmb-part-amount">{formatCents(data.house.amount_cents)}</span>
            </div>
            <p className="cmb-status is-wait">{data.house.status_label}</p>
            <a className="cmb-link" href={data.house.order_url}>
              Acompanhar o pedido do pão
            </a>
          </li>
          {data.partners.map((part) => {
            const status = PARTNER_STATUS[part.status] ?? PARTNER_STATUS.submitted;
            return (
              <li key={part.id} className="cmb-part">
                <div className="cmb-part-head">
                  <PartnerMark partner={part.brand} />
                  <div>
                    <strong>{part.brand.brand_name}</strong>
                    <span className="mkp-muted">
                      {part.product_name} e entrega · pedido {part.public_reference}
                    </span>
                  </div>
                  <span className="cmb-part-amount">{formatCents(part.amount_cents)}</span>
                </div>
                <p className={`cmb-status ${status.tone}`}>{status.label}</p>
                <p className="mkp-muted cmb-part-hint">
                  {part.status === "refused" && part.refuse_reason ? `${part.refuse_reason}. ` : ""}
                  {status.hint}
                </p>
              </li>
            );
          })}
        </ol>

        <p className="cmb-total cmb-total-page">
          <span>Total da combo</span>
          <strong>{formatCents(data.total_cents)}</strong>
        </p>
        <p className="mkp-muted cmb-after">Guarde este link: ele mostra o andamento de cada parte.</p>
      </main>
    </StorefrontLayout>
  );
}
