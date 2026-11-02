import { useEffect, useRef, useState } from "react";
import {
  financialKindLabel,
  formatCents,
  formatDateTime,
  formatDay,
  formatMoney,
  historyEventName,
  isoDatesToBr,
  modalityLabel,
  statusLabel,
} from "./format";

const VOIDED_TEXT = "Cancelado — registro anulado por duplicidade";
import { ReschedulePanel, ScheduleLine, VoidPanel, bakeryToday, deliverySense } from "./orders/DateException";
import type { OrderDetail, UnpaidProductionPrompt } from "./types";

const ACTION_LABELS: Record<string, string> = {
  confirm: "Confirmar pedido",
  start_production: "Iniciar produção",
  confirm_delivery: "Confirmar entrega",
  mark_ready: "Marcar pronto",
  complete: "Marcar como entregue",
  cancel: "Cancelar",
};

function actionLabel(action: string, status: string, custom: boolean, modality?: string | null): string {
  if (action === "confirm" && status === "submitted") {
    return custom ? "Aceitar e liberar pagamento" : "Aceitar e reservar a data";
  }
  if (action === "complete") {
    return modality === "pickup" ? "Marcar como retirado" : "Marcar como entregue";
  }
  return ACTION_LABELS[action] ?? action;
}

const ADAPTATION_STATUS: Record<string, string> = {
  pending: "Pendente de avaliação",
  accepted: "Aceita conforme solicitada",
  alternative_proposed: "Alternativa proposta",
  alternative_accepted: "Alternativa acordada com o cliente",
  declined: "Não atendida",
};

const REASON_LABEL: Record<string, string> = {
  preference: "Preferência",
  dietary_restriction: "Intolerância ou restrição alimentar",
};

function AdaptationPanel({
  itemId,
  quantity,
  adaptation,
  disabled,
  onEvaluate,
}: {
  itemId: string;
  quantity: number;
  adaptation: NonNullable<OrderDetail["items"][number]["adaptation"]>;
  disabled: boolean;
  onEvaluate: (itemId: string, decision: string, response: string) => void;
}) {
  const [decision, setDecision] = useState("accept");
  const [response, setResponse] = useState(adaptation.bakery_response);

  return (
    <div className="admin-adaptation">
      <p>
        <strong>Solicitação de adaptação</strong> · {ADAPTATION_STATUS[adaptation.status] ?? adaptation.status}
      </p>
      <p>
        Aplica-se às {quantity} {quantity === 1 ? "unidade" : "unidades"} desta linha.
        {adaptation.reason ? ` Motivo informado: ${REASON_LABEL[adaptation.reason] ?? adaptation.reason}.` : ""}
      </p>
      <blockquote>{adaptation.customer_text}</blockquote>
      {adaptation.bakery_response ? <p>Resposta registrada: {adaptation.bakery_response}</p> : null}
      {adaptation.client_decision === "accepted_alternative" ? (
        <p>O cliente concordou com a alternativa.</p>
      ) : null}
      {adaptation.client_decision === "declined" ? (
        <p>O cliente recusou a alternativa. Silêncio não confirma. Não transforme este item em pão sem alteração.</p>
      ) : null}
      {adaptation.status === "accepted" ? (
        <p className="admin-muted">
          A aceitação registra a avaliação de A Loja, não uma certificação de ausência de alergênicos.
        </p>
      ) : null}
      {!adaptation.resolved && !disabled ? (
        <form
          className="admin-adaptation-form"
          onSubmit={(event) => {
            event.preventDefault();
            onEvaluate(itemId, decision, response);
          }}
        >
          <fieldset>
            <legend>Avaliar esta solicitação</legend>
            <label>
              <input
                type="radio"
                name={`adapt-${itemId}`}
                checked={decision === "accept"}
                onChange={() => setDecision("accept")}
              />
              Consegue atender conforme solicitado
            </label>
            <label>
              <input
                type="radio"
                name={`adapt-${itemId}`}
                checked={decision === "propose_alternative"}
                onChange={() => setDecision("propose_alternative")}
              />
              Propor uma alternativa
            </label>
            <label>
              <input
                type="radio"
                name={`adapt-${itemId}`}
                checked={decision === "decline"}
                onChange={() => setDecision("decline")}
              />
              Não consegue atender
            </label>
          </fieldset>
          <label>
            Resposta à cliente
            <textarea
              value={response}
              onChange={(event) => setResponse(event.target.value)}
              maxLength={2000}
              rows={3}
              required={decision !== "accept"}
            />
          </label>
          <p className="admin-muted">
            Uma alternativa em texto não muda preço, quantidade nem receita-base. Se isso for necessário,
            explique na resposta e só aceite o pedido depois de um acordo explícito; não cobre diferença
            automaticamente.
          </p>
          <button className="admin-secondary" type="submit">
            Registrar avaliação
          </button>
        </form>
      ) : null}
    </div>
  );
}

type DetailProps = {
  order: OrderDetail | null;
  loading: boolean;
  error: string | null;
  conflict: boolean;
  busyAction: string | null;
  noteError: string | null;
  onBack: () => void;
  onReload: () => void;
  onAction: (action: string, reason?: string) => void;
  onNote: (body: string) => void;
  onEvaluateAdaptation: (itemId: string, decision: string, response: string) => void;
  productionPrompt?: UnpaidProductionPrompt | null;
  onDismissProduction?: () => void;
  onConfirmUnpaidProduction?: () => void;
  onReschedule?: (body: {
    date: string;
    reason: string;
    origin: "customer" | "store";
    notify_customer: boolean;
    allow_closed_day: boolean;
  }) => Promise<void>;
  onVoidDuplicate?: (body: { original_order_id: string; reason: string }) => Promise<void>;
  onConfirmDelivery?: (body: { align_date_to_delivery: boolean; align_origin: "customer" | "store" }) => Promise<void>;
};

export function OrderDetailView({
  order,
  loading,
  error,
  conflict,
  busyAction,
  noteError,
  onBack,
  onReload,
  onAction,
  onNote,
  onEvaluateAdaptation,
  productionPrompt = null,
  onDismissProduction = () => undefined,
  onConfirmUnpaidProduction = () => undefined,
  onReschedule,
  onVoidDuplicate,
  onConfirmDelivery,
}: DetailProps) {
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [voidOpen, setVoidOpen] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [gapOpen, setGapOpen] = useState(false);
  const [alignDelivery, setAlignDelivery] = useState(true);
  const [alignOrigin, setAlignOrigin] = useState<"customer" | "store">("customer");
  const [note, setNote] = useState("");
  const dismissProductionRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (productionPrompt) {
      dismissProductionRef.current?.focus();
    }
  }, [productionPrompt]);

  if (loading && !order) {
    return (
      <section className="admin-page">
        <p className="admin-muted">Carregando pedido…</p>
      </section>
    );
  }

  if (error && !order) {
    return (
      <section className="admin-page">
        <p className="admin-error" role="alert">{error}</p>
        <button type="button" className="admin-secondary" onClick={onBack}>
          Voltar à lista
        </button>
      </section>
    );
  }

  if (!order) {
    return null;
  }

  const busy = Boolean(busyAction);
  const voided = Boolean(order.void_banner);
  const paidRecords = order.payment_records.filter((record) =>
    ["paid", "partially_refunded", "refunded"].includes(record.financial_status)
    && record.amount_paid_cents !== null,
  );
  const paymentMethods = [...new Set(paidRecords.map((record) =>
    record.method === "pix" ? "Pix" : record.method === "card" ? "Cartão" : "Não informada",
  ))];
  const paidTotal = paidRecords.reduce((sum, record) => sum + (record.amount_paid_cents ?? 0), 0);
  const refundedTotal = paidRecords.reduce((sum, record) => sum + (record.amount_refunded_cents ?? 0), 0);
  const paymentError = !order.financially_settled
    ? order.payment_records.find((record) => ["pending", "unknown"].includes(record.financial_status) && record.sanitized_error)?.sanitized_error
    : null;
  const unresolvedAdaptations =
    order.has_unresolved_adaptations ?? order.items.some((item) => item.adaptation && !item.adaptation.resolved);

  return (
    <section className="admin-page">
      <button type="button" className="admin-text" onClick={onBack}>
        ← Pedidos
      </button>
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">{order.public_reference}</p>
          <h1>
            <span className={order.visible_stage ? `admin-stage is-${order.visible_stage.replaceAll("_", "-")}` : "admin-stage"}>
              {order.visible_label || statusLabel(order.status, order.fulfillment_modality)}
            </span>
          </h1>
          <p>
            Encomenda: {order.visible_label || statusLabel(order.status, order.fulfillment_modality)}
          </p>
          {voided ? (
            <p className="admin-tag admin-tag-pay">{VOIDED_TEXT}</p>
          ) : order.payment_attention ? (
            <p className="admin-tag admin-tag-pay">{order.payment_attention}</p>
          ) : null}
          <p>{voided ? VOIDED_TEXT : order.financially_settled ? "Pagamento: Pago" : financialKindLabel(order.financial_kind)}</p>
          <p className="admin-muted">Criado em {formatDateTime(order.created_at)}</p>
          {order.schedule_exception ? (
            <ScheduleLine exception={order.schedule_exception} />
          ) : order.production_local_date ? (
            <p className="admin-muted">Data pedida: {formatDay(order.production_local_date)}</p>
          ) : null}
          <p className="admin-muted">
            Horário solicitado:{" "}
            {order.preferred_time
              ? `${order.preferred_time} (preferência; ainda não confirmado)`
              : "Sem preferência informada"}
          </p>
          {order.proposed_production_date ? (
            <p className="admin-muted">Data alternativa proposta: {formatDay(order.proposed_production_date)}</p>
          ) : null}
          {order.delivery_confirmed_at ? (
            <p className="admin-muted">Entrega confirmada em {formatDateTime(order.delivery_confirmed_at)}</p>
          ) : order.completed_at ? (
            <p className="admin-muted">
              Finalizado em {formatDateTime(order.completed_at)}. Este registro não tem confirmação de entrega.
            </p>
          ) : null}
          {order.has_custom && order.status === "submitted" ? (
            <p className="admin-tag admin-tag-attention">Nova solicitação de pão personalizado</p>
          ) : null}
          {order.notifications?.length ? (
            <ul className="admin-muted">
              {order.notifications.map((row, index) => (
                <li key={row.id ?? `${row.kind}-${row.status}-${index}`}>
                  Aviso {row.kind}: {row.status}
                  {row.sent_at ? " — aceito pelo serviço de e-mail (não comprova entrega na caixa)" : ""}
                  {row.status !== "sent" && row.last_error ? ` — ${row.last_error}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {order.fidelity_opt_in ? (
            <p className="admin-muted">
              Participação na fidelidade
              {order.fidelity_cpf_masked ? ` · CPF ${order.fidelity_cpf_masked}` : ""}
              {order.order_kind === "redemption" ? " · pedido de resgate" : ""}
            </p>
          ) : null}
        </div>
        {voided ? null : (
          <button type="button" className="admin-secondary" onClick={onReload} disabled={busy}>
            Recarregar
          </button>
        )}
      </header>

      {conflict ? (
        <p className="admin-warning" role="status">
          O pedido mudou. Atualize o pedido para ver o estado atual antes de agir de novo.
          <button type="button" className="admin-text" onClick={onReload} disabled={busy}>
            Atualizar pedido
          </button>
        </p>
      ) : null}
      {order.void_banner ? (
        <p className="admin-warning" role="status">
          Registro anulado como duplicado de {order.void_banner.original_reference}
          {order.void_banner.at ? ` em ${formatDateTime(order.void_banner.at)}` : ""}
          {order.void_banner.actor ? `, por ${order.void_banner.actor}` : ""}. Motivo: {isoDatesToBr(order.void_banner.reason ?? "")}
          {order.void_banner.original_id ? (
            <>
              {" "}
              <a href={`/admin/pedidos/${order.void_banner.original_id}`}>{order.void_banner.original_reference}</a>
            </>
          ) : null}
        </p>
      ) : null}
      {order.duplicate_links?.map((link) => (
        <p key={link.id} className="admin-muted">
          O pedido <a href={`/admin/pedidos/${link.id}`}>{link.public_reference}</a> foi anulado como duplicado deste.
        </p>
      ))}
      {order.action_notice ? <p role="status">{order.action_notice}</p> : null}
      {error ? <p className="admin-error" role="alert">{error}</p> : null}

      {unresolvedAdaptations ? <p>Adaptação: Aguardando avaliação</p> : null}

      {unresolvedAdaptations ? (
        <p className="admin-warning" role="status">
          Há adaptação pendente de resolução. Não aceite o pedido até avaliar cada solicitação e, se houver
          alternativa, esperar a concordância explícita da cliente. Pedido sem adaptação segue o fluxo normal.
        </p>
      ) : null}

      {order.void_banner ? null : (
      <div className="admin-actions">
        {order.allowed_actions
          .filter((action) => action !== "cancel")
          .map((action) => (
            <button
              key={action}
              type="button"
              className="admin-primary"
              disabled={busy || (action === "confirm" && unresolvedAdaptations)}
              onClick={() => {
                if (action === "confirm_delivery" && order.production_local_date && order.production_local_date !== bakeryToday()) {
                  setAlignDelivery(true);
                  setAlignOrigin("customer");
                  setDeliveryOpen(true);
                  return;
                }
                if (action === "start_production" && order.production_date_notice) {
                  setGapOpen(true);
                  return;
                }
                onAction(action);
              }}
            >
              {busyAction === action
                ? "Enviando…"
                : actionLabel(
                    action,
                    order.status,
                    order.items.some((item) => item.origin === "custom"),
                    order.fulfillment_modality,
                  )}
            </button>
          ))}
        {order.allowed_actions.includes("cancel") ? (
          <button
            type="button"
            className="admin-danger"
            disabled={busy}
            onClick={() => setCancelOpen(true)}
          >
            Cancelar
          </button>
        ) : null}
        {["confirmed", "in_production", "ready", "completed"].includes(order.status) ? (
          <button type="button" className="admin-secondary" disabled={busy} onClick={() => setRescheduleOpen(true)}>
            {order.status === "completed" ? "Corrigir a data registrada" : "Mudar a data da fornada"}
          </button>
        ) : null}
        {order.status === "completed" || (order.duplicate_candidates && order.duplicate_candidates.length > 0) ? (
          <button type="button" className="admin-danger" disabled={busy} onClick={() => setVoidOpen(true)}>
            Anular por duplicidade…
          </button>
        ) : null}
      </div>
      )}

      {cancelOpen ? (
        <form
          className="admin-cancel"
          onSubmit={(event) => {
            event.preventDefault();
            if (!reason.trim()) {
              return;
            }
            onAction("cancel", reason.trim());
            setCancelOpen(false);
            setReason("");
          }}
        >
          <label>
            Motivo do cancelamento (obrigatório)
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
              maxLength={280}
              rows={3}
            />
          </label>
          <div className="admin-actions">
            <button className="admin-danger" type="submit" disabled={busy || !reason.trim()}>
              Confirmar cancelamento
            </button>
            <button type="button" className="admin-secondary" onClick={() => setCancelOpen(false)}>
              Voltar
            </button>
          </div>
        </form>
      ) : null}
      {rescheduleOpen && onReschedule ? (
        <ReschedulePanel
          order={order}
          busy={busy}
          onClose={() => setRescheduleOpen(false)}
          onSubmit={async (body) => {
            await onReschedule(body);
            setRescheduleOpen(false);
          }}
        />
      ) : null}
      {voidOpen && onVoidDuplicate ? (
        <VoidPanel
          order={order}
          busy={busy}
          onClose={() => setVoidOpen(false)}
          onSubmit={async (body) => {
            await onVoidDuplicate(body);
            setVoidOpen(false);
          }}
        />
      ) : null}
      {deliveryOpen ? (
        <form
          className="admin-cancel"
          onSubmit={(event) => {
            event.preventDefault();
            const body = { align_date_to_delivery: alignDelivery, align_origin: alignOrigin };
            setDeliveryOpen(false);
            if (onConfirmDelivery) {
              void onConfirmDelivery(body);
            } else {
              onAction("confirm_delivery");
            }
          }}
        >
          <p>
            A fornada registrada é {formatDay(order.production_local_date)}. Você está confirmando a entrega em{" "}
            {formatDay(bakeryToday())}.
          </p>
          <label className="admin-check">
            <input
              type="checkbox"
              checked={alignDelivery && alignOrigin === "customer"}
              onChange={(event) => {
                setAlignDelivery(event.target.checked);
                setAlignOrigin("customer");
              }}
            />
            Registrar como entrega {deliverySense(order, bakeryToday())} a pedido do cliente
          </label>
          <label className="admin-check">
            <input
              type="checkbox"
              checked={alignDelivery && alignOrigin === "store"}
              onChange={(event) => {
                setAlignDelivery(event.target.checked);
                setAlignOrigin("store");
              }}
            />
            Registrar como entrega {deliverySense(order, bakeryToday())} pela loja
          </label>
          <div className="admin-actions">
            <button className="admin-primary" type="submit" disabled={busy}>
              Confirmar entrega
            </button>
            <button type="button" className="admin-secondary" onClick={() => setDeliveryOpen(false)}>
              Voltar
            </button>
          </div>
        </form>
      ) : null}
      {gapOpen ? (
        <div className="admin-cancel" role="dialog" aria-label="Data da fornada">
          <p>{order.production_date_notice}</p>
          <div className="admin-actions">
            <button
              type="button"
              className="admin-secondary"
              onClick={() => {
                setGapOpen(false);
                setRescheduleOpen(true);
              }}
            >
              Mudar a data da fornada
            </button>
            <button
              type="button"
              className="admin-primary"
              onClick={() => {
                setGapOpen(false);
                onAction("start_production");
              }}
            >
              Iniciar produção
            </button>
          </div>
        </div>
      ) : null}

      <div className="admin-grid">
        <article>
          <h2>Cliente</h2>
          <p>{order.customer_name ?? "Nome não informado"}</p>
          <p>{order.customer_email ?? "E-mail não informado"}</p>
          <p>{order.customer_phone ?? "Telefone não informado"}</p>
          {order.fulfillment_modality === "delivery" ? (
            <>
              {order.address.street ||
              order.address.number ||
              order.address.district ||
              order.address.city ||
              order.address.state ||
              order.address.postal_code ||
              order.address.complement ? (
                <p>
                  {[order.address.street, order.address.number].filter(Boolean).join(" ")}
                  {order.address.complement ? `, ${order.address.complement}` : ""}
                  {order.address.district || order.address.city || order.address.state || order.address.postal_code
                    ? ` — ${[order.address.district, [order.address.city, order.address.state].filter(Boolean).join("/")].filter(Boolean).join(", ")} ${order.address.postal_code || ""}`.trim()
                    : ""}
                </p>
              ) : (
                <p className="admin-muted">Nenhum endereço foi enviado neste pedido.</p>
              )}
              {order.delivery_pending ? (
                <p className="admin-warning" role="status">
                  {order.delivery_missing_fields?.length
                    ? `Dados de entrega incompletos: falta ${order.delivery_missing_fields.join(", ")}.`
                    : "Dados de entrega pendentes"}
                  {order.linked_delivery_filled_fields?.length
                    ? ` Na solicitação vinculada há rascunho de ${order.linked_delivery_filled_fields.join(", ")}; isso não foi gravado no pedido.`
                    : ""}
                </p>
              ) : null}
            </>
          ) : null}
        </article>
        <article>
          <h2>Recebimento</h2>
          <p>{modalityLabel(order.fulfillment_modality)}</p>
          <p>
            Fornada{" "}
            {order.production_batch_code
              ? order.production_batch_code
              : "não vinculada neste fluxo — a data pedida é o que o aceite reserva"}
          </p>
          <p>
            Janela{" "}
            {order.slot_starts_at || order.slot_ends_at
              ? `${formatDateTime(order.slot_starts_at)} – ${formatDateTime(order.slot_ends_at)}`
              : "ausente; o horário solicitado é preferência, não uma janela confirmada"}
          </p>
          <p>Reserva de capacidade: {order.holds_capacity ? "sim" : "não"}</p>
        </article>
        <article>
          <h2>Valores</h2>
          <p>Subtotal {formatMoney(order.subtotal)}</p>
          <p>Entrega {formatMoney(order.delivery_fee)}</p>
          <p>Desconto {formatMoney(order.discount)}</p>
          <p>
            <strong>Total {formatMoney(order.total)}</strong>
          </p>
        </article>
      </div>

      <article>
        <h2>Itens</h2>
        {!order.snapshots_locked ? (
          <p className="admin-muted">Rascunho: nomes e preços ainda são provisórios.</p>
        ) : null}
        <ul className="admin-items">
          {order.items.map((item) => (
            <li key={item.id}>
              <strong>
                {item.origin === "custom" ? "Pão personalizado · " : ""}
                {item.quantity}× {item.origin === "custom" ? item.shape_name : `${item.dough_name} · ${item.shape_name}`}
                {item.weight_grams ? ` · ${item.weight_grams} g` : ""}
              </strong>
              {item.origin === "custom" ? (
                <p>Fermentação e preparo: {item.dough_name}</p>
              ) : null}
              {item.provisional ? <span className="admin-tag">provisório</span> : null}
              <p>
                {formatMoney(item.unit_price)} cada · {formatMoney(item.line_total)}
              </p>
              {item.extras.length > 0 ? (
                <>
                  {item.extras.some((extra) => extra.assistant_role === "flour") ? (
                    <p>
                      Farinha:{" "}
                      {item.extras
                        .filter((extra) => extra.assistant_role === "flour")
                        .map((extra) => extra.name)
                        .join(", ")}
                    </p>
                  ) : null}
                  {item.extras.some((extra) => extra.assistant_role !== "flour") ? (
                    <p>
                      Inclusões:{" "}
                      {item.extras
                        .filter((extra) => extra.assistant_role !== "flour")
                        .map((extra) =>
                          extra.included_in_loaf_price || !extra.surcharge
                            ? `${extra.name} (incluso no preço do pão)`
                            : `${extra.name} (${formatMoney(extra.surcharge)})`,
                        )
                        .join(", ")}
                    </p>
                  ) : (
                    <p>Sem inclusões</p>
                  )}
                </>
              ) : (
                <p>Sem inclusões</p>
              )}
              {item.adaptation ? (
                <AdaptationPanel
                  itemId={item.id}
                  quantity={item.quantity}
                  adaptation={item.adaptation}
                  disabled={busy || order.status !== "submitted"}
                  onEvaluate={onEvaluateAdaptation}
                />
              ) : null}
            </li>
          ))}
        </ul>
      </article>

      <article>
        <h2>Observação do cliente</h2>
        <p>{order.customer_note || "Nenhuma"}</p>
      </article>

      <article>
        <h2>Notas internas</h2>
        <p className="admin-muted">Não aparecem na vitrine nem para o cliente.</p>
        <ul className="admin-timeline">
          {order.notes.length === 0 ? <li>Nenhuma nota interna.</li> : null}
          {order.notes.map((entry) => (
            <li key={entry.id}>
              <strong>{entry.author_ref ?? "sem autoria"}</strong> · {formatDateTime(entry.created_at)}
              <p>{entry.body}</p>
            </li>
          ))}
        </ul>
        <form
          className="admin-note-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!note.trim()) {
              return;
            }
            onNote(note.trim());
            setNote("");
          }}
        >
          <label>
            Nova nota
            <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} rows={3} />
          </label>
          {noteError ? <p className="admin-error">{noteError}</p> : null}
          <button className="admin-secondary" type="submit" disabled={busy || !note.trim()}>
            Registrar nota
          </button>
        </form>
      </article>

      <article>
        <h2>Histórico operacional</h2>
        <ul className="admin-timeline">
          {order.history.map((entry) => (
            <li key={entry.id}>
              {entry.from_status && entry.from_status === entry.to_status ? (
                historyEventName(entry.reason)
              ) : (
                <>
                  {statusLabel(entry.from_status ?? "—")} →{" "}
                  {entry.reason === "entrega confirmada pelo gestor" && entry.to_status === "completed"
                    ? "Entregue"
                    : statusLabel(entry.to_status)}
                </>
              )}{" "}
              ·{" "}
              {formatDateTime(entry.created_at)}
              {entry.actor_ref ? ` · ${entry.actor_ref}` : ""}
              {entry.reason ? <p>{isoDatesToBr(entry.reason)}</p> : null}
            </li>
          ))}
        </ul>
      </article>

      <article>
        <h2>Pagamento do pedido</h2>
        <p>Pedido {order.public_reference} · Total {formatMoney(order.total)}</p>
        <p><strong>{voided ? VOIDED_TEXT : order.total.cents === 0 ? "Sem valor a pagar" : order.financially_settled ? "Pago" : refundedTotal > 0 ? "Pagamento com estorno — conferir saldo" : paymentError ? "Pagamento em verificação" : "Aguardando confirmação do pagamento"}</strong></p>
        {paidRecords.length > 0 ? (
          <>
            <p>Forma de pagamento: {paymentMethods.join(" / ")}</p>
            <p>Valor recebido: {formatCents(paidTotal, order.currency)}</p>
            {refundedTotal > 0 ? <p>Valor estornado: {formatCents(refundedTotal, order.currency)}</p> : null}
            {paidRecords.map((record) => (
              <p key={record.id}>Confirmação: {formatDateTime(record.confirmed_at)} · Referência do pagamento: {record.external_reference ?? "não informada"}</p>
            ))}
            {order.total.cents !== null && paidTotal - refundedTotal > order.total.cents ? <p role="alert">Valor recebido superior ao total. Conferir no financeiro.</p> : null}
          </>
        ) : voided ? null : (
          <p className="admin-muted">Forma e valor recebido serão exibidos após a confirmação financeira.</p>
        )}
        {paymentError ? <p role="alert">{paymentError}</p> : null}
      </article>
      {productionPrompt ? (
        // O plugin trata o clique fora como elemento estático. O diálogo e o Escape continuam no elemento seguinte.
        // eslint-disable-next-line jsx-a11y/no-static-element-interactions
        <div
          className="admin-dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              onDismissProduction();
            }
          }}
        >
          {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- role=dialog num div não entra na exceção do plugin, que só libera a tag dialog */}
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="unpaid-production-title"
            className="admin-dialog"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                onDismissProduction();
              }
            }}
          >
            <h2 id="unpaid-production-title">
              {productionPrompt.uncertain
                ? "O pagamento deste pedido não pôde ser confirmado. Deseja iniciar a produção mesmo assim?"
                : "Este pedido ainda não está pago. Deseja iniciar a produção mesmo assim?"}
            </h2>
            <p>Referência {productionPrompt.public_reference}</p>
            <p>Total: {formatCents(productionPrompt.total_cents, productionPrompt.currency)}</p>
            <p>Condição financeira: {productionPrompt.financial_label}</p>
            {order.duplicate_paid ? (
              <p>
                Este cliente tem o pedido{" "}
                <a href={`/admin/pedidos/${order.duplicate_paid.id}`}>{order.duplicate_paid.public_reference}</a> pago
                com os mesmos itens. Pode ser o mesmo pedido.
              </p>
            ) : null}
            {order.production_date_notice ? <p>{order.production_date_notice}</p> : null}
            <div className="admin-dialog-actions">
              <button
                type="button"
                className="admin-secondary"
                ref={dismissProductionRef}
                onClick={onDismissProduction}
                disabled={busy}
              >
                Voltar
              </button>
              <button type="button" className="admin-primary" onClick={onConfirmUnpaidProduction} disabled={busy}>
                Iniciar mesmo sem pagamento
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
