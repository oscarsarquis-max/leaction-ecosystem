import { useEffect, useRef } from "react";
import { writeBuilderResume } from "../features/bread-builder/state";
import { formatCents } from "../lib/money";
import { AdaptationLineEditor } from "./AdaptationRequest";
import { useCart } from "./CartContext";
import { goStorefront } from "./checkoutApi";
import { QuantityField } from "./QuantityField";

export function SelectionDrawer({ ordersEnabled = true }: { ordersEnabled?: boolean }) {
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
      {cart.notice ? <p role="status">{cart.notice}</p> : null}
      {cart.resolved.length === 0 ? <p>Nenhum pão na seleção ainda.</p> : null}
      <ul className="selection-list">
        {cart.resolved.map((line) => (
          <li key={line.key}>
            <div>
              <strong>{line.productName}</strong>
              <span>
                {line.variantName}
                {line.packLabel ? ` · ${line.packLabel}` : ""}
              </span>
              {line.notice ? <em>{line.notice}</em> : null}
              {line.reviewTarget && line.custom ? (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    const extras = line.custom!.ingredientIds.filter((id) => id !== line.custom!.flourId);
                    const extraNames = line.custom!.ingredientNames.filter((name) => name !== line.custom!.flourName);
                    writeBuilderResume({
                      massId: line.reviewTarget === "preparation" ? "" : line.custom!.doughTypeId,
                      massName: line.reviewTarget === "preparation" ? "" : line.custom!.doughName,
                      flourId: line.reviewTarget === "flour" ? "" : line.custom!.flourId,
                      flourName: line.reviewTarget === "flour" ? "" : line.custom!.flourName,
                      extraIds: extras,
                      extraNames,
                      shapeId: line.custom!.breadShapeId,
                      shapeName: line.custom!.shapeName,
                      freeText: line.adaptation?.reason === "preference" ? line.adaptation.text : "",
                      quantity: line.quantity,
                      notice: line.notice,
                    });
                    cart.remove(line.key);
                    cart.setOpen(false);
                    goStorefront("/#criacao");
                  }}
                >
                  Revisar esta escolha
                </button>
              ) : null}
              <AdaptationLineEditor line={line} />
            </div>
            <QuantityField
              value={line.quantity}
              onChange={(quantity) => cart.changeQuantity(line.key, quantity)}
            />
            <span>{line.available ? formatCents(line.lineCents) : "—"}</span>
            <button type="button" className="text-button" onClick={() => cart.remove(line.key)}>
              Remover
            </button>
          </li>
        ))}
      </ul>
      <p className="selection-total">Total {formatCents(cart.totalCents)}</p>
      {ordersEnabled && cart.resolved.some((line) => line.available) ? (
        <button
          type="button"
          className="primary"
          onClick={() => {
            handleClose();
            goStorefront("/pedido/novo");
          }}
        >
          Pedir estes pães
        </button>
      ) : null}
      <p className="demo">
        {ordersEnabled
          ? "Pagar não reserva a fornada. A data só fica confirmada quando A Loja aceitar o pedido."
          : "A loja está em preparação. Pedidos estão desativados."}
      </p>
    </dialog>
  );
}
