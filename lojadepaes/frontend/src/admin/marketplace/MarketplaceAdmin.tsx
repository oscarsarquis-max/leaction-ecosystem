import { useCallback, useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { PageHeader } from "../shell/PageHeader";
import { InvitePartner } from "./InvitePartner";
import { LinksTable } from "./LinksTable";
import { MARKETPLACE_API } from "./labels";
import { PartnerDetail } from "./PartnerDetail";
import { PartnersTable } from "./PartnersTable";
import { ProductReviewPage } from "./ProductReview";
import { ReviewQueue } from "./ReviewQueue";
import type { Partner, PartnerProduct } from "./types";
import "./marketplace.css";

export const MARKETPLACE_BASE = "/admin/marketplace";

type Route =
  | { view: "tab"; tab: "parceiros" | "avaliacao" | "vinculos" }
  | { view: "invite" }
  | { view: "partner"; id: string }
  | { view: "review"; id: string };

export function marketplaceRoute(path: string): Route {
  const rest = path.replace(/\/+$/, "").slice(MARKETPLACE_BASE.length).split("/").filter(Boolean);
  const [section, id] = rest;
  if (section === "parceiros" && id === "novo") {
    return { view: "invite" };
  }
  if (section === "parceiros" && id) {
    return { view: "partner", id };
  }
  if (section === "avaliacao" && id) {
    return { view: "review", id };
  }
  if (section === "avaliacao" || section === "vinculos") {
    return { view: "tab", tab: section };
  }
  return { view: "tab", tab: "parceiros" };
}

type Props = {
  path: string;
  onNavigate: (to: string) => void;
};

const TABS: Array<["parceiros" | "avaliacao" | "vinculos", string]> = [
  ["parceiros", "Parceiros"],
  ["avaliacao", "Avaliação"],
  ["vinculos", "Vínculos por categoria"],
];

export function MarketplaceAdmin({ path, onNavigate }: Props) {
  const route = marketplaceRoute(path);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [products, setProducts] = useState<PartnerProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [off, setOff] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [partnerRows, productRows] = await Promise.all([
        adminRequest<Partner[]>(`${MARKETPLACE_API}/partners`),
        adminRequest<PartnerProduct[]>(`${MARKETPLACE_API}/products`),
      ]);
      setPartners(partnerRows);
      setProducts(productRows);
      setOff(false);
    } catch (reason) {
      if (reason instanceof AdminApiError && reason.status === 404) {
        setOff(true);
      } else {
        setError(reason instanceof AdminApiError ? reason.message : "Não foi possível carregar o marketplace.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (off) {
    return (
      <section className="mkt-page">
        <PageHeader title="Parceiros" />
        <p className="mkt-note" role="status">
          O marketplace está desligado neste ambiente.
        </p>
      </section>
    );
  }

  if (route.view === "invite") {
    return (
      <InvitePartner
        onBack={() => onNavigate(`${MARKETPLACE_BASE}/parceiros`)}
        onCreated={() => void load()}
        onOpen={(id) => onNavigate(`${MARKETPLACE_BASE}/parceiros/${id}`)}
      />
    );
  }

  if (route.view === "partner") {
    return (
      <PartnerDetail
        partnerId={route.id}
        products={products.filter((item) => item.partner_id === route.id)}
        onBack={() => onNavigate(`${MARKETPLACE_BASE}/parceiros`)}
        onChanged={() => void load()}
        onReview={(id) => onNavigate(`${MARKETPLACE_BASE}/avaliacao/${id}`)}
      />
    );
  }

  if (route.view === "review") {
    const product = products.find((item) => item.id === route.id) ?? null;
    return (
      <ProductReviewPage
        product={product}
        partner={product ? (partners.find((item) => item.id === product.partner_id) ?? null) : null}
        loading={loading}
        onBack={() => onNavigate(`${MARKETPLACE_BASE}/avaliacao`)}
        onDecided={() => void load()}
      />
    );
  }

  const pending = products.filter((item) => item.status === "pending");
  const tab = route.tab;

  return (
    <section className="mkt-page">
      <PageHeader
        title="Parceiros"
        description="Produtores que complementam o pão da casa. Cada parceiro cadastra os próprios produtos; nada vai para a vitrine sem a avaliação da Loja."
        actions={
          <Button variant="primary" onClick={() => onNavigate(`${MARKETPLACE_BASE}/parceiros/novo`)}>
            Convidar parceiro
          </Button>
        }
      />
      <nav className="mkt-tabs" aria-label="Seções do marketplace">
        {TABS.map(([key, label]) => {
          const count = key === "parceiros" ? partners.length : key === "avaliacao" ? pending.length : null;
          return (
            <a
              key={key}
              href={`${MARKETPLACE_BASE}/${key}`}
              className={tab === key ? "mkt-tab is-on" : "mkt-tab"}
              aria-current={tab === key ? "page" : undefined}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(`${MARKETPLACE_BASE}/${key}`);
              }}
            >
              {label}
              {count !== null && !loading ? <span className="mkt-tab-count">{count}</span> : null}
            </a>
          );
        })}
      </nav>
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {loading ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : error ? null : tab === "parceiros" ? (
        <PartnersTable
          partners={partners}
          products={products}
          onOpen={(id) => onNavigate(`${MARKETPLACE_BASE}/parceiros/${id}`)}
          onInvite={() => onNavigate(`${MARKETPLACE_BASE}/parceiros/novo`)}
        />
      ) : tab === "avaliacao" ? (
        <ReviewQueue
          products={pending}
          partners={partners}
          onOpen={(id) => onNavigate(`${MARKETPLACE_BASE}/avaliacao/${id}`)}
        />
      ) : (
        <LinksTable partners={partners} onOpen={(id) => onNavigate(`${MARKETPLACE_BASE}/parceiros/${id}`)} />
      )}
    </section>
  );
}
