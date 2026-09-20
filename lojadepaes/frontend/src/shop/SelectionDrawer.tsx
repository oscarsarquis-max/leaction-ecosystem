import { useEffect, useRef } from "react";
import { formatCents } from "../lib/money";
import { useCart } from "./CartContext";

export function SelectionDrawer() {
  const cart = useCart();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }
    if (cart.open && !dialog.open) {
      dialog.showModal();
    }
    if (!cart.open && dialog.open) {
      dialog.close();
    }
  }, [cart.open]);

  function handleClose() {
    cart.setOpen(false);
    const trigger = document.querySelector<HTMLButtonElement>(".header-cart");
    trigger?.focus();
  }

  return (
    <dialog
      ref={dialogRef}
      className="selection-drawer"
      aria-labelledby="selection-title"
      onClose={handleClose}
      onCancel={handleClose}
    >
      <button type="button" className="close" onClick={handleClose} aria-label="Fechar seleção">
        ×
      </button>
      <h2 id="selection-title">Sua seleção</h2>
      {cart.resolved.length === 0 ? <p>Nenhum pão na seleção ainda.</p> : null}
      <ul className="selection-list">
        {cart.resolved.map((line) => (
          <li key={line.variantId}>
            <div>
              <strong>{line.productName}</strong>
              <span>
                {line.variantName}
                {line.packLabel ? ` · ${line.packLabel}` : ""}
              </span>
              {line.notice ? <em>{line.notice}</em> : null}
            </div>
            <label className="selection-qty">
              Quantidade
              <input
                type="number"
                min={1}
                max={20}
                value={line.quantity}
                onChange={(event) =>
                  cart.changeQuantity(line.variantId, Math.max(1, Number.parseInt(event.target.value, 10) || 1))
                }
              />
            </label>
            <span>{line.available ? formatCents(line.lineCents) : "—"}</span>
            <button type="button" className="text-button" onClick={() => cart.remove(line.variantId)}>
              Remover
            </button>
          </li>
        ))}
      </ul>
      <p className="selection-total">Total {formatCents(cart.totalCents)}</p>
      <p className="demo">
        A finalização de pedidos ainda não está disponível. Esta seleção guarda pão, apresentação e quantidade; não
        reserva fornada nem processa pagamento.
      </p>
    </dialog>
  );
}
