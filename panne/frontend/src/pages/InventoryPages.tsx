import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { isCancelledError } from "../api/errors";
import { CountMentor, PurchaseMentor } from "../components/InventoryMentors";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { config } from "../config";
import { formatDateTime, statusLabel } from "../format";
import {
  aggregateBalancesByUnit,
  demoExpiryReferenceNote,
  eligibilitySurfaceLabel,
  formatExpiryCaption,
  formatSignedMovementQuantity,
  historicalAdoptionCaption,
  historicalAdoptionHelp,
  locationPassageLabel,
  MOVEMENT_ORIGIN_LABEL,
  MOVEMENT_TYPE_LABEL,
  movementOriginLabel,
  movementTypeLabel,
  positionLotHref,
  resolveInventoryAsOf,
} from "../language/inventory";
import { formatExactQuantity, formatOperationalQuantity, pluralize } from "../language/quantities";
import { useOrganization } from "../session/OrganizationContext";

type Row = Record<string, unknown>;

type InventoryListState =
  | { kind: "carregando" }
  | { kind: "ok"; items: Row[]; asOf: string | null }
  | { kind: "erro"; error: unknown };

function tone(status: string): "sucesso" | "atencao" | "erro" | "info" {
  if (["available", "posted", "approved", "issued", "received", "reserved", "closed"].includes(status)) return "sucesso";
  if (["partial", "partially_received", "draft", "submitted", "counting", "review"].includes(status)) return "atencao";
  if (["blocked", "expired", "rejected", "cancelled", "failed"].includes(status)) return "erro";
  return "info";
}

function qty(value: unknown, unit?: unknown): string {
  return formatOperationalQuantity(
    value == null ? null : String(value),
    unit == null ? null : String(unit),
  );
}

function useItems(path: string) {
  const { api, active } = useOrganization();
  const [state, setState] = useState<InventoryListState>({ kind: "carregando" });

  const reload = useCallback(() => {
    setState({ kind: "carregando" });
    api
      .listInventory(path)
      .then((body) =>
        setState({
          kind: "ok",
          items: body.items,
          asOf: resolveInventoryAsOf(body.as_of),
        }),
      )
      .catch((error) => {
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  }, [api, path]);

  useEffect(() => {
    let alive = true;
    setState({ kind: "carregando" });
    api
      .listInventory(path)
      .then((body) => {
        if (!alive) return;
        setState({
          kind: "ok",
          items: body.items,
          asOf: resolveInventoryAsOf(body.as_of),
        });
      })
      .catch((error) => {
        if (!alive) return;
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [path, active?.organization_id, api]);

  return { state, load: reload, api };
}

function Screen({
  title,
  lede,
  path,
  children,
}: {
  title: string;
  lede: string;
  path: string;
  children?: (items: Row[], reload: () => void, asOf: string | null) => ReactNode;
}) {
  const { state, load } = useItems(path);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") {
    return <ErrorState error={state.error} onRetry={load} />;
  }
  return (
    <div className="stage">
      <div>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
        {state.items.length === 0 ? <EmptyState>Não há registros nesta organização.</EmptyState> : null}
        {children ? children(state.items, load, state.asOf) : null}
      </div>
    </div>
  );
}

export function InventoryOverviewPage() {
  const { hasPermission } = useOrganization();
  const { state, load } = useItems("/inventory/balances");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  const totals = aggregateBalancesByUnit(state.items);
  const exactRows = state.items.flatMap((row, index) => {
    const unit = String(row.unit_code ?? "");
    return [
      {
        label: `Linha ${index + 1} · físico integral`,
        value: formatExactQuantity(String(row.physical_quantity ?? ""), unit || null),
      },
      {
        label: `Linha ${index + 1} · não reservado integral`,
        value: formatExactQuantity(
          String(row.unreserved_quantity ?? row.available_quantity ?? ""),
          unit || null,
        ),
      },
      {
        label: `Linha ${index + 1} · elegível integral`,
        value: formatExactQuantity(String(row.eligible_quantity ?? ""), unit || null),
      },
    ];
  });

  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Estoque</h1>
            <p className="lede">
              Totais só na mesma unidade. Físico e reservado vêm do saldo. Não reservado é físico menos
              reserva. Impedido é a parte não reservada inelegível (bloqueado, quarentena ou vencido).
              Disponível para produção exclui o impedido. Em trânsito não entra no físico.
            </p>
          </div>
        </div>
        {totals.length === 0 ? (
          <EmptyState>Não há saldos nesta organização.</EmptyState>
        ) : (
          totals.map((group) => (
            <section key={group.unit} className="section" aria-label={`Totais em ${group.unit}`}>
              <h2>Unidade: {group.unit}</h2>
              <p className="meta">{pluralize(group.lines, "posição", "posições")}</p>
              <div className="cards">
                <article className="card">
                  <h3>Físico</h3>
                  <p>{formatOperationalQuantity(String(group.physical), group.unit)}</p>
                </article>
                <article className="card">
                  <h3>Reservado</h3>
                  <p>{formatOperationalQuantity(String(group.reserved), group.unit)}</p>
                </article>
                <article className="card">
                  <h3>Não reservado</h3>
                  <p>{formatOperationalQuantity(String(group.unreserved), group.unit)}</p>
                </article>
                <article className="card">
                  <h3>Impedido</h3>
                  <p>{formatOperationalQuantity(String(group.impeded), group.unit)}</p>
                </article>
                <article className="card">
                  <h3>Disponível para produção</h3>
                  <p>{formatOperationalQuantity(String(group.eligible), group.unit)}</p>
                </article>
              </div>
              <p className="meta">
                Impedido está contido no não reservado. Disponível para produção = não reservado −
                impedido.
              </p>
            </section>
          ))
        )}
        <div className="cards">
          <article className="card">
            <h2>Em trânsito</h2>
            <p>Pedidos emitidos e ainda não recebidos.</p>
          </article>
        </div>
        <TechnicalAuditDetails
          title="Valores integrais dos saldos"
          purpose="Quantidades com precisão integral para auditoria. Não alteram o valor armazenado."
          rows={exactRows}
        />
        {hasPermission("inventory.read") ? (
          <p>
            <Link className="primary" to="/componentes/estoque/posicao">
              Abrir posição
            </Link>
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function InventoryPositionPage() {
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const lotFilter = (params.get("lot") ?? "").trim();
  const [reloadToken, setReloadToken] = useState(0);
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: Row[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const prevOrg = useRef(orgId);

  const clearLotFilter = useCallback(() => {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("lot");
        return next;
      },
      { replace: true },
    );
  }, [setParams]);

  useEffect(() => {
    if (prevOrg.current !== orgId) {
      prevOrg.current = orgId;
      if (lotFilter) clearLotFilter();
    }
  }, [orgId, lotFilter, clearLotFilter]);

  useEffect(() => {
    if (!orgId) return;
    let alive = true;
    setState({ kind: "carregando" });
    api
      .listInventory("/inventory/balances")
      .then((body) => {
        if (!alive) return;
        setState({ kind: "ok", items: body.items });
      })
      .catch((error) => {
        if (!alive) return;
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, orgId, reloadToken]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") {
    return <ErrorState error={state.error} onRetry={() => setReloadToken((n) => n + 1)} />;
  }

  const filtered = lotFilter
    ? state.items.filter((row) => String(row.lot_code ?? "") === lotFilter)
    : state.items;
  const filterMiss = Boolean(lotFilter) && filtered.length === 0;

  return (
    <div className="stage">
      <div>
        <h1>Posição de estoque</h1>
        <p className="lede">
          Tabela por item, local e lote. Não reservado ≠ disponível para produção. Sem valor contábil.
        </p>
        {lotFilter ? (
          <p className="meta" role="status">
            Filtro: lote <strong>{lotFilter}</strong>
            {" · "}
            <button type="button" className="ghost" onClick={clearLotFilter}>
              Limpar filtro
            </button>
          </p>
        ) : null}
        {filterMiss ? (
          <EmptyState>
            Lote {lotFilter} não encontrado nesta organização. Limpe o filtro ou escolha outro lote.
          </EmptyState>
        ) : null}
        {!filterMiss && filtered.length === 0 ? (
          <EmptyState>Não há registros nesta organização.</EmptyState>
        ) : null}
        {filtered.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>
                {lotFilter
                  ? `Posição do lote ${lotFilter}`
                  : "Posição reconciliável com o histórico de movimentos"}
              </caption>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Local</th>
                  <th>Lote</th>
                  <th>Situação</th>
                  <th>Físico</th>
                  <th>Reservado</th>
                  <th>Não reservado</th>
                  <th>Disponível para produção</th>
                  <th>Unidade</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={String(row.id)}>
                    <td>{String(row.item_label || "item sem nome")}</td>
                    <td>{String(row.location_label || "local sem nome")}</td>
                    <td>{String(row.lot_code || "lote sem código")}</td>
                    <td>
                      <StatusBadge
                        tone={tone(String(row.lot_status || "available"))}
                        label={
                          row.lot_status
                            ? statusLabel(String(row.lot_status))
                            : eligibilitySurfaceLabel(row)
                        }
                      />
                      <span className="meta"> {eligibilitySurfaceLabel(row)}</span>
                    </td>
                    <td>{qty(row.physical_quantity, row.unit_code)}</td>
                    <td>{qty(row.reserved_quantity, row.unit_code)}</td>
                    <td>{qty(row.unreserved_quantity ?? row.available_quantity, row.unit_code)}</td>
                    <td>{qty(row.eligible_quantity, row.unit_code)}</td>
                    <td>{String(row.unit_code || "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function InventoryLotsPage() {
  const { hasPermission } = useOrganization();
  return (
    <Screen
      title="Lotes e validade"
      lede={
        hasPermission("inventory.lot.manage")
          ? "Lote vencido, bloqueado ou em quarentena não é sugerido no FEFO sem override auditável. Alteração de status exige motivo na API."
          : "Lote vencido, bloqueado ou em quarentena não é sugerido no FEFO sem override auditável."
      }
      path="/inventory/lots"
    >
      {(items, _reload, asOf) => {
        const referenceNote = demoExpiryReferenceNote(config.demoMode, asOf);
        return (
        <>
          {referenceNote ? (
            <p className="meta" role="note">
              {referenceNote}
            </p>
          ) : null}
          <div className="table-wrap">
            <table>
              <caption>Validade e elegibilidade por lote</caption>
              <thead>
                <tr>
                  <th>Lote</th>
                  <th>Ingrediente</th>
                  <th>Local</th>
                  <th>Situação</th>
                  <th>Físico</th>
                  <th>Reservado</th>
                  <th>Disponível para produção</th>
                  <th>Validade</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => {
                  const code = String(row.internal_lot_code || "");
                  const unit = row.unit_code;
                  return (
                    <tr key={String(row.id)}>
                      <td>
                        <strong>{code || "lote sem código"}</strong>
                      </td>
                      <td>{String(row.item_label || "—")}</td>
                      <td>{String(row.location_label || "—")}</td>
                      <td>
                        <StatusBadge
                          tone={tone(String(row.status))}
                          label={statusLabel(String(row.status))}
                        />
                      </td>
                      <td>{qty(row.physical_quantity, unit)}</td>
                      <td>{qty(row.reserved_quantity, unit)}</td>
                      <td>{qty(row.eligible_quantity, unit)}</td>
                      <td>
                        {formatExpiryCaption(
                          row.expires_on == null ? null : String(row.expires_on),
                          asOf,
                        )}
                      </td>
                      <td>
                        {code ? (
                          <Link
                            to={positionLotHref(code)}
                            aria-label={`Abrir posição relacionada ao lote ${code}`}
                          >
                            Posição
                          </Link>
                        ) : (
                          <Link to="/componentes/estoque/posicao">Posição</Link>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
        );
      }}
    </Screen>
  );
}

export function InventoryReservationsPage() {
  return (
    <Screen
      title="Reservas"
      lede="Reserva compromete saldo livre sem alterar o físico. Ordem anterior à política exige adoção humana explícita."
      path="/inventory/reservations"
    >
      {(items) => (
        <div className="table-wrap">
          <table>
            <caption>Reservas por ordem e ingrediente</caption>
            <thead>
              <tr>
                <th>Ordem</th>
                <th>Item</th>
                <th>Necessário</th>
                <th>Reservado</th>
                <th>Falta</th>
                <th>Situação</th>
                <th>Contexto</th>
                <th>Alocações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const orderCode = String(row.order_public_code || "");
                const unit = row.unit_code;
                const allocations = Array.isArray(row.allocations) ? (row.allocations as Row[]) : [];
                return (
                  <tr key={String(row.id)}>
                    <td>
                      {orderCode ? (
                        <Link to={`/ordens/${String(row.production_order_id)}`}>{orderCode}</Link>
                      ) : (
                        "ordem sem código"
                      )}
                    </td>
                    <td>{String(row.item_label || "item sem nome")}</td>
                    <td>{qty(row.required_quantity, unit)}</td>
                    <td>{qty(row.reserved_quantity, unit)}</td>
                    <td>{qty(row.shortage_quantity, unit)}</td>
                    <td>
                      <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
                    </td>
                    <td>
                      {row.adopted ? (
                        <details>
                          <summary>{historicalAdoptionCaption(true)}</summary>
                          <p className="meta">{historicalAdoptionHelp()}</p>
                        </details>
                      ) : (
                        <span className="meta">Reserva operacional</span>
                      )}
                    </td>
                    <td>
                      {allocations.length === 0 ? (
                        <span className="meta">Sem lote alocado</span>
                      ) : (
                        <ul className="meta">
                          {allocations.map((alloc) => {
                            const lotCode = String(alloc.lot_code || "");
                            return (
                              <li key={`${alloc.lot_id}-${alloc.location_id}`}>
                                {lotCode ? (
                                  <Link
                                    to={positionLotHref(lotCode)}
                                    aria-label={`Abrir posição do lote ${lotCode}`}
                                  >
                                    {lotCode}
                                  </Link>
                                ) : (
                                  "lote"
                                )}{" "}
                                · {String(alloc.location_label || "local")} · {qty(alloc.quantity, unit)}
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Screen>
  );
}

export function InventoryMovementsPage() {
  return (
    <Screen
      title="Movimentações"
      lede="Histórico append-only. Erro se corrige com reversão, nunca com edição."
      path="/inventory/movements"
    >
      {(items) => (
        <div className="table-wrap">
          <table>
            <caption>Movimentos reconciliáveis com item, lote e local</caption>
            <thead>
              <tr>
                <th>Data e hora</th>
                <th>Tipo</th>
                <th>Item</th>
                <th>Lote</th>
                <th>Local</th>
                <th>Quantidade</th>
                <th>Documento</th>
                <th>Origem</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const lotCode = row.lot_code == null ? "" : String(row.lot_code);
                const unknownType = !MOVEMENT_TYPE_LABEL[String(row.movement_type || "")];
                const unknownOrigin = !MOVEMENT_ORIGIN_LABEL[String(row.origin_type || "")];
                return (
                  <tr key={String(row.id)}>
                    <td>{formatDateTime(String(row.effective_at || row.created_at || ""))}</td>
                    <td>{movementTypeLabel(String(row.movement_type))}</td>
                    <td>{String(row.item_label || "item sem nome")}</td>
                    <td>{lotCode || "—"}</td>
                    <td>{locationPassageLabel(row.from_location_label, row.to_location_label)}</td>
                    <td>
                      {formatSignedMovementQuantity(
                        row.canonical_quantity ?? row.quantity,
                        row.sign,
                        row.unit_code,
                      )}
                    </td>
                    <td>{String(row.document_label || "—")}</td>
                    <td>
                      {movementOriginLabel(String(row.origin_type))}
                      {row.reverses_id ? <span className="meta"> · reversão</span> : null}
                    </td>
                    <td>
                      {lotCode ? (
                        <Link
                          to={positionLotHref(lotCode)}
                          aria-label={`Abrir posição do lote ${lotCode}`}
                        >
                          Posição
                        </Link>
                      ) : (
                        <Link to="/componentes/estoque/posicao">Posição</Link>
                      )}
                      {unknownType || unknownOrigin || row.content_hash ? (
                        <TechnicalAuditDetails
                          rows={[
                            {
                              label: "Tipo técnico",
                              value: String(row.movement_type || "—"),
                              copyable: true,
                            },
                            {
                              label: "Origem técnica",
                              value: String(row.origin_type || "—"),
                              copyable: true,
                            },
                            {
                              label: "Hash",
                              value: String(row.content_hash || "—"),
                              copyable: true,
                            },
                            {
                              label: "Autor",
                              value: String(row.actor_label || "—"),
                            },
                          ]}
                        />
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Screen>
  );
}

export function InventoryPicksPage() {
  const { active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const { state, load } = useItems("/inventory/picks");
  const [selectedPickId, setSelectedPickId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedPickId(null);
  }, [orgId]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  const selectedPick =
    selectedPickId == null
      ? state.items[0] || null
      : state.items.find((row) => String(row.id) === selectedPickId) || null;

  return (
    <div className="stage">
      <div>
        <h1>Separação</h1>
        <p className="lede">
          Consulta e impressão das listas confirmadas. Abrir esta tela não altera estoque.
        </p>
        <p className="meta" role="note">
          Nesta demonstração, você pode consultar e imprimir separações já confirmadas. A preparação
          de uma nova separação — necessidades, sugestão de lotes, revisão e confirmação — ainda não
          está disponível nesta tela.
        </p>
        {state.items.length === 0 ? <EmptyState>Não há listas de separação.</EmptyState> : null}
        {state.items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Listas de separação</caption>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Ordem</th>
                  <th>Produto</th>
                  <th>Situação</th>
                  <th>Linhas</th>
                  <th>Data</th>
                  <th>Responsável</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {state.items.map((row) => (
                  <tr key={String(row.id)}>
                    <td>
                      <strong>{String(row.public_code)}</strong>
                    </td>
                    <td>
                      {row.order_public_code ? (
                        <Link to={`/ordens/${String(row.production_order_id)}`}>
                          {String(row.order_public_code)}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{String(row.product_label || "—")}</td>
                    <td>
                      <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
                    </td>
                    <td>{String(row.line_count ?? (Array.isArray(row.lines) ? row.lines.length : 0))}</td>
                    <td>{formatDateTime(String(row.created_at || ""))}</td>
                    <td>{String(row.created_by_label || "—")}</td>
                    <td>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => setSelectedPickId(String(row.id))}
                      >
                        Detalhe
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {selectedPick ? (
          <section
            className="pick-print-area"
            aria-label={`Detalhe da separação ${String(selectedPick.public_code)}`}
          >
            <h2>{String(selectedPick.public_code)}</h2>
            <p className="meta">
              Ordem {String(selectedPick.order_public_code || "—")} · Produto{" "}
              {String(selectedPick.product_label || "—")} ·{" "}
              <StatusBadge
                tone={tone(String(selectedPick.status))}
                label={statusLabel(String(selectedPick.status))}
              />
            </p>
            <div className="table-wrap">
              <table>
                <caption>Linhas confirmadas</caption>
                <thead>
                  <tr>
                    <th>Ingrediente</th>
                    <th>Quantidade</th>
                    <th>Lote</th>
                    <th>Local</th>
                    <th>Sugestão FEFO</th>
                    <th>Observação</th>
                  </tr>
                </thead>
                <tbody>
                  {(Array.isArray(selectedPick.lines) ? (selectedPick.lines as Row[]) : []).map((line) => (
                    <tr key={String(line.id || line.lot_id)}>
                      <td>{String(line.item_label || "—")}</td>
                      <td>{qty(line.quantity, line.unit_code)}</td>
                      <td>
                        {line.lot_code ? (
                          <Link
                            to={positionLotHref(String(line.lot_code))}
                            aria-label={`Abrir posição do lote ${String(line.lot_code)}`}
                          >
                            {String(line.lot_code)}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>{String(line.location_label || "—")}</td>
                      <td>
                        {line.suggested ? "Sugerido" : "Manual"}
                        {line.substituted ? " · substituído" : ""}
                      </td>
                      <td>{String(line.reason || "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="meta">Conferência humana: ________________________ Data: ____/____/________</p>
            <button type="button" className="ghost no-print" onClick={() => window.print()}>
              Imprimir lista
            </button>
          </section>
        ) : null}
      </div>
    </div>
  );
}

export function InventoryCountsPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useItems("/inventory/counts");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Inventários</h1>
        <p className="lede">
          Contagem física com corte, escopo congelado e ajuste só por movimento. Reabertura é proibida.
        </p>
        {state.items.length === 0 ? <EmptyState>Não há sessões de inventário.</EmptyState> : null}
        <ul>
          {state.items.map((row) => (
            <li key={String(row.id)}>
              {String(row.public_code)}{" "}
              <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
              {Array.isArray(row.variances)
                ? row.variances.map((item) => (
                    <span key={String((item as Row).scope_id)} className="meta">
                      {" "}
                      divergência {qty((item as Row).variance, (item as Row).unit_code)}
                    </span>
                  ))
                : null}
              {hasPermission("inventory.count.approve") && String(row.status) !== "closed" ? (
                <button
                  type="button"
                  className="primary"
                  onClick={() =>
                    api
                      .catalogCommand(`/inventory/counts/${row.id}/approve`, {
                        ifMatch: Number(row.row_version),
                      })
                      .then(load)
                      .catch(load)
                  }
                >
                  Aprovar e ajustar
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      <CountMentor step={state.items.length ? 3 : 0} />
    </div>
  );
}

export function ProcurementNeedsPage() {
  const { api, hasPermission, active } = useOrganization();
  const { state, reload } = useAsyncNeeds(api, active?.organization_id ?? null);
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={reload} />;
  if (state.kind === "carregando" && hasPermission("procurement.read")) return <LoadingState />;
  const items = state.kind === "ok" ? state.items : [];
  return (
    <div className="stage">
      <div>
        <h1>Necessidades</h1>
        <p className="lede">Sugestão determinística. Não há compra automática nem previsão por IA.</p>
        {items.length === 0 ? (
          <EmptyState>Não há necessidade calculada ou faltam dados explícitos.</EmptyState>
        ) : null}
        <ul>
          {items.map((row) => (
            <li key={String(row.inventory_item_id)}>
              {String(row.item_label || "item sem nome")} · sugerido{" "}
              {qty(row.suggested_quantity, row.unit_code)}
              {Array.isArray(row.gaps) && row.gaps.length > 0 ? (
                <span className="meta"> · lacunas: {(row.gaps as unknown[]).map(String).join(", ")}</span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      <PurchaseMentor step={0} />
    </div>
  );
}

function useAsyncNeeds(api: ReturnType<typeof useOrganization>["api"], orgId: string | null) {
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: Row[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const reload = useCallback(() => {
    setState({ kind: "carregando" });
    api
      .catalogCommand<{ data: Row }>("/inventory/replenishment", { body: { horizon_days: 7 } })
      .then((body) => setState({ kind: "ok", items: (body.data?.items as Row[]) || [] }))
      .catch((error) => {
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  }, [api]);
  useEffect(() => {
    if (!orgId) return;
    let alive = true;
    setState({ kind: "carregando" });
    api
      .catalogCommand<{ data: Row }>("/inventory/replenishment", { body: { horizon_days: 7 } })
      .then((body) => {
        if (!alive) return;
        setState({ kind: "ok", items: (body.data?.items as Row[]) || [] });
      })
      .catch((error) => {
        if (!alive) return;
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, orgId]);
  return { state, reload };
}

export function ProcurementListPage({
  title,
  path,
  lede,
}: {
  title: string;
  path: string;
  lede: string;
}) {
  const { hasPermission } = useOrganization();
  const showPrice = hasPermission("supplier.price.record") || hasPermission("procurement.order.manage");
  return (
    <Screen title={title} lede={lede} path={path}>
      {(items) => (
        <ul>
          {items.map((row) => (
            <li key={String(row.id)}>
              {String(row.public_code || "código ausente")}{" "}
              {row.status ? (
                <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
              ) : null}
              {row.supplier_name ? <span className="meta"> {String(row.supplier_name)}</span> : null}
              {showPrice && row.items && Array.isArray(row.items)
                ? (row.items as Row[]).map((item) =>
                    item.unit_price ? (
                      <span key={String(item.id)} className="meta">
                        {" "}
                        {String(item.unit_price)}
                      </span>
                    ) : null,
                  )
                : null}
            </li>
          ))}
        </ul>
      )}
    </Screen>
  );
}

export function ProcurementQuotesPage() {
  const { api } = useOrganization();
  const { state, load } = useItems("/procurement/quotations");
  const [compared, setCompared] = useState<Row[]>([]);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Cotações</h1>
        <p className="lede">Comparação por preço unitário e prazo. Nenhuma escolha automática de fornecedor.</p>
        {state.items.length === 0 ? <EmptyState>Não há cotações registradas.</EmptyState> : null}
        <ul>
          {state.items.map((row) => (
            <li key={String(row.id)}>
              fornecedor {String(row.supplier_name || "sem nome")} · prazo{" "}
              {String(row.lead_time_days ?? "ausente")}
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="primary"
          onClick={() => {
            const first = state.items[0]?.items as Row[] | undefined;
            const itemId = first?.[0]?.inventory_item_id;
            if (!itemId) return;
            api.listInventory("/procurement/quotations/compare", { inventory_item_id: String(itemId) }).then((body) => {
              setCompared(body.items);
            });
          }}
        >
          Comparar
        </button>
        {compared.length ? (
          <table>
            <caption>Comparação determinística</caption>
            <thead>
              <tr>
                <th>Fornecedor</th>
                <th>Preço unitário</th>
                <th>Prazo</th>
                <th>Escolhido</th>
              </tr>
            </thead>
            <tbody>
              {compared.map((row) => (
                <tr key={String(row.quotation_id)}>
                  <td>{String(row.supplier_name || "sem nome")}</td>
                  <td>{String(row.unit_price)}</td>
                  <td>{String(row.lead_time_days ?? "ausente")}</td>
                  <td>{row.chosen ? "não automático" : "não"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
      <PurchaseMentor step={5} />
    </div>
  );
}
