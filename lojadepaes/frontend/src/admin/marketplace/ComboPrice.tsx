import { useId, useState, type FormEvent } from "react";
import { formatCents, parseBrlToCents } from "../../lib/money";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { MARKETPLACE_API } from "./labels";

type Props = {
  comboId: string;
  value: number | null | undefined;
  onSaved?: (cents: number | null) => void;
};

function toText(cents: number | null | undefined): string {
  if (cents == null) return "";
  return (cents / 100).toFixed(2).replace(".", ",");
}

/** Preço do pão nesta combo: acordo da Loja com o parceiro. Vazio = preço da vitrine. Só a Loja vê. */
export function ComboPrice({ comboId, value, onSaved }: Props) {
  const id = useId();
  const [text, setText] = useState(toText(value));
  const [saved, setSaved] = useState<number | null>(value ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(false);
    let cents: number | null;
    try {
      cents = parseBrlToCents(text);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "valor inválido");
      return;
    }
    setBusy(true);
    try {
      await adminRequest(`${MARKETPLACE_API}/combos/${encodeURIComponent(comboId)}/price`, {
        method: "PATCH",
        body: JSON.stringify({ house_unit_price_cents: cents }),
      });
      setSaved(cents);
      setOk(true);
      onSaved?.(cents);
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível salvar o preço.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="mkt-combo-price" onSubmit={(event) => void save(event)}>
      <label htmlFor={id}>Preço do pão nesta combo</label>
      <div className="mkt-combo-price-row">
        <span className="mkt-combo-price-prefix" aria-hidden="true">
          R$
        </span>
        <input
          id={id}
          className="mkt-input"
          inputMode="decimal"
          placeholder="preço da vitrine"
          value={text}
          aria-describedby={`${id}-hint`}
          onChange={(event) => {
            setText(event.target.value);
            setOk(false);
          }}
        />
        <Button type="submit" disabled={busy}>
          {busy ? "Salvando…" : "Salvar"}
        </Button>
      </div>
      <p className="mkt-muted" id={`${id}-hint`}>
        {saved == null
          ? "Vazio: o pão sai pelo preço da vitrine. Preencha para o valor negociado neste acordo (por pão, qualquer apresentação)."
          : `Acordo: ${formatCents(saved)} por pão, em qualquer apresentação e quantidade. Apague para voltar ao preço da vitrine.`}
      </p>
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}
        </p>
      ) : null}
      {ok ? (
        <p className="mkt-ok" role="status">
          Preço salvo.
        </p>
      ) : null}
    </form>
  );
}
