import { useEffect, useState } from "react";
import { formatCents } from "../lib/money";
import { fetchHouseFidelity } from "./houseFidelityApi";
import type { HouseFidelityStatus } from "./houseFidelity";

export type CreditOfferItem = {
  variant_id: string;
  product_name: string;
  variant_name: string;
  unit_cents: number;
};

type Props = {
  optIn: boolean;
  onOptIn: (value: boolean) => void;
  applyCredit: boolean;
  onApplyCredit: (value: boolean) => void;
  creditVariantId: string;
  onCreditVariantId: (value: string) => void;
  eligibleItems: CreditOfferItem[];
  creditNotice: string | null;
  creditLabel: string | null;
  quoteReady?: boolean;
  queryFailed?: boolean;
  onRetry?: () => void;
};

export function HouseFidelityCheckout({
  optIn,
  onOptIn,
  applyCredit,
  onApplyCredit,
  creditVariantId,
  onCreditVariantId,
  eligibleItems,
  creditNotice,
  creditLabel,
  quoteReady = false,
  queryFailed = false,
  onRetry,
}: Props) {
  const [status, setStatus] = useState<HouseFidelityStatus | null>(null);
  const [failed, setFailed] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);

  function load() {
    setFailed(false);
    fetchHouseFidelity()
      .then(setStatus)
      .catch(() => setFailed(true));
  }

  useEffect(() => {
    load();
  }, []);

  if (failed || queryFailed) {
    return (
      <fieldset className="house-fidelity-checkout">
        <legend>Fidelidade da casa</legend>
        <p>
          Não foi possível consultar a fidelidade agora. Isso não significa que o saldo seja zero. Você
          pode tentar de novo ou seguir a compra sem aplicar crédito.
        </p>
        <button type="button" className="text-button" onClick={() => { load(); onRetry?.(); }}>
          Tentar de novo
        </button>
      </fieldset>
    );
  }

  if (status?.verified) {
    const credits = status.participant?.credits ?? 0;
    return (
      <fieldset className="house-fidelity-checkout">
        <legend>Fidelidade da casa</legend>
        <p>
          {status.name} · CPF {status.cpf_masked}
        </p>
        {credits > 0 ? (
          <div className="house-fidelity-offer">
            <p>
              {credits === 1
                ? "Você tem 1 crédito disponível. Quer usar neste pedido?"
                : `Você tem ${credits} créditos disponíveis. Quer usar 1 neste pedido?`}
            </p>
            <p>Vale um pão de 500 g da vitrine. Focaccias não participam. Frete, se houver, é cobrado à parte.</p>
            {!quoteReady ? (
              <p>Consultando se este pedido comporta o crédito…</p>
            ) : eligibleItems.length === 0 ? (
              <p>
                Este item não participa da fidelidade.{" "}
                <a href="/">Escolher um pão da vitrine</a>
              </p>
            ) : (
              <>
                {eligibleItems.length === 1 ? (
                  <p>
                    O benefício cobre 1 unidade de {eligibleItems[0].product_name} ·{" "}
                    {eligibleItems[0].variant_name}.
                  </p>
                ) : (
                  <fieldset>
                    <legend>Qual pão recebe o crédito?</legend>
                    {eligibleItems.map((item) => (
                      <label key={item.variant_id}>
                        <input
                          type="radio"
                          name="fidelity-credit-item"
                          checked={creditVariantId === item.variant_id}
                          onChange={() => {
                            onCreditVariantId(item.variant_id);
                            setPickError(null);
                          }}
                        />
                        {item.product_name} · {item.variant_name} · {formatCents(item.unit_cents)}
                      </label>
                    ))}
                  </fieldset>
                )}
                {pickError ? (
                  <p className="house-fidelity-error" role="alert">
                    {pickError}
                  </p>
                ) : null}
                <div className="house-fidelity-offer-actions">
                  <button
                    type="button"
                    className="primary"
                    onClick={() => {
                      if (eligibleItems.length > 1 && !creditVariantId) {
                        setPickError("Escolha qual pão de 500 g receberá o crédito.");
                        return;
                      }
                      if (eligibleItems.length === 1) {
                        onCreditVariantId(eligibleItems[0].variant_id);
                      }
                      setPickError(null);
                      onApplyCredit(true);
                    }}
                  >
                    Usar meu crédito
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => {
                      setPickError(null);
                      onApplyCredit(false);
                      onCreditVariantId("");
                    }}
                  >
                    Guardar para depois
                  </button>
                </div>
              </>
            )}
            {applyCredit && creditLabel ? (
              <p>
                Crédito aplicado em {creditLabel}.{" "}
                <button type="button" className="text-button" onClick={() => onApplyCredit(false)}>
                  Retirar do pedido
                </button>
              </p>
            ) : null}
            {creditNotice ? <p role="status">{creditNotice}</p> : null}
          </div>
        ) : (
          <p>{status.participant?.progress_label ?? "Ainda não há crédito disponível."}</p>
        )}
        {status.campaign_active ? (
          <label>
            <input type="checkbox" checked={optIn} onChange={(event) => onOptIn(event.target.checked)} />
            Participar neste pedido. Se A Loja aceitar e o pagamento for confirmado, poderá contar um
            carimbo. O saldo só muda depois do aceite e do pagamento.
          </label>
        ) : null}
      </fieldset>
    );
  }

  return (
    <fieldset className="house-fidelity-checkout">
      <legend>Quer participar das promoções?</legend>
      <p>
        Identifique-se na peça Carimbos da casa se quiser pontuar. Sem cadastro, a compra segue
        normalmente, sem carimbo.
      </p>
      <p>
        <a href="/#fidelidade-cadastro">Quero participar</a>
        {" · "}
        <a href="/#fidelidade">Já tenho cadastro</a>
      </p>
    </fieldset>
  );
}
