import { useEffect, useId, useRef, useState } from "react";
import { Logo } from "./Logo";
import { HeaderAccount } from "./HeaderAccount";
import { CartStrokeIcon } from "./HeaderIcons";
import { useCart } from "../shop/CartContext";

const LINKS = [
  { href: "#paes", label: "Nossos pães" },
  { href: "#criacao", label: "Crie seu pão" },
  { href: "#mural", label: "À nossa mesa" },
  { href: "#biblioteca", label: "Biblioteca do padeiro" },
] as const;

export function Header() {
  const cart = useCart();
  const [active, setActive] = useState("#paes");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const onProductPage = window.location.pathname.startsWith("/paes/");
  const home = onProductPage ? "/" : "";

  useEffect(() => {
    const sync = () => {
      const hash = window.location.hash || (onProductPage ? "" : "#paes");
      setActive(hash);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, [onProductPage]);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        toggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <header className="site-header">
      <Logo href={onProductPage ? "/" : "#inicio"} />
      <button
        ref={toggleRef}
        type="button"
        className="menu-toggle"
        aria-expanded={menuOpen}
        aria-controls={menuId}
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? "Fechar menu" : "Menu"}
      </button>
      <nav id={menuId} className={menuOpen ? "is-open" : undefined} aria-label="Navegação principal">
        {LINKS.map((link) => (
          <a
            key={link.href}
            href={`${home}${link.href}`}
            className={active === link.href ? "active" : undefined}
            onClick={() => setMenuOpen(false)}
          >
            {link.label}
          </a>
        ))}
      </nav>
      <div className="header-actions">
        <HeaderAccount />
        <button
          type="button"
          className="header-cart"
          aria-label="Abrir carrinho"
          aria-haspopup="dialog"
          aria-expanded={cart.open}
          onClick={() => cart.setOpen(true)}
        >
          <CartStrokeIcon />
          {cart.count > 0 ? <span className="header-cart-count">{cart.count}</span> : null}
        </button>
      </div>
    </header>
  );
}
