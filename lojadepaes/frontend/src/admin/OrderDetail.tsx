import { useEffect, useRef, useState } from "react";
import {
  financialKindLabel,
  formatCents,
  formatDateTime,
  formatMoney,
  modalityLabel,
  statusLabel,
} from "./format";
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
}: DetailProps) {
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
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
          {order.payment_attention ? <p className="admin-tag admin-tag-pay">{order.payment_attention}</p> : null}
          <p>{order.financially_settled ? "Pagamento: Pago" : financialKindLabel(order.financial_kind)}</p>
          <p className="admin-muted">Criado em {formatDateTime(order.created_at)}</p>
          {order.production_local_date ? (
            <p className="admin-muted">Data pedida: {order.production_local_date}</p>
          ) : null}
          <p className="admin-muted">
            Horário solicitado:{" "}
            {order.preferred_time
              ? `${order.preferred_time} (preferência; ainda não confirmado)`
              : "Sem preferência informada"}
          </p>
          {order.proposed_production_date ? (
            <p className="admin-muted">Data alternativa proposta: {order.proposed_production_date}</p>
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
        <button type="button" className="admin-secondary" onClick={onReload} disabled={busy}>
          Recarregar
        </button>
      </header>

      {conflict ? (
        <p className="admin-warning" role="status">
          O pedido mudou. Atualize o pedido para ver o estado atual antes de agir de novo.
          <button type="button" className="admin-text" onClick={onReload} disabled={busy}>
            Atualizar pedido
          </button>
        </p>
      ) : null}
      {error ? <p className="admin-error" role="alert">{error}</p> : null}

      {unresolvedAdaptations ? <p>Adaptação: Aguardando avaliação</p> : null}

      {unresolvedAdaptations ? (
        <p className="admin-warning" role="status">
          Há adaptação pendente de resolução. Não aceite o pedido até avaliar cada solicitação e, se houver
          alternativa, esperar a concordância explícita da cliente. Pedido sem adaptação segue o fluxo normal.
        </p>
      ) : null}

      <div className="admin-actions">
        {order.allowed_actions
          .filter((action) => action !== "cancel")
          .map((action) => (
            <button
              key={action}
              type="button"
              className="admin-primary"
              disabled={busy || (action === "confirm" && unresolvedAdaptations)}
              onClick={() => onAction(action)}
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
      </div>

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
              {statusLabel(entry.from_status ?? "—")} →{" "}
              {entry.reason === "entrega confirmada pelo gestor" && entry.to_status === "completed"
                ? "Entregue"
                : statusLabel(entry.to_status)}{" "}
              ·{" "}
              {formatDateTime(entry.created_at)}
              {entry.actor_ref ? ` · ${entry.actor_ref}` : ""}
              {entry.reason ? <p>{entry.reason}</p> : null}
            </li>
          ))}
        </ul>
      </article>

      <article>
        <h2>Pagamento do pedido</h2>
        <p>Pedido {order.public_reference} · Total {formatMoney(order.total)}</p>
        <p><strong>{order.total.cents === 0 ? "Sem valor a pagar" : order.financially_settled ? "Pago" : refundedTotal > 0 ? "Pagamento com estorno — conferir saldo" : paymentError ? "Pagamento em verificação" : "Aguardando confirmação do pagamento"}</strong></p>
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
        ) : <p className="admin-muted">Forma e valor recebido serão exibidos após a confirmação financeira.</p>}
        {paymentError ? <p role="alert">{paymentError}</p> : null}
      </article>
      {productionPrompt ? (
        <div
          className="admin-dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              onDismissProduction();
            }
          }}
        >
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
