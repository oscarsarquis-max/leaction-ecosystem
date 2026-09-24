import { useState } from "react";
import {
  financialKindLabel,
  formatCents,
  formatDateTime,
  formatMoney,
  modalityLabel,
  paymentStatusLabel,
  statusLabel,
} from "./format";
import type { OrderDetail } from "./types";

const ACTION_LABELS: Record<string, string> = {
  confirm: "Confirmar pedido",
  start_production: "Iniciar produção",
  mark_ready: "Marcar pronto",
  complete: "Concluir atendimento",
  cancel: "Cancelar",
};

function actionLabel(action: string, status: string): string {
  if (action === "confirm" && status === "submitted") {
    return "Aceitar e reservar a data";
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
          A aceitação registra a avaliação da padaria, não uma certificação de ausência de alergênicos.
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
}: DetailProps) {
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");

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
          <h1>{statusLabel(order.status)}</h1>
          <p className="admin-muted">Criado em {formatDateTime(order.created_at)}</p>
          {order.production_local_date ? (
            <p className="admin-muted">Data pedida: {order.production_local_date}</p>
          ) : null}
          {order.proposed_production_date ? (
            <p className="admin-muted">Data alternativa proposta: {order.proposed_production_date}</p>
          ) : null}
        </div>
        <button type="button" className="admin-secondary" onClick={onReload} disabled={busy}>
          Recarregar
        </button>
      </header>

      {conflict ? (
        <p className="admin-warning" role="status">
          O pedido mudou. Recarregue para ver o estado atual antes de agir de novo.
        </p>
      ) : null}
      {error ? <p className="admin-error" role="alert">{error}</p> : null}

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
              {busyAction === action ? "Enviando…" : actionLabel(action, order.status)}
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
            <p>
              {order.address.street} {order.address.number}
              {order.address.complement ? `, ${order.address.complement}` : ""} — {order.address.district},{" "}
              {order.address.city}/{order.address.state} {order.address.postal_code}
            </p>
          ) : null}
        </article>
        <article>
          <h2>Recebimento</h2>
          <p>{modalityLabel(order.fulfillment_modality)}</p>
          <p>Fornada {order.production_batch_code ?? "não vinculada"}</p>
          <p>
            Janela {formatDateTime(order.slot_starts_at)} – {formatDateTime(order.slot_ends_at)}
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
                {item.quantity}× {item.dough_name} · {item.shape_name}
              </strong>
              {item.provisional ? <span className="admin-tag">provisório</span> : null}
              <p>
                {formatMoney(item.unit_price)} cada · {formatMoney(item.line_total)}
              </p>
              {item.extras.length > 0 ? (
                <p>
                  Inclusões:{" "}
                  {item.extras.map((extra) => `${extra.name} (${formatMoney(extra.surcharge)})`).join(", ")}
                </p>
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
              {statusLabel(entry.from_status ?? "—")} → {statusLabel(entry.to_status)} ·{" "}
              {formatDateTime(entry.created_at)}
              {entry.actor_ref ? ` · ${entry.actor_ref}` : ""}
              {entry.reason ? <p>{entry.reason}</p> : null}
            </li>
          ))}
        </ul>
      </article>

      <article>
        <h2>Financeiro (consulta)</h2>
        <p>O financeiro não reserva fornada. Aceitar o pedido é o que ocupa a data.</p>
        <p>{financialKindLabel(order.financial_kind)}</p>
        {order.financially_settled ? (
          <p>Quitação conferida pela regra interna de valor e moeda — não significa pedido concluído.</p>
        ) : null}
        {order.payment_records.length === 0 ? (
          <p className="admin-muted">
            Sem registro financeiro. Isso não indica cobrança pendente no ActionHub.
          </p>
        ) : (
          <ul className="admin-items">
            {order.payment_records.map((record) => (
              <li key={record.id}>
                <strong>{paymentStatusLabel(record.financial_status)}</strong> · {record.provider}
                <p>Esperado {formatCents(record.expected_cents, record.currency)}</p>
                <p>Pago {formatCents(record.amount_paid_cents, record.currency)}</p>
                <p>Estornado {formatCents(record.amount_refunded_cents, record.currency)}</p>
                <p>Referência ActionHub: {record.external_reference ?? "não informada"}</p>
                {record.method ? <p>Método: {record.method === "pix" ? "Pix" : "Cartão"}</p> : null}
                {record.sanitized_error ? <p>{record.sanitized_error}</p> : null}
                <p>Sincronizado: {formatDateTime(record.last_synced_at)}</p>
              </li>
            ))}
          </ul>
        )}
        {order.payment_events.length > 0 ? (
          <ul className="admin-timeline">
            {order.payment_events.map((event) => (
              <li key={event.id}>
                Evento {event.external_event_id} · {event.process_status} · {formatDateTime(event.received_at)}
                {event.sanitized_error ? <p>{event.sanitized_error}</p> : null}
              </li>
            ))}
          </ul>
        ) : null}
      </article>
    </section>
  );
}
