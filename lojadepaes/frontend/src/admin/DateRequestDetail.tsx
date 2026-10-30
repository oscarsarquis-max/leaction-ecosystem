import { useEffect, useState } from "react";
import { formatCents, formatDateTime, formatDay, notificationStatusLabel, paes, statusLabel } from "./format";
import type { AcceptPreview, DateRequestDetail } from "./types";

const EVENT_LABELS: Record<string, string> = {
  created: "Solicitação recebida",
  available: "Disponibilidade informada",
  proposed: "Outra data proposta ao cliente",
  closed: "Encerrada com justificativa ao cliente",
  closed_silent: "Encerrada no registro",
  awaiting_details: "Aceite autorizado; faltam dados",
  converted: "Pedido formalizado e data reservada",
  accepted_notice: "Comunicação corretiva de aceite e pagamento",
};

type Address = {
  delivery_street: string;
  delivery_number: string;
  delivery_complement: string;
  delivery_district: string;
  delivery_city: string;
  delivery_state: string;
  delivery_postal_code: string;
};

const EMPTY_ADDRESS: Address = {
  delivery_street: "",
  delivery_number: "",
  delivery_complement: "",
  delivery_district: "",
  delivery_city: "",
  delivery_state: "",
  delivery_postal_code: "",
};

type CommercialLine = { variant_id: string; quantity: number };

type ActPayload = {
  proposed_date?: string | null;
  note?: string | null;
  address?: Address | null;
  lines?: CommercialLine[];
};

type DraftLine = { key: string; variant_id: string; quantity: string };

type Props = {
  request: DateRequestDetail | null;
  loading: boolean;
  error: string | null;
  busyAction: string | null;
  onBack: () => void;
  onReload: () => void;
  onAct: (action: "propose" | "close" | "accept" | "request_completion", payload: ActPayload) => void;
  onRetry?: (outboxId: string) => void;
  onQuote?: (lines: CommercialLine[]) => Promise<AcceptPreview>;
};

function communicationLabel(status: string): string {
  if (status === "pending" || status === "skipped") {
    return "Encerramento registrado — comunicação pendente";
  }
  if (status === "failed") {
    return "Falha no envio da justificativa";
  }
  if (status === "sent") {
    return "Justificativa aceita pelo serviço de e-mail — não comprova entrega na caixa";
  }
  return notificationStatusLabel(status);
}

export function DateRequestDetailView({
  request,
  loading,
  error,
  busyAction,
  onBack,
  onReload,
  onAct,
  onRetry,
  onQuote,
}: Props) {
  const [note, setNote] = useState("");
  const [proposed, setProposed] = useState("");
  const [proposeOpen, setProposeOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [address, setAddress] = useState<Address>(EMPTY_ADDRESS);
  const [draft, setDraft] = useState<DraftLine[]>([]);
  const [quoted, setQuoted] = useState<AcceptPreview | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  useEffect(() => {
    if (!request?.accept_preview?.needs_catalog_choice) {
      return;
    }
    const informed = request.accept_preview.informed_quantity;
    const suggestion = request.accept_preview.suggestion;
    setQuoted(null);
    setQuoteError(null);
    setDraft([
      {
        key: "linha-1",
        variant_id: suggestion?.variant_id ?? "",
        quantity: informed ? String(informed) : "",
      },
    ]);
  }, [request?.id, request?.accept_preview?.needs_catalog_choice, request?.accept_preview?.informed_quantity, request?.accept_preview?.suggestion?.variant_id]);

  useEffect(() => {
    if (!onQuote || !request?.accept_preview?.needs_catalog_choice) {
      return;
    }
    const complete = draft.filter((row) => row.variant_id && /^[1-9]\d*$/.test(row.quantity.trim()));
    if (complete.length === 0 || complete.length !== draft.length) {
      setQuoted(null);
      return;
    }
    let cancelled = false;
    onQuote(complete.map((row) => ({ variant_id: row.variant_id, quantity: Number(row.quantity) })))
      .then((preview) => {
        if (!cancelled) {
          setQuoted(preview);
          setQuoteError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setQuoted(null);
          setQuoteError("Não foi possível calcular o preço vigente.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [draft, onQuote, request?.id, request?.accept_preview?.needs_catalog_choice]);

  if (loading && !request) {
    return (
      <section className="admin-page">
        <p className="admin-muted">Carregando solicitação…</p>
      </section>
    );
  }
  if (!request) {
    return (
      <section className="admin-page">
        <p className="admin-error" role="alert">
          {error ?? "Solicitação não encontrada."}{" "}
          <button type="button" className="admin-link" onClick={onReload}>
            Tentar de novo
          </button>
        </p>
        <button type="button" className="admin-secondary" onClick={onBack}>
          Voltar à fila
        </button>
      </section>
    );
  }

  const open = request.allowed_actions.length > 0;
  const serverPreview = request.accept_preview;
  const preview = quoted ?? serverPreview;
  const catalogChoices = serverPreview?.catalog_choices ?? [];
  const selection =
    request.cart_context && request.cart_context.length > 0
      ? request.cart_context.map((line) => `${line.quantity}× ${line.product_name} (${line.variant_name})`).join("; ")
      : request.intended_quantity
        ? paes(request.intended_quantity)
        : "Quantidade não informada";
  const declined = request.notifications.filter((row) => row.kind === "date_request_declined");
  const closePreview = `A Loja avaliou sua solicitação de data ${formatDay(request.desired_date)} e não poderá atender.\n\n${note.trim()}`;

  return (
    <section className="admin-page admin-date-request-detail">
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Pedidos</p>
          <h1>{request.public_reference}</h1>
          <p>
            <span className="admin-tag admin-tag-request">Solicitação de data</span>{" "}
            {statusLabel(request.status)}
          </p>
        </div>
        <button type="button" className="admin-secondary" onClick={onBack}>
          Voltar à fila
        </button>
      </header>
      {error ? (
        <p className="admin-error" role="alert">
          {error}
        </p>
      ) : null}

      <article>
        <h2>Contato e contexto</h2>
        <p>
          <strong>{request.customer_name}</strong> · {request.customer_email}
        </p>
        <p>Recebida em {formatDateTime(request.created_at)}</p>
        <p>
          Data desejada: <strong>{formatDay(request.desired_date)}</strong>
        </p>
        {request.proposed_date ? <p>Data proposta ao cliente: {formatDay(request.proposed_date)}</p> : null}
        <p>{selection}</p>
        {request.message ? (
          <>
            <h3>Mensagem original</h3>
            <blockquote>{request.message}</blockquote>
          </>
        ) : (
          <p className="admin-muted">Sem mensagem original.</p>
        )}
        <p className="admin-muted">
          Seleção no carrinho não comprova checkout. Sem cobrança até o aceite formalizar o pedido.
        </p>
        {request.converted_order_href ? (
          <p>
            Pedido formalizado.{" "}
            <a className="admin-link" href={request.converted_order_href}>
              Abrir encomenda
            </a>
          </p>
        ) : null}
      </article>

      <article>
        <h2>Histórico</h2>
        {request.events.length === 0 ? <p className="admin-muted">Sem eventos ainda.</p> : null}
        <ol className="admin-timeline">
          {request.events.map((event) => (
            <li key={`${event.created_at}-${event.action}`}>
              {formatDateTime(event.created_at)} — {EVENT_LABELS[event.action] ?? event.action}
              {event.detail && event.action !== "created" && event.action !== "closed" ? ` · ${event.detail}` : ""}
            </li>
          ))}
        </ol>
      </article>

      <article>
        <h2>Avisos</h2>
        {request.notifications.length === 0 ? (
          <p className="admin-muted">Nenhum aviso enfileirado. A captura da tela não prova envio.</p>
        ) : (
          <ul className="admin-timeline">
            {request.notifications.map((row) => (
              <li key={row.id || `${row.kind}-${row.status}`}>
                {row.kind === "date_request_declined" ? communicationLabel(row.status) : notificationStatusLabel(row.status)}
                {row.last_error ? ` · ${row.last_error}` : ""}
                {row.id && row.status === "failed" && onRetry ? (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="admin-link"
                      disabled={busyAction !== null}
                      onClick={() => onRetry(row.id as string)}
                    >
                      Tentar envio de novo
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {request.status === "closed" && declined.length === 0 ? (
          <p className="admin-muted">
            Encerrada no registro. Não há evidência de e-mail de justificativa neste outbox.
          </p>
        ) : null}
      </article>

      {open ? (
        <article>
          <h2>Avaliar e responder</h2>
          {request.reply_preview ? <p className="admin-lead">{request.reply_preview}</p> : null}
          {preview ? (
            <div className="admin-accept-preview">
              <p>
                Prévia do aceite: data {formatDay(preview.accepted_date)}
                {preview.total_cents != null ? ` · ${formatCents(preview.total_cents, preview.currency)}` : ""}
              </p>
              {preview.items.length > 0 ? (
                <ul>
                  {preview.items.map((item) => (
                    <li key={`${item.product_name}-${item.variant_name}`}>
                      {item.quantity}× {item.product_name} ({item.variant_name}) · {formatCents(item.line_cents)}
                    </li>
                  ))}
                </ul>
              ) : null}
              {preview.gaps.length > 0 ? (
                <p className="admin-warning" role="status">
                  Ainda não dá para aceitar: {preview.gaps.join("; ")}.
                </p>
              ) : null}
              {serverPreview?.suggestion?.reason ? (
                <p className="admin-muted">{serverPreview.suggestion.reason}</p>
              ) : null}
              {quoteError ? (
                <p className="admin-warning" role="alert">
                  {quoteError}
                </p>
              ) : null}
              {(preview.complementary_pending?.length ?? 0) > 0 ? (
                <p className="admin-warning" role="status">
                  Pendências que não impedem o aceite nem o pagamento: {preview.complementary_pending?.join(", ")}.
                </p>
              ) : null}
              {preview.can_accept && !preview.has_address ? (
                <p className="admin-warning" role="status">
                  Dados de entrega pendentes. O aceite formaliza o pedido e o cliente completa o endereço no pagamento.
                </p>
              ) : null}
            </div>
          ) : null}
          {serverPreview?.needs_catalog_choice ? (
            <fieldset className="admin-address admin-catalog-choice">
              <legend>Confirmar o pão da encomenda</legend>
              <p className="admin-muted">
                A quantidade informada permanece. Escolha o produto real do catálogo para ver o preço vigente. Texto da mensagem não vira pão sozinho.
              </p>
              {draft.map((row, index) => (
                <div key={row.key} className="admin-catalog-row">
                  <label>
                    Pão
                    <select
                      aria-label={draft.length > 1 ? `Pão ${index + 1}` : "Pão do catálogo"}
                      value={row.variant_id}
                      onChange={(event) =>
                        setDraft((current) =>
                          current.map((item) =>
                            item.key === row.key ? { ...item, variant_id: event.target.value } : item,
                          ),
                        )
                      }
                    >
                      <option value="">Escolha o pão</option>
                      {catalogChoices.map((choice) => (
                        <option key={choice.variant_id} value={choice.variant_id}>
                          {choice.product_name} ({choice.variant_name}) · {formatCents(choice.unit_cents)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Quantidade
                    <input
                      aria-label={draft.length > 1 ? `Quantidade ${index + 1}` : "Quantidade"}
                      inputMode="numeric"
                      value={row.quantity}
                      onChange={(event) =>
                        setDraft((current) =>
                          current.map((item) =>
                            item.key === row.key ? { ...item, quantity: event.target.value } : item,
                          ),
                        )
                      }
                    />
                  </label>
                </div>
              ))}
              <div className="admin-actions">
                <button
                  type="button"
                  className="admin-secondary"
                  onClick={() =>
                    setDraft((current) => [
                      ...current,
                      { key: `linha-${current.length + 1}`, variant_id: "", quantity: "" },
                    ])
                  }
                >
                  Incluir outro pão
                </button>
                {draft.length > 1 ? (
                  <button
                    type="button"
                    className="admin-secondary"
                    onClick={() => setDraft((current) => current.slice(0, -1))}
                  >
                    Remover o último pão
                  </button>
                ) : null}
              </div>
            </fieldset>
          ) : null}
          {preview && !preview.has_address ? (
            <fieldset className="admin-address">
              <legend>Endereço (opcional — pendência de entrega se vazio)</legend>
              <label>
                Rua
                <input
                  value={address.delivery_street}
                  onChange={(event) => setAddress({ ...address, delivery_street: event.target.value })}
                />
              </label>
              <label>
                Número
                <input
                  value={address.delivery_number}
                  onChange={(event) => setAddress({ ...address, delivery_number: event.target.value })}
                />
              </label>
              <label>
                Complemento
                <input
                  value={address.delivery_complement}
                  onChange={(event) => setAddress({ ...address, delivery_complement: event.target.value })}
                />
              </label>
              <label>
                Bairro
                <input
                  value={address.delivery_district}
                  onChange={(event) => setAddress({ ...address, delivery_district: event.target.value })}
                />
              </label>
              <label>
                Cidade
                <input
                  value={address.delivery_city}
                  onChange={(event) => setAddress({ ...address, delivery_city: event.target.value })}
                />
              </label>
              <label>
                UF
                <input
                  value={address.delivery_state}
                  onChange={(event) => setAddress({ ...address, delivery_state: event.target.value })}
                  maxLength={2}
                />
              </label>
              <label>
                CEP
                <input
                  value={address.delivery_postal_code}
                  onChange={(event) => setAddress({ ...address, delivery_postal_code: event.target.value })}
                />
              </label>
            </fieldset>
          ) : null}
          <div className="admin-actions">
            <button
              type="button"
              className="admin-primary"
              disabled={busyAction !== null || (preview != null && !preview.can_accept)}
              onClick={() =>
                onAct("accept", {
                  note: note || null,
                  address: address.delivery_street.trim() ? address : null,
                  lines: serverPreview?.needs_catalog_choice
                    ? draft
                        .filter((row) => row.variant_id && /^[1-9]\d*$/.test(row.quantity.trim()))
                        .map((row) => ({ variant_id: row.variant_id, quantity: Number(row.quantity) }))
                    : undefined,
                })
              }
            >
              Aceitar data solicitada e enviar para pagamento
            </button>
            {preview && preview.ask_customer ? (
              <button
                type="button"
                className="admin-secondary"
                disabled={busyAction !== null}
                onClick={() => onAct("request_completion", { note: note || null })}
              >
                Enviar acesso para o cliente completar
              </button>
            ) : null}
            <button
              type="button"
              className="admin-secondary"
              disabled={busyAction !== null}
              onClick={() => {
                setProposeOpen((current) => !current);
                setCloseOpen(false);
              }}
            >
              Propor outra data
            </button>
          </div>
          {proposeOpen ? (
            <div className="admin-propose">
              <p className="admin-lead">
                A proposta não reserva a fornada. O cliente precisa responder; silêncio não confirma.
              </p>
              <label>
                Data alternativa
                <input type="date" value={proposed} onChange={(event) => setProposed(event.target.value)} />
              </label>
              <label>
                Mensagem opcional ao cliente
                <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} />
              </label>
              <button
                type="button"
                className="admin-secondary"
                disabled={busyAction !== null || !proposed}
                onClick={() => onAct("propose", { proposed_date: proposed, note: note || null })}
              >
                Enviar proposta
              </button>
            </div>
          ) : null}
          <button
            type="button"
            className="admin-text"
            disabled={busyAction !== null}
            onClick={() => {
              setCloseOpen((current) => !current);
              setProposeOpen(false);
            }}
          >
            Não será possível atender
          </button>
          {closeOpen ? (
            <div className="admin-close">
              <label>
                Justificativa ao cliente
                <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} required />
              </label>
              {note.trim() ? (
                <blockquote>
                  <p>Mensagem que será enviada:</p>
                  <pre>{closePreview}</pre>
                </blockquote>
              ) : (
                <p className="admin-muted">A justificativa é obrigatória. Espaços não contam.</p>
              )}
              <button
                type="button"
                className="admin-danger"
                disabled={busyAction !== null || !note.trim()}
                onClick={() => onAct("close", { note: note.trim() })}
              >
                Enviar justificativa e encerrar
              </button>
            </div>
          ) : null}
        </article>
      ) : (
        <p className="admin-muted">
          {request.status === "converted"
            ? "Esta solicitação já foi formalizada em pedido."
            : "Esta solicitação já foi encerrada."}
        </p>
      )}
    </section>
  );
}
