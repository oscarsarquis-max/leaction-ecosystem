import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import type {
  Envelope,
  FiscalDocument,
  FiscalDocumentItem,
  FiscalMatchBody,
  IngredientPage,
} from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDate, formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  FISCAL_CHECK_LABEL,
  fiscalAttachmentLabel,
  fiscalCheckLabel,
  fiscalCheckTone,
  fiscalDocumentTitle,
  fiscalItemTitle,
  fiscalMatchLabel,
  fiscalMatchTone,
  fiscalMoney,
  fiscalNextActionLabel,
  fiscalOriginLabel,
  fiscalProgressSentence,
  fiscalQuantityLabel,
  fiscalStatusLabel,
  fiscalStatusTone,
  fiscalStockLabel,
  fiscalSupplierLabel,
  fiscalSupplierRegistrationLabel,
  formatAccessKey,
  formatTaxId,
} from "../language/fiscal";
import { useCommand } from "../ops/useCommand";
import {
  canCheckFiscalItem,
  canConfirmFiscalReceipt,
  canMatchFiscalItem,
  canReadFiscalPrice,
} from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

type CheckForm = {
  received_quantity: string;
  result: string;
  lot_code: string;
  expires_on: string;
  notes: string;
};

const EMPTY_CHECK: CheckForm = {
  received_quantity: "",
  result: "ok",
  lot_code: "",
  expires_on: "",
  notes: "",
};

type StorageLocation = { id: string; display_name: string; status: string };

export function FiscalDocumentPage() {
  const { documentId } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();

  const [checkingItemId, setCheckingItemId] = useState<string | null>(null);
  const [checkForm, setCheckForm] = useState<CheckForm>(EMPTY_CHECK);
  const [locationId, setLocationId] = useState("");
  const [acceptDivergence, setAcceptDivergence] = useState(false);

  const { state, reload } = useAsyncResource<Envelope<FiscalDocument>>(
    () => api.getFiscalDocument(documentId!),
    [api, documentId, orgId],
    Boolean(orgId && documentId),
  );

  const document = state.kind === "ok" ? state.data.data : null;
  const canMatch = canMatchFiscalItem(hasPermission);
  const canCheck = canCheckFiscalItem(hasPermission);
  const canConfirm = canConfirmFiscalReceipt(hasPermission);
  // A API declara se este perfil recebeu os campos de custo; a permissão só evita pedir à toa.
  const showCosts = document ? document.cost_access : canReadFiscalPrice(hasPermission);

  const { state: ingredientsState } = useAsyncResource<IngredientPage>(
    () => api.listIngredients({ limit: "50", offset: "0" }),
    [api, orgId],
    Boolean(orgId) && canMatch && hasPermission("ingredient.read"),
  );
  const ingredients = ingredientsState.kind === "ok" ? ingredientsState.data.items : [];

  const { state: locationsState } = useAsyncResource<{ items: StorageLocation[] }>(
    () => api.listInventory<StorageLocation>("/inventory/locations"),
    [api, orgId],
    Boolean(orgId) && canConfirm && hasPermission("inventory.read"),
  );
  const locations = locationsState.kind === "ok" ? locationsState.data.items : [];
  const usableLocations = locations.filter((row) => row.status !== "inactive");

  useEffect(() => {
    if (!locationId && usableLocations.length > 0) setLocationId(usableLocations[0].id);
  }, [locationId, usableLocations]);

  async function decideMatch(item: FiscalDocumentItem, body: FiscalMatchBody) {
    if (!document || command.pending) return;
    try {
      await command.run(`fiscal-match:${item.id}:${body.target_type}:${body.target_id}`, (key) =>
        api.matchFiscalItem(document.id, item.id, body, key),
      );
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  async function submitCheck(event: FormEvent<HTMLFormElement>, item: FiscalDocumentItem) {
    event.preventDefault();
    const quantity = checkForm.received_quantity.trim();
    if (!document || command.pending || !quantity) return;
    try {
      await command.run(`fiscal-physical:${item.id}:${quantity}`, (key) =>
        api.recordFiscalPhysical(
          document.id,
          item.id,
          {
            received_quantity: quantity,
            unit_code: item.unit_code,
            result: checkForm.result,
            supplier_lot_code: checkForm.lot_code.trim() || null,
            expires_on: checkForm.expires_on || null,
            notes: checkForm.notes.trim() || null,
          },
          key,
        ),
      );
      setCheckingItemId(null);
      setCheckForm(EMPTY_CHECK);
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  async function confirmReceipt() {
    if (!document || command.pending || !locationId) return;
    try {
      await command.run(`fiscal-confirm:${document.id}:${locationId}`, (key) =>
        api.confirmFiscalReceipt(
          document.id,
          { inventory_location_id: locationId, accept_divergence: acceptDivergence },
          key,
        ),
      );
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  function startCheck(item: FiscalDocumentItem) {
    setCheckingItemId(item.id);
    setCheckForm({
      ...EMPTY_CHECK,
      received_quantity: item.physical?.received_quantity ?? item.invoiced_quantity ?? "",
      result: item.physical?.result ?? "ok",
      lot_code: item.physical?.lot_code ?? "",
      expires_on: item.physical?.expires_on ?? "",
      notes: item.physical?.notes ?? "",
    });
  }

  const title = document ? fiscalDocumentTitle(document) : "Entrada fiscal";
  const pending = document?.pending_reasons ?? [];

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        entityLabel={title}
        status={document ? fiscalStatusLabel(document.status) : undefined}
        next={document ? fiscalNextActionLabel(document.next_action, document.next_action_label) : undefined}
      />
      <div>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => reload()} /> : null}
        {document ? (
          <>
            <div className="page-head">
              <div>
                <h1>{title}</h1>
              </div>
            </div>
            <p className="lede">
              <StatusBadge
                tone={fiscalStatusTone(document.status)}
                label={document.status_label?.trim() || fiscalStatusLabel(document.status)}
              />{" "}
              {fiscalSupplierLabel(document.supplier)} · {fiscalProgressSentence(document)}
            </p>

            {(document.operational_notes ?? []).length > 0 ? (
              <section className="panel">
                <h2>O que ainda falta nesta fase</h2>
                <ul>
                  {(document.operational_notes ?? []).map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="panel">
              <h2>Qual é o documento</h2>
              <p>
                <strong>Identificação: </strong>
                {title}
              </p>
              <p>
                <strong>Chave de acesso: </strong>
                {formatAccessKey(document.access_key)}
              </p>
              <p>
                <strong>Emissão: </strong>
                {formatDate(document.issued_on)}
              </p>
              <p>
                <strong>Origem do registro: </strong>
                {fiscalOriginLabel(document.origin)}
              </p>
              <p>
                <strong>Anexos: </strong>
                {document.attachments.length === 0
                  ? "Nenhum arquivo anexado a esta entrada."
                  : null}
              </p>
              {document.attachments.length > 0 ? (
                <ul className="fiscal-attachments">
                  {document.attachments.map((attachment) => (
                    <li key={attachment.id}>
                      {attachment.filename?.trim() || fiscalAttachmentLabel(attachment.kind)}
                      <span className="meta">
                        {" "}
                        · {fiscalAttachmentLabel(attachment.kind)} · enviado em{" "}
                        {formatDateTime(attachment.uploaded_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {document.attachments.length > 0 ? (
                <p className="meta">
                  Os arquivos ficam guardados no armazenamento privado da organização e não abrem por
                  endereço público.
                </p>
              ) : null}
            </section>

            <section className="panel">
              <h2>Quem forneceu</h2>
              <p>
                <strong>Fornecedor: </strong>
                {document.supplier?.id && hasPermission("supplier.read") ? (
                  <Link to={`/componentes/fornecedores/${document.supplier.id}`}>
                    {fiscalSupplierLabel(document.supplier)}
                  </Link>
                ) : (
                  fiscalSupplierLabel(document.supplier)
                )}
              </p>
              <p>
                <strong>CNPJ: </strong>
                {formatTaxId(document.supplier?.tax_id)}
              </p>
              <p>{fiscalSupplierRegistrationLabel(document.supplier)}</p>
            </section>

            <section className="panel">
              <h2>O que foi comprado e o que corresponde na Panne</h2>
              <p className="meta">
                Cada linha da nota precisa apontar para um item do cadastro antes de virar estoque.
              </p>
              {document.items.length === 0 ? (
                <p>Este documento ainda não tem itens informados.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <caption>Itens do documento e correspondência com o cadastro</caption>
                    <thead>
                      <tr>
                        <th>Item do fornecedor</th>
                        <th>Quantidade na nota</th>
                        <th>Corresponde na Panne</th>
                        <th>Situação da correspondência</th>
                        <th>Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {document.items.map((item) => (
                        <tr key={item.id}>
                          <td>
                            {fiscalItemTitle(item)}
                            {item.supplier_sku ? (
                              <span className="meta"> · referência {item.supplier_sku}</span>
                            ) : null}
                          </td>
                          <td>{fiscalQuantityLabel(item.invoiced_quantity, item.unit_code)}</td>
                          <td>
                            {matchTargetLabel(item)}
                            {item.match.suggestion_reason ? (
                              <span className="meta"> · {item.match.suggestion_reason}</span>
                            ) : null}
                          </td>
                          <td>
                            <StatusBadge
                              tone={fiscalMatchTone(item.match.status)}
                              label={fiscalMatchLabel(item.match.status)}
                            />
                          </td>
                          <td>
                            {canMatch ? (
                              <MatchActions
                                item={item}
                                ingredients={ingredients}
                                pending={command.pending}
                                onDecide={(body) => void decideMatch(item, body)}
                              />
                            ) : (
                              <span className="meta">Correspondência oculta neste papel.</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel">
              <h2>O que realmente chegou</h2>
              <p className="meta">
                Registre a conferência física de cada item. Diferença entre nota e mercadoria vira
                divergência explícita, nunca ajuste silencioso.
              </p>
              {document.items.length === 0 ? (
                <p>Sem itens para conferir nesta entrada.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <caption>Conferência física por item</caption>
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Quantidade recebida</th>
                        <th>Lote</th>
                        <th>Validade</th>
                        <th>Resultado</th>
                        <th>Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {document.items.map((item) => (
                        <tr key={item.id}>
                          <td>{fiscalItemTitle(item)}</td>
                          <td>
                            {fiscalQuantityLabel(
                              item.physical?.received_quantity,
                              item.physical?.unit_code ?? item.unit_code,
                            )}
                          </td>
                          <td>{item.physical?.lot_code?.trim() || "Sem lote informado"}</td>
                          <td>{formatDate(item.physical?.expires_on)}</td>
                          <td>
                            <StatusBadge
                              tone={fiscalCheckTone(checkResultOf(item))}
                              label={fiscalCheckLabel(checkResultOf(item))}
                            />
                          </td>
                          <td>
                            {!canCheck ? (
                              <span className="meta">Conferência oculta neste papel.</span>
                            ) : item.match.status === "matched" ? (
                              <button
                                type="button"
                                className="ghost"
                                disabled={command.pending}
                                onClick={() => startCheck(item)}
                              >
                                Registrar conferência
                              </button>
                            ) : (
                              <span className="meta">
                                Faça a correspondência deste item antes de conferir.
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {checkingItemId
                ? (() => {
                    const item = document.items.find((row) => row.id === checkingItemId);
                    if (!item) return null;
                    return (
                      <form className="fiscal-check-form" onSubmit={(event) => void submitCheck(event, item)}>
                        <h3>Conferência de {fiscalItemTitle(item)}</h3>
                        <label>
                          Quantidade recebida
                          <input
                            value={checkForm.received_quantity}
                            inputMode="decimal"
                            onChange={(event) =>
                              setCheckForm((current) => ({
                                ...current,
                                received_quantity: event.target.value,
                              }))
                            }
                            disabled={command.pending}
                          />
                        </label>
                        <label>
                          Resultado da conferência
                          <select
                            value={checkForm.result}
                            onChange={(event) =>
                              setCheckForm((current) => ({ ...current, result: event.target.value }))
                            }
                            disabled={command.pending}
                          >
                            {Object.keys(FISCAL_CHECK_LABEL).map((code) => (
                              <option key={code} value={code}>
                                {fiscalCheckLabel(code)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Lote do fornecedor
                          <input
                            value={checkForm.lot_code}
                            autoComplete="off"
                            onChange={(event) =>
                              setCheckForm((current) => ({ ...current, lot_code: event.target.value }))
                            }
                            disabled={command.pending}
                          />
                        </label>
                        <label>
                          Validade
                          <input
                            type="date"
                            value={checkForm.expires_on}
                            onChange={(event) =>
                              setCheckForm((current) => ({ ...current, expires_on: event.target.value }))
                            }
                            disabled={command.pending}
                          />
                        </label>
                        <label>
                          Observação da conferência
                          <textarea
                            value={checkForm.notes}
                            onChange={(event) =>
                              setCheckForm((current) => ({ ...current, notes: event.target.value }))
                            }
                            disabled={command.pending}
                          />
                        </label>
                        <p>
                          <button type="submit" className="primary" disabled={command.pending}>
                            Guardar conferência
                          </button>{" "}
                          <button
                            type="button"
                            className="ghost"
                            disabled={command.pending}
                            onClick={() => setCheckingItemId(null)}
                          >
                            Cancelar
                          </button>
                        </p>
                      </form>
                    );
                  })()
                : null}
            </section>

            <section className="panel">
              <h2>Onde vai ser armazenado</h2>
              {document.stock_applied ? (
                <p>
                  {document.storage_location_label?.trim()
                    || "A mercadoria já foi lançada no estoque desta entrada."}
                </p>
              ) : !canConfirm ? (
                <p>
                  A escolha do local de estoque cabe a quem confirma a entrada.
                </p>
              ) : usableLocations.length === 0 ? (
                <p className="meta" role="status">
                  Nenhum local de estoque disponível. Cadastre um local antes de confirmar a entrada.
                </p>
              ) : (
                <>
                  <label>
                    Local de estoque que vai receber
                    <select
                      value={locationId}
                      onChange={(event) => setLocationId(event.target.value)}
                      disabled={command.pending}
                    >
                      {usableLocations.map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.display_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p className="meta">
                    O saldo entra neste local quando a entrada for confirmada.
                  </p>
                </>
              )}
            </section>

            {showCosts ? (
              <section className="panel">
                <h2>Quanto custou</h2>
                <p>
                  <strong>Total do documento: </strong>
                  {fiscalMoney(document.costs?.document_total ?? document.document_total, document.costs?.currency ?? document.currency)}
                </p>
                <p>
                  <strong>Itens: </strong>
                  {fiscalMoney(document.costs?.items_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Frete: </strong>
                  {fiscalMoney(document.costs?.freight_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Descontos: </strong>
                  {fiscalMoney(document.costs?.discount_total, document.costs?.currency)}
                </p>
                <p>
                  <strong>Tributos destacados: </strong>
                  {fiscalMoney(document.costs?.taxes_total, document.costs?.currency)}
                </p>
                {document.items.some((item) => item.unit_cost != null) ? (
                  <div className="table-wrap">
                    <table>
                      <caption>Custo por item do documento</caption>
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>Custo unitário</th>
                          <th>Custo total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {document.items.map((item) => (
                          <tr key={item.id}>
                            <td>{fiscalItemTitle(item)}</td>
                            <td>{fiscalMoney(item.unit_cost, document.costs?.currency)}</td>
                            <td>{fiscalMoney(item.total_cost, document.costs?.currency)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                <p className="meta">
                  Valor do documento não é preço vigente do ingrediente. O histórico de preço é
                  atualizado na confirmação da entrada.
                </p>
              </section>
            ) : (
              <section className="panel">
                <h2>Quanto custou</h2>
                <p>Valores do documento ficam ocultos para o seu papel.</p>
              </section>
            )}

            <section className="panel">
              <h2>O estoque já foi atualizado</h2>
              <p>
                <StatusBadge
                  tone={document.stock_applied ? "sucesso" : "atencao"}
                  label={document.stock_applied ? "Estoque atualizado" : "Estoque ainda não atualizado"}
                />{" "}
                {fiscalStockLabel(document.stock_applied, document.stock_summary)}
              </p>
              {document.stock_applied && hasPermission("inventory.read") ? (
                <p>
                  <Link className="ghost" to="/componentes/estoque/posicao">
                    Abrir posição de estoque
                  </Link>
                </p>
              ) : null}
            </section>

            <section className="panel">
              <h2>Próxima ação</h2>
              <p>{fiscalNextActionLabel(document.next_action, document.next_action_label)}</p>
              {pending.length > 0 ? (
                <>
                  <p className="meta">Pendências que ainda seguram esta entrada:</p>
                  <ul>
                    {pending.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              {command.error ? (
                <p className="error" role="alert">
                  {command.error.message || "Não foi possível concluir a ação."}
                </p>
              ) : null}
              {canConfirm && !document.stock_applied && document.divergence_count > 0 ? (
                <label>
                  <input
                    type="checkbox"
                    checked={acceptDivergence}
                    onChange={(event) => setAcceptDivergence(event.target.checked)}
                    disabled={command.pending}
                  />{" "}
                  Aceitar as divergências e concluir mesmo assim
                </label>
              ) : null}
              <p>
                {canConfirm && !document.stock_applied ? (
                  <button
                    type="button"
                    className="primary"
                    disabled={command.pending || !locationId || document.items.length === 0}
                    onClick={() => void confirmReceipt()}
                  >
                    Confirmar entrada e atualizar estoque
                  </button>
                ) : null}{" "}
                <Link className="ghost" to="/gestao/compras/entradas">
                  Voltar às entradas fiscais
                </Link>
              </p>
            </section>

            <details className="fiscal-history">
              <summary>Histórico e auditoria desta entrada</summary>
              <p className="meta">
                Registro de quem fez o quê. Correção se faz por novo registro, nunca apagando o
                anterior.
              </p>
              {document.history.length === 0 ? (
                <p>Ainda não há passos registrados nesta entrada.</p>
              ) : (
                <ol className="fiscal-history__list">
                  {document.history.map((event) => (
                    <li key={event.id}>
                      <strong>{event.action_label?.trim() || "Passo registrado"}</strong>
                      <span className="meta">
                        {" "}
                        {formatDateTime(event.occurred_at)}
                        {event.actor_label ? ` · ${event.actor_label}` : ""}
                      </span>
                      {event.detail ? <p>{event.detail}</p> : null}
                    </li>
                  ))}
                </ol>
              )}
              <TechnicalAuditDetails
                rows={[
                  { label: "Identificador da entrada", value: document.id, copyable: true },
                  { label: "Versão de linha", value: String(document.row_version) },
                  { label: "Atualizado em", value: formatDateTime(document.updated_at) },
                ]}
              />
            </details>
          </>
        ) : null}
      </div>
      <aside className="panel">
        <h2>A ordem importa</h2>
        <p>
          Primeiro o documento, depois a correspondência com o cadastro, depois a conferência do que
          chegou. O estoque só se move no último passo.
        </p>
        <p>
          Divergência não bloqueia a operação: ela fica registrada e visível para quem negocia com o
          fornecedor.
        </p>
        <p className="meta">
          Confirmar a entrada cria lote, movimenta saldo e alimenta o histórico de preço de compra.
        </p>
      </aside>
    </div>
  );
}

/**
 * O contrato ainda não devolve o nome do item ligado. Enquanto isso a tela diz o tipo do
 * vínculo em palavras, em vez de mostrar o identificador técnico.
 */
function matchTargetLabel(item: FiscalDocumentItem): string {
  const named = item.match.target_label?.trim();
  if (named) return named;
  if (!item.match.target_id) return "Ainda não escolhido";
  if (item.match.target_kind === "product") return "Produto do cadastro da Panne";
  if (item.match.target_kind === "ingredient") return "Ingrediente do cadastro da Panne";
  return "Item do cadastro da Panne";
}

/** A conferência sem divergência não devolve resultado; a linha existir já significa "ok". */
function checkResultOf(item: FiscalDocumentItem): string | null {
  if (!item.physical) return null;
  return item.physical.result ?? "ok";
}

function MatchActions({
  item,
  ingredients,
  pending,
  onDecide,
}: {
  item: FiscalDocumentItem;
  ingredients: Array<{ id: string; display_name: string }>;
  pending: boolean;
  onDecide: (body: FiscalMatchBody) => void;
}) {
  const suggested =
    item.match.status === "suggested" &&
    (item.match.target_kind === "ingredient" || item.match.target_kind === "product") &&
    item.match.target_id;

  if (item.match.status === "matched") {
    return <span className="meta">Item já ligado ao cadastro.</span>;
  }

  return (
    <div className="fiscal-match-actions">
      {suggested ? (
        <button
          type="button"
          className="primary"
          disabled={pending}
          onClick={() =>
            onDecide({
              target_type: item.match.target_kind as FiscalMatchBody["target_type"],
              target_id: item.match.target_id!,
            })
          }
        >
          Confirmar sugestão
        </button>
      ) : null}
      {ingredients.length > 0 ? (
        <label>
          <span className="visually-hidden">
            Escolher ingrediente para {fiscalItemTitle(item)}
          </span>
          <select
            value=""
            disabled={pending}
            onChange={(event) => {
              if (!event.target.value) return;
              onDecide({ target_type: "ingredient", target_id: event.target.value });
            }}
          >
            <option value="">Escolher no cadastro…</option>
            {ingredients.map((ingredient) => (
              <option key={ingredient.id} value={ingredient.id}>
                {ingredient.display_name}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <span className="meta">Nenhum ingrediente disponível para ligar este item.</span>
      )}
    </div>
  );
}
