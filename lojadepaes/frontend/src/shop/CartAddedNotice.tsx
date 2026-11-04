import { useCart } from "./CartContext";
import { goStorefront } from "./checkoutApi";

type Props = {
  onContinue?: () => void;
};

export function CartAddedNotice({ onContinue }: Props) {
  const cart = useCart();
  return (
    <div className="cart-added" role="status">
      <p>Item adicionado ao carrinho. Sua compra ainda não foi finalizada.</p>
      <p>Seu pão está no carrinho. Você ainda não enviou o pedido.</p>
      <p className="cart-added-actions">
        <button
          type="button"
          className="primary"
          onClick={() => {
            // A gaveta é modal: se ficar aberta, cobre a própria página do carrinho.
            cart.setOpen(false);
            goStorefront("/pedido/novo");
          }}
        >
          Ir ao carrinho para finalizar
        </button>
        <button
          type="button"
          className="text-button"
          onClick={onContinue ?? (() => goStorefront("/#paes"))}
        >
          Continuar escolhendo
        </button>
      </p>
    </div>
  );
}
