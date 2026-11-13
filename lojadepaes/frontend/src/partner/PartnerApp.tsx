import { useCallback, useEffect, useState } from "react";
import { PartnerMark } from "../admin/marketplace/PartnerMark";
import { Button } from "../admin/shell/Button";
import { PartnerAccess } from "./PartnerAccess";
import { PartnerBrand } from "./PartnerBrand";
import { PartnerHome } from "./PartnerHome";
import { PartnerProductForm } from "./PartnerProductForm";
import { PartnerApiError, partnerApi, rememberCsrf, type PartnerSession } from "./partnerApi";
import "../admin/shell/tokens.css";
import "../admin/shell/shell.css";
import "../admin/marketplace/marketplace.css";
import "./partner.css";

export const PARTNER_BASE = "/parceiro";

type Route =
  | { view: "home" }
  | { view: "brand" }
  | { view: "invite" }
  | { view: "login" }
  | { view: "product"; id: string | null };

export function partnerRoute(path: string): Route {
  const rest = path.replace(/\/+$/, "").slice(PARTNER_BASE.length).split("/").filter(Boolean);
  const [section, id] = rest;
  if (section === "convite") {
    return { view: "invite" };
  }
  if (section === "entrar") {
    return { view: "login" };
  }
  if (section === "marca") {
    return { view: "brand" };
  }
  if (section === "produtos" && id) {
    return { view: "product", id: id === "novo" ? null : id };
  }
  return { view: "home" };
}

function currentPath(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function go(to: string): void {
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function PartnerApp() {
  const [path, setPath] = useState(currentPath);
  const [session, setSession] = useState<PartnerSession | null>(null);
  const [state, setState] = useState<"checking" | "ready" | "signed-out" | "off" | "error">("checking");

  useEffect(() => {
    const onPop = () => setPath(currentPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    document.title = "Portal do parceiro — Loja de Pães";
  }, []);

  const accept = useCallback((next: PartnerSession) => {
    rememberCsrf(next.csrf_token);
    setSession(next);
    setState("ready");
  }, []);

  useEffect(() => {
    let cancelled = false;
    partnerApi
      .me()
      .then((next) => {
        if (!cancelled) {
          accept(next);
        }
      })
      .catch((reason) => {
        if (cancelled) {
          return;
        }
        if (reason instanceof PartnerApiError && reason.status === 404) {
          setState("off");
        } else if (reason instanceof PartnerApiError && reason.status === 401) {
          setState("signed-out");
        } else {
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accept]);

  const route = partnerRoute(path);

  async function signOut() {
    try {
      await partnerApi.logout();
    } finally {
      rememberCsrf(null);
      setSession(null);
      setState("signed-out");
      go(`${PARTNER_BASE}/entrar`);
    }
  }

  const header = (
    <header className="ptn-top">
      <a
        className="ptn-brand"
        href={PARTNER_BASE}
        onClick={(event) => {
          event.preventDefault();
          go(PARTNER_BASE);
        }}
      >
        <span className="ptn-brand-name">Loja de Pães</span>
        <span className="ptn-brand-mark">Portal do parceiro</span>
      </a>
      {session ? (
        <div className="ptn-who">
          <PartnerMark partner={session.partner} />
          <span className="ptn-who-name">{session.partner.brand_name}</span>
          <Button onClick={() => void signOut()}>Sair</Button>
        </div>
      ) : null}
    </header>
  );

  let body;
  if (state === "checking") {
    body = (
      <div className="admin-card mkt-skel" aria-busy="true">
        <span className="mkt-sr">Carregando…</span>
      </div>
    );
  } else if (state === "off") {
    body = (
      <section className="ptn-center admin-card">
        <h1 className="ptn-h1">Portal indisponível</h1>
        <p className="mkt-muted">O portal do parceiro ainda não está aberto. Fale com a Loja de Pães.</p>
      </section>
    );
  } else if (state === "error") {
    body = (
      <section className="ptn-center admin-card">
        <h1 className="ptn-h1">Não foi possível abrir o portal</h1>
        <p className="mkt-muted">Confira a conexão e tente de novo.</p>
        <Button variant="primary" onClick={() => window.location.reload()}>
          Tentar de novo
        </Button>
      </section>
    );
  } else if (state === "signed-out" || !session) {
    body = (
      <PartnerAccess
        mode={route.view === "invite" ? "invite" : "login"}
        onSignedIn={(next) => {
          accept(next);
          go(PARTNER_BASE);
        }}
      />
    );
  } else if (route.view === "brand") {
    body = (
      <PartnerBrand
        partner={session.partner}
        onSaved={(partner) => setSession({ ...session, partner })}
        onBack={() => go(PARTNER_BASE)}
      />
    );
  } else if (route.view === "product") {
    body = (
      <PartnerProductForm
        productId={route.id}
        paused={session.partner.status === "paused"}
        onBack={() => go(PARTNER_BASE)}
        onSaved={(id) => go(`${PARTNER_BASE}/produtos/${id}`)}
      />
    );
  } else {
    body = (
      <PartnerHome
        partner={session.partner}
        onNew={() => go(`${PARTNER_BASE}/produtos/novo`)}
        onOpen={(id) => go(`${PARTNER_BASE}/produtos/${id}`)}
        onBrand={() => go(`${PARTNER_BASE}/marca`)}
      />
    );
  }

  return (
    <div className="admin-shell ptn-shell">
      <div className="admin-frame ptn-frame">
        {header}
        <main className="ptn-main mkt-page">{body}</main>
      </div>
    </div>
  );
}
