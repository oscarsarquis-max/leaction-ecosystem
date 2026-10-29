import { FormEvent, useEffect, useState } from "react";
import { ApiError, requestJson } from "../services/http";
import {
  DeliveryAddressFields,
  addressFieldErrors,
  emptyDeliveryAddress,
  type DeliveryAddressInput,
} from "./DeliveryAddressFields";

type PublicDetail = {
  id: string;
  status: string;
  desired_date: string;
  gaps: string[];
  converted: boolean;
  message: string;
  order_href?: string | null;
  delivery_pending?: boolean;
};

function tokenFromSearch(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

function requestIdFromPath(): string {
  const match = window.location.pathname.match(/^\/solicitacao\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function DateRequestCompletePage() {
  const id = requestIdFromPath();
  const token = tokenFromSearch();
  const [detail, setDetail] = useState<PublicDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof DeliveryAddressInput, string>>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [address, setAddress] = useState<DeliveryAddressInput>(emptyDeliveryAddress());

  useEffect(() => {
    if (!id || !token) {
      setError("Este endereço protegido está incompleto.");
      setLoading(false);
      return;
    }
    requestJson<PublicDetail>(`/api/v1/schedule/date-requests/${id}?token=${encodeURIComponent(token)}`)
      .then((data) => {
        setDetail(data);
        setError(null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof ApiError ? reason.message : "Não foi possível abrir a solicitação.");
      })
      .finally(() => setLoading(false));
  }, [id, token]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const invalid = addressFieldErrors(address);
    if (Object.keys(invalid).length) {
      setFieldErrors(invalid);
      setError("Revise os dados de entrega destacados.");
      return;
    }
    setBusy(true);
    setSaved(false);
    try {
      const updated = await requestJson<PublicDetail>(`/api/v1/schedule/date-requests/${id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, ...address }),
      });
      setDetail(updated);
      setFieldErrors({});
      setError(null);
      setSaved(true);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.message : "Não foi possível enviar o endereço.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="checkout-page">
      <h1>Completar solicitação</h1>
      {loading ? <p>Carregando…</p> : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p className="tip" role="status">
          Endereço de entrega salvo.
        </p>
      ) : null}
      {detail ? (
        <>
          <p>{detail.message}</p>
          {detail.gaps.length > 0 ? <p>Ainda falta: {detail.gaps.join("; ")}.</p> : null}
          {detail.order_href && detail.converted ? (
            <div className="checkout-methods">
              <p>Como prefere pagar? Completar o endereço não impede esta etapa.</p>
              <div className="checkout-method-row">
                <a className="primary" href={detail.order_href}>
                  Pagar com Pix
                </a>
                <a className="primary" href={detail.order_href}>
                  Pagar com cartão
                </a>
              </div>
            </div>
          ) : null}
          {detail.order_href ? (
            <p>
              <a className="primary" href={detail.order_href}>
                {detail.converted ? "Acompanhar o pedido" : "Pagar e acompanhar o pedido"}
              </a>
            </p>
          ) : null}
          {detail.converted ? (
            <p className="fornada-note">
              O pedido já foi aceito. Você pode pagar pelo botão acima e completar o endereço aqui
              mesmo. Completar o endereço não muda o aceite, a data nem o total.
            </p>
          ) : null}
          {detail.delivery_pending || (!detail.converted && detail.gaps.length > 0) ? (
            <form className="checkout-form" onSubmit={(event) => void onSubmit(event)} noValidate>
              <DeliveryAddressFields
                value={address}
                onChange={setAddress}
                note={detail.converted ? "accepted" : "checkout"}
                errors={fieldErrors}
              />
              <button className="primary" type="submit" disabled={busy}>
                Salvar endereço de entrega
              </button>
            </form>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
