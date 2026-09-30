import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { AdminApiError, adminRequest } from "./api";
import "./fidelity.css";

type Participant = {
  id: string;
  name: string;
  email: string;
  cpf_masked: string;
  verified: boolean;
  valid_orders: number;
  credits_available: number;
};

type CreditRow = {
  id: string;
  status: string;
  reversible: boolean;
  block_reason: string | null;
  created_at: string | null;
};

type HistoryRow = {
  id: string;
  kind: string;
  reason: string;
  actor_ref: string | null;
  at: string | null;
};

type Detail = {
  id: string;
  name: string;
  email: string;
  cpf_masked: string;
  verified: boolean;
  valid_orders_month: number;
  credits: { available: number; reserved: number; used: number; returned: number };
  credits_available: number;
  progress: { progress_label?: string; credits_label?: string } | null;
  credit_rows: CreditRow[];
  history: HistoryRow[];
  can_grant: boolean;
  grant_block_reason: string | null;
};

type ListPayload = {
  items: Participant[];
  page: number;
  page_size: number;
  total: number;
  campaign_status: string | null;
  campaign_active: boolean;
  gaps: { name: string }[];
  pending_reviews?: { id: string; order_reference: string | null; reason: string }[];
  search_note?: string | null;
};

type FormMode = "grant" | "reverse" | null;

function statusLabel(status: string): string {
  if (status === "available") return "disponível";
  if (status === "reserved") return "reservado";
  if (status === "used") return "usado";
  if (status === "returned") return "revertido";
  return status;
}

function historyLabel(kind: string): string {
  if (kind === "qualify") return "Crédito conquistado pela promoção";
  if (kind === "manual_grant" || kind === "adjustment_grant") return "Concessão manual";
  if (kind === "manual_reverse" || kind === "adjustment_reverse") return "Reversão manual";
  if (kind === "partial_review") return "Revisão de estorno parcial";
  if (kind === "reverse") return "Reversão por cancelamento ou estorno";
  return kind;
}

export function FidelityParticipants() {
  const [list, setList] = useState<ListPayload | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [creditId, setCreditId] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchNote, setSearchNote] = useState<string | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const searchId = useId();
  const reasonId = useId();

  async function loadList(nextQuery = submittedQuery, nextPage = page) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        q: nextQuery,
        page: String(nextPage),
        page_size: "20",
      });
      const payload = await adminRequest<ListPayload>(
        `/api/v1/promotions/house-fidelity/admin/participants?${params}`,
      );
      setList(payload);
      setSearchNote(payload.search_note ?? null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "não foi possível carregar os participantes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadList();
  }, [submittedQuery, page]);

  useEffect(() => {
    if (detail) {
      panelRef.current?.focus();
    }
  }, [detail]);

  useEffect(() => {
    if (formMode) {
      reasonRef.current?.focus();
    }
  }, [formMode]);

  async function openDetail(id: string, opener?: HTMLButtonElement | null) {
    openerRef.current = opener ?? null;
    setDetailError(null);
    setFormMode(null);
    setReason("");
    setReasonError(null);
    setSuccess(null);
    try {
      const payload = await adminRequest<Detail>(`/api/v1/promotions/house-fidelity/admin/participants/${id}`);
      setDetail(payload);
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : "não foi possível abrir o participante");
    }
  }

  function closeDetail() {
    setDetail(null);
    setFormMode(null);
    setReason("");
    setReasonError(null);
    openerRef.current?.focus();
  }

  function onDrawerKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      if (formMode) {
        setFormMode(null);
        setReasonError(null);
        return;
      }
      closeDetail();
    }
  }

  async function submitAdjust(event: FormEvent) {
    event.preventDefault();
    if (!detail || busy) {
      return;
    }
    if (reason.trim().length < 3) {
      setReasonError("Informe o motivo deste ajuste.");
      reasonRef.current?.focus();
      return;
    }
    if (formMode === "reverse" && !creditId) {
      setReasonError("Escolha o crédito que será revertido.");
      return;
    }
    setBusy(true);
    setReasonError(null);
    try {
      await adminRequest("/api/v1/promotions/house-fidelity/admin/adjust", {
        method: "POST",
        body: JSON.stringify({
          account_id: detail.id,
          kind: formMode === "grant" ? "grant" : "reverse",
          reason,
          credit_id: formMode === "reverse" ? creditId : undefined,
        }),
      });
      const refreshed = await adminRequest<Detail>(
        `/api/v1/promotions/house-fidelity/admin/participants/${detail.id}`,
      );
      setDetail(refreshed);
      setFormMode(null);
      setReason("");
      setSuccess(formMode === "grant" ? "Crédito concedido." : "Crédito revertido.");
      await loadList();
    } catch (err: unknown) {
      setReasonError(err instanceof AdminApiError || err instanceof Error ? err.message : "não foi possível ajustar");
    } finally {
      setBusy(false);
    }
  }

  const items = list?.items ?? [];

  return (
    <section className="fidelity-page">
      <header>
        <h1>Fidelidade da casa</h1>
        <p className="fidelity-lead">Acompanhe participantes, créditos e ajustes.</p>
      </header>
      <div className="fidelity-strip">
        <span className={`fidelity-status ${list?.campaign_active ? "is-on" : "is-off"}`}>
          {list?.campaign_active ? "Campanha ativa" : "Campanha inativa"}
        </span>
        <span>4 pedidos válidos no mês → 1 crédito</span>
        <span>Créditos conquistados permanecem</span>
      </div>
      <p className="fidelity-reward">
        O crédito vale um pão de 500 g da vitrine. Focaccias não participam. Frete à parte.{" "}
        <a href="/" target="_blank" rel="noreferrer">
          Ver vitrine
        </a>
      </p>
      <details className="fidelity-help">
        <summary>Como os créditos são gerados</summary>
        <p>
          Quatro pedidos aceitos e pagos, com identidade verificada, geram um crédito sozinhos. Não é
          preciso conceder. Use o ajuste manual só para cortesia ou correção, com motivo.
        </p>
      </details>
      {(list?.gaps.length ?? 0) > 0 ? (
        <details className="fidelity-gaps">
          <summary>Relatório de apresentações</summary>
          <p>Falta 500 g / uma unidade em: {list?.gaps.map((item) => item.name).join(", ")}.</p>
        </details>
      ) : null}
      {(list?.pending_reviews?.length ?? 0) > 0 ? (
        <p className="admin-warning">
          Há estornos parciais aguardando revisão, sem decisão automática de carimbo.
        </p>
      ) : null}
      <form
        className="fidelity-search"
        onSubmit={(event) => {
          event.preventDefault();
          const digits = query.replace(/\D/g, "");
          if (digits.length >= 11) {
            setSearchNote("Busque por nome ou e-mail. O CPF não entra na busca.");
            setList((current) =>
              current ? { ...current, items: [], total: 0, page: 1 } : current,
            );
            return;
          }
          setSearchNote(null);
          setPage(1);
          setSubmittedQuery(query.trim());
        }}
      >
        <label htmlFor={searchId}>Buscar por nome ou e-mail</label>
        <input
          id={searchId}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoComplete="off"
        />
      </form>
      {searchNote ? <p className="fidelity-empty">{searchNote}</p> : null}
      {error ? (
        <p className="admin-error">
          {error}{" "}
          <button type="button" className="admin-text" onClick={() => void loadList()}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {loading && !list ? <p>Carregando participantes…</p> : null}
      {!loading && items.length === 0 ? (
        <p className="fidelity-empty">
          {submittedQuery ? "Nenhum participante com esse nome ou e-mail." : "Ainda não há participantes."}
        </p>
      ) : null}
      {items.length > 0 ? (
        <div className="fidelity-surface">
          <div className="fidelity-table-wrap">
            <table className="fidelity-table">
              <thead>
                <tr>
                  <th>Participante</th>
                  <th>CPF</th>
                  <th className="is-num">Pedidos válidos no mês</th>
                  <th className="is-num">Créditos disponíveis</th>
                  <th> </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="fidelity-who">
                        <strong>{item.name}</strong>
                        <span>{item.email}</span>
                      </div>
                    </td>
                    <td>{item.cpf_masked}</td>
                    <td className="is-num">{item.valid_orders}</td>
                    <td className="is-num">{item.credits_available}</td>
                    <td>
                      <button
                        type="button"
                        className="admin-text"
                        onClick={(event) => void openDetail(item.id, event.currentTarget)}
                      >
                        Ver detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="fidelity-cards">
            {items.map((item) => (
              <article key={item.id} className="fidelity-card">
                <strong className="fidelity-card-name">{item.name}</strong>
                <span className="fidelity-card-email">{item.email}</span>
                <dl>
                  <dt>CPF</dt>
                  <dd>{item.cpf_masked}</dd>
                  <dt>Pedidos válidos no mês</dt>
                  <dd>{item.valid_orders}</dd>
                  <dt>Créditos disponíveis</dt>
                  <dd>{item.credits_available}</dd>
                </dl>
                <button
                  type="button"
                  className="admin-secondary"
                  onClick={(event) => void openDetail(item.id, event.currentTarget)}
                >
                  Ver detalhes
                </button>
              </article>
            ))}
          </div>
        </div>
      ) : null}
      {list && list.total > list.page_size ? (
        <div className="fidelity-pager">
          <button type="button" className="admin-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Página anterior
          </button>
          <span>
            Página {list.page} de {Math.ceil(list.total / list.page_size)}
          </span>
          <button
            type="button"
            className="admin-secondary"
            disabled={page * list.page_size >= list.total}
            onClick={() => setPage(page + 1)}
          >
            Próxima página
          </button>
        </div>
      ) : null}

      {detail || detailError ? (
        <div className="fidelity-drawer" onKeyDown={onDrawerKey}>
          <aside
            ref={panelRef}
            className="fidelity-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
          >
            <button type="button" className="admin-text" onClick={closeDetail}>
              Fechar
            </button>
            {detailError ? <p className="admin-error">{detailError}</p> : null}
            {detail ? (
              <>
                <h2 id={titleId}>{detail.name}</h2>
                <p>
                  {detail.email} · CPF {detail.cpf_masked}
                </p>
                <p>
                  {detail.valid_orders_month} pedidos válidos neste mês · {detail.credits_available} crédito
                  {detail.credits_available === 1 ? "" : "s"} disponível
                  {detail.credits_available === 1 ? "" : "is"}
                </p>
                {detail.progress ? <p>{detail.progress.progress_label}</p> : null}
                {!detail.verified ? <p>Este cadastro ainda não confirmou o e-mail.</p> : null}
                {detail.valid_orders_month === 0 && detail.credits_available === 0 ? (
                  <p>Ainda não há compras válidas neste mês. Um crédito manual pode ser uma cortesia.</p>
                ) : null}
                <h3>Créditos</h3>
                {detail.credit_rows.length === 0 ? (
                  <p>Nenhum crédito ainda.</p>
                ) : (
                  <ul className="fidelity-credit-list">
                    {detail.credit_rows.map((row) => (
                      <li key={row.id}>
                        {statusLabel(row.status)}
                        {row.block_reason ? ` · ${row.block_reason}` : ""}
                        {row.reversible ? (
                          <>
                            {" · "}
                            <button
                              type="button"
                              className="admin-secondary fidelity-reverse"
                              onClick={() => {
                                setFormMode("reverse");
                                setCreditId(row.id);
                                setReason("");
                                setReasonError(null);
                                setSuccess(null);
                              }}
                            >
                              Reverter este crédito
                            </button>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
                <h3>Ajuste manual</h3>
                <p>
                  Use para uma cortesia ou correção excepcional. Os créditos da promoção são gerados
                  automaticamente.
                </p>
                {detail.can_grant ? (
                  <button
                    type="button"
                    className="admin-primary"
                    onClick={() => {
                      setFormMode("grant");
                      setReason("");
                      setReasonError(null);
                      setSuccess(null);
                    }}
                  >
                    Conceder crédito manualmente
                  </button>
                ) : (
                  <p>{detail.grant_block_reason}</p>
                )}
                {success ? <p className="admin-success">{success}</p> : null}
                {formMode ? (
                  <form className="fidelity-form" onSubmit={submitAdjust}>
                    <h3>
                      {formMode === "grant" ? "Conceder 1 crédito" : "Reverter crédito disponível"}
                    </h3>
                    <p>
                      {detail.name} · CPF {detail.cpf_masked}
                    </p>
                    <p>
                      {formMode === "grant"
                        ? "Um crédito disponível será acrescentado agora, sem pedido associado."
                        : "O crédito volta a não estar disponível. Pedidos e cobranças existentes não mudam."}
                    </p>
                    <label htmlFor={reasonId}>
                      {formMode === "grant"
                        ? "Por que está concedendo este crédito?"
                        : "Por que está revertendo este crédito?"}
                    </label>
                    <textarea
                      id={reasonId}
                      ref={reasonRef}
                      value={reason}
                      onChange={(event) => {
                        setReason(event.target.value);
                        setReasonError(null);
                      }}
                      maxLength={280}
                    />
                    {reasonError ? (
                      <p className="admin-error" role="alert">
                        {reasonError}
                      </p>
                    ) : null}
                    <div className="fidelity-form-actions">
                      <button type="submit" className="admin-primary" disabled={busy}>
                        {busy ? "Enviando…" : "Confirmar ajuste"}
                      </button>
                      <button
                        type="button"
                        className="admin-secondary"
                        onClick={() => {
                          setFormMode(null);
                          setReasonError(null);
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </form>
                ) : null}
                <h3>Histórico</h3>
                {detail.history.length === 0 ? (
                  <p>Nenhum evento ainda.</p>
                ) : (
                  <ul className="fidelity-history">
                    {detail.history.map((row) => (
                      <li key={row.id}>
                        {historyLabel(row.kind)}
                        {row.reason ? ` · ${row.reason}` : ""}
                        {row.actor_ref ? ` · ${row.actor_ref}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : null}
          </aside>
        </div>
      ) : null}
    </section>
  );
}
