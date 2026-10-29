import { useEffect, useId, useRef, useState } from "react";
import { currentPathname, homeSectionHref } from "../app/homeHash";
import { useCart } from "../shop/CartContext";
import { HeaderAccount } from "./HeaderAccount";
import { HeaderCustomerStatus } from "./HeaderCustomerStatus";
import { CartStrokeIcon } from "./HeaderIcons";
import { Logo } from "./Logo";

const LINKS = [
  { href: "#paes", label: "Nossos pães" },
  { href: "#criacao", label: "Crie seu pão" },
  { href: "#mural", label: "À nossa mesa" },
  { href: "#biblioteca", label: "Biblioteca do padeiro" },
] as const;

export function Header({ accompanimentsVisible = false }: { accompanimentsVisible?: boolean }) {
  const cart = useCart();
  const [path, setPath] = useState(currentPathname);
  const [active, setActive] = useState(() => window.location.hash || (currentPathname() !== "/" ? "" : "#inicio"));
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const offHome = path !== "/";
  const homeCurrent = !offHome && (active === "#inicio" || active === "");

  useEffect(() => {
    const onPop = () => setPath(currentPathname());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    const sync = () => {
      const hash = window.location.hash || (offHome ? "" : "#inicio");
      setActive(hash);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, [offHome]);

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
      <Logo href={offHome ? "/" : "#inicio"} />
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
        {!offHome ? (
          <a href="#inicio" className={homeCurrent ? "active" : undefined} aria-current={homeCurrent ? "page" : undefined} onClick={() => setMenuOpen(false)}>
            Página principal
          </a>
        ) : null}
        {LINKS.map((link) => {
          const href = homeSectionHref(link.href, path);
          return (
            <a
              key={link.href}
              href={href}
              className={active === link.href ? "active" : undefined}
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </a>
          );
        })}
        {accompanimentsVisible ? (
          <a
            href="/acompanhar"
            className={path === "/acompanhar" ? "active" : undefined}
            aria-current={path === "/acompanhar" ? "page" : undefined}
            onClick={() => setMenuOpen(false)}
          >
            Para acompanhar
          </a>
        ) : null}
      </nav>
      <div className="header-actions">
        <HeaderCustomerStatus />
        <HeaderAccount />
        <button
          type="button"
          className="header-cart"
          aria-label="Carrinho"
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
