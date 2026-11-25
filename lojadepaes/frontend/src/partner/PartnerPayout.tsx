import { useCallback, useEffect, useState } from "react";
import { stampLabel } from "../admin/marketplace/labels";
import type { Partner } from "../admin/marketplace/types";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, partnerApi, type PartnerMpStatus } from "./partnerApi";

type Props = {
  partner: Partner;
  onBack: () => void;
  onChanged: (patch: Pick<Partner, "mp_connected" | "mp_nickname">) => void;
};

const REASONS: Record<string, string> = {
  negado: "Você não autorizou a conexão no Mercado Pago. Quando quiser, tente de novo.",
  expirado: "O tempo para autorizar acabou. Clique em conectar de novo.",
  sem_codigo: "O Mercado Pago não confirmou a autorização. Tente de novo.",
  oauth: "Não conseguimos concluir a conexão com o Mercado Pago. Tente de novo em instantes.",
};

function returnNotice(): { tone: "ok" | "error"; text: string } | null {
  const params = new URLSearchParams(window.location.search);
  const mp = params.get("mp");
  if (mp === "ok") return { tone: "ok", text: "Conta do Mercado Pago conectada. Você já pode confirmar pedidos." };
  if (mp === "erro") {
    const reason = params.get("motivo") ?? "";
    return { tone: "error", text: REASONS[reason] ?? REASONS.oauth };
  }
  return null;
}

/** Recebimento: o parceiro conecta a própria conta do Mercado Pago, onde ficam a conta corrente e o CPF/CNPJ dele. */
export function PartnerPayout({ partner, onBack, onChanged }: Props) {
  const [status, setStatus] = useState<PartnerMpStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmOff, setConfirmOff] = useState(false);
  const [notice] = useState(returnNotice);

  const load = useCallback(async () => {
    setError(null);
    try {
      const next = await partnerApi.mpStatus();
      setStatus(next);
      onChanged({ mp_connected: next.available ? next.connected : null, mp_nickname: next.nickname ?? null });
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível ver o estado do recebimento.");
    }
  }, [onChanged]);

  useEffect(() => {
    void load();
    if (window.location.search) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [load]);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await partnerApi.mpConnect();
      window.location.assign(url);
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível abrir o Mercado Pago agora.");
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError(null);
    try {
      await partnerApi.mpDisconnect();
      setConfirmOff(false);
      await load();
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível desconectar agora.");
    } finally {
      setBusy(false);
    }
  }

  const paused = partner.status === "paused";

  return (
    <section className="ptn-payout">
      <a
        className="mkt-back"
        href="/parceiro"
        onClick={(event) => {
          event.preventDefault();
          onBack();
        }}
      >
        ← Meus produtos
      </a>
      <header className="admin-page-header">
        <div>
          <h1>Recebimento</h1>
          <p>
            O cliente paga a sua parte de cada combo direto na sua conta do Mercado Pago, por Pix ou cartão. A Loja de
            Pães não recebe nem repassa o seu dinheiro.
          </p>
        </div>
      </header>

      {notice ? (
        <p className={notice.tone === "ok" ? "mkt-ok ptn-payout-notice" : "mkt-alert ptn-payout-notice"} role="status">
          {notice.text}
        </p>
      ) : null}
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}

      {status === null && !error ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : null}

      {status && !status.available ? (
        <div className="admin-card ptn-payout-card">
          <p className="mkt-empty-title">O recebimento pelo Mercado Pago abre em breve.</p>
          <p className="mkt-muted">Assim que estiver disponível, você conecta a sua conta aqui, com um clique.</p>
        </div>
      ) : null}

      {status && status.available && status.connected ? (
        <div className="admin-card ptn-payout-card">
          <div className="ptn-payout-state">
            <span className="ptn-payout-dot is-on" aria-hidden="true" />
            <div>
              <p className="ptn-payout-title">Conta conectada</p>
              <p className="mkt-muted">
                {status.nickname ? `Mercado Pago: ${status.nickname}` : "Mercado Pago"}
                {status.connected_at ? ` · desde ${stampLabel(status.connected_at)}` : ""}
              </p>
            </div>
          </div>
          <p className="mkt-muted">
            Para mudar a conta corrente ou o CPF/CNPJ, altere no próprio Mercado Pago. Se trocar de conta, desconecte aqui e
            conecte a nova.
          </p>
          {confirmOff ? (
            <div className="ptn-payout-confirm" role="group" aria-label="Confirmar desconexão">
              <p>Sem conta conectada, você não consegue confirmar pedidos novos. Desconectar mesmo assim?</p>
              <div className="mkt-row">
                <Button disabled={busy} onClick={() => void disconnect()}>
                  {busy ? "Desconectando…" : "Sim, desconectar"}
                </Button>
                <Button variant="primary" onClick={() => setConfirmOff(false)}>
                  Manter conectada
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={() => setConfirmOff(true)}>Desconectar</Button>
          )}
        </div>
      ) : null}

      {status && status.available && !status.connected ? (
        <div className="admin-card ptn-payout-card">
          <div className="ptn-payout-state">
            <span className="ptn-payout-dot" aria-hidden="true" />
            <div>
              <p className="ptn-payout-title">
                {status.status === "error" ? "Reconecte a sua conta" : "Nenhuma conta conectada"}
              </p>
              <p className="mkt-muted">
                {status.status === "error"
                  ? "A autorização do Mercado Pago venceu ou foi retirada. Conecte de novo para continuar recebendo."
                  : "Conecte para confirmar pedidos e receber a sua parte das combos."}
              </p>
            </div>
          </div>
          <ol className="ptn-payout-steps">
            <li>Você vai para o site do Mercado Pago e entra na sua conta (ou cria uma, de graça).</li>
            <li>Autoriza a Loja de Pães a gerar, na sua conta, as cobranças das combos com o seu produto.</li>
            <li>Volta para cá com a conta conectada.</li>
          </ol>
          <Button variant="primary" disabled={busy || paused} onClick={() => void connect()}>
            {busy ? "Abrindo o Mercado Pago…" : "Conectar ao Mercado Pago"}
          </Button>
          {paused ? <p className="mkt-muted">Sua conta está pausada pela Loja de Pães.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
