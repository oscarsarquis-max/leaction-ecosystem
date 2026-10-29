import { Fragment, useEffect, useMemo, useState } from "react";
import { fetchAccompaniments, type AccompanimentCard, type AccompanimentsCatalog } from "./accompanimentsApi";
import {
  ACC_PAGE_SIZE,
  clampPage,
  flattenCatalogItems,
  groupPageStories,
  pageCount,
  readCatalogPage,
  slicePage,
  writeCatalogPage,
} from "./accompanimentsPaging";

function formatSeenDate(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null;
  }
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(
    new Date(year, month - 1, day),
  );
}

function pricePrep(marketplace: string): string {
  return marketplace === "Amazon" ? "na" : "no";
}

function Card({ item }: { item: AccompanimentCard }) {
  const marketplace = item.marketplace || "Mercado Livre";
  const prep = pricePrep(marketplace);
  const cta = item.outbound_label || "Ver no Mercado Livre";
  const isDemo = item.demo === true || item.commercial_enabled === false;
  const extra =
    item.why_pairs ||
    item.serving_tip ||
    item.related_breads.length > 0 ||
    item.related_recipes.length > 0;
  return (
    <article className="acc-card" id={item.id}>
      {item.image_url ? (
        <figure className="acc-card-media">
          <img src={item.image_url} alt={item.name} />
        </figure>
      ) : (
        <div className="acc-card-media acc-card-media--missing" aria-hidden="true" />
      )}
      <div className="acc-card-body">
        <h3>{item.name}</h3>
        {item.description ? <p className="acc-card-desc">{item.description}</p> : null}
        <p className="acc-price">
          {isDemo
            ? "Demonstração local — sem preço comercial"
            : item.price_label
              ? item.price_fresh
                ? item.price_label
                : `${item.price_label} — confirme ${prep} ${marketplace}`
              : `Consulte o preço ${prep} ${marketplace}`}
        </p>
        {isDemo && item.external_notice ? <p className="acc-notice">{item.external_notice}</p> : null}
        {item.outbound_href && !isDemo ? (
          <a
            className="primary acc-outbound"
            href={item.outbound_href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {cta}
          </a>
        ) : isDemo ? (
          <p className="acc-notice">Compra no site de compra desligada nesta prévia — sem oferta comercial.</p>
        ) : null}
        {extra ? (
          <details className="acc-more">
            <summary>Mais sobre este acompanhamento</summary>
            {item.why_pairs ? <p className="acc-why">{item.why_pairs}</p> : null}
            {item.serving_tip ? <p className="acc-tip">{item.serving_tip}</p> : null}
            {item.related_breads.length ? (
              <p className="acc-pairs">
                Combina com{" "}
                {item.related_breads.map((bread, index) => (
                  <span key={bread.slug}>
                    {index > 0 ? ", " : ""}
                    <a href={bread.href}>{bread.name}</a>
                  </span>
                ))}
                .
              </p>
            ) : null}
            {item.related_recipes.map((recipe) => (
              <p key={recipe.slug} className="acc-pairs">
                <a href={recipe.href}>Ler {recipe.title}</a>
              </p>
            ))}
          </details>
        ) : null}
      </div>
    </article>
  );
}

export function AccompanimentsPage() {
  const [catalog, setCatalog] = useState<AccompanimentsCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seenDate, setSeenDate] = useState("");
  const [page, setPage] = useState(() => readCatalogPage());
  const fornada = useMemo(() => {
    const raw = new URLSearchParams(window.location.search).get("fornada");
    return formatSeenDate(raw || "");
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchAccompaniments()
      .then((data) => {
        if (!cancelled) {
          setCatalog(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Não foi possível abrir esta página agora. Os pães da casa continuam disponíveis.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = catalog?.enabled ? flattenCatalogItems(catalog) : [];
  const total = items.length;
  const pages = pageCount(total);
  const safePage = clampPage(page, total);
  const visible = slicePage(items, safePage);
  const stories = groupPageStories(visible);

  useEffect(() => {
    if (!catalog?.enabled) {
      return;
    }
    if (page !== safePage) {
      setPage(safePage);
      writeCatalogPage(safePage);
    }
  }, [catalog, page, safePage]);

  const goTo = (next: number) => {
    const target = clampPage(next, total);
    setPage(target);
    writeCatalogPage(target);
    document.getElementById("acc-grid")?.scrollIntoView?.({ block: "start" });
  };

  const seenLabel = formatSeenDate(seenDate);

  return (
    <main className="acc-page">
      <p className="eyebrow">
        <a href="/">A Loja</a>
      </p>
      <header className="acc-open">
        <div>
          <h1>{catalog?.title || "Para acompanhar seu pão"}</h1>
          <p>
            {catalog?.intro ||
              "Uma seleção de complementos e acessórios para aproveitar seus pães à mesa ou encontrar uma ideia de presente."}
          </p>
          {catalog?.context?.active ? (
            <p className="acc-context">
              {catalog.context.filters.map((filter) => (
                <span key={`${filter.key}-${filter.label}`}>{filter.label}</span>
              ))}
              {catalog.context.empty ? null : <a href={catalog.context.clear_href}>Ver todos os acompanhamentos</a>}
            </p>
          ) : null}
        </div>
      </header>
      {catalog?.preview && catalog.demo_notice ? (
        <p className="shelf-status" role="status">
          {catalog.demo_notice}
        </p>
      ) : null}
      {!catalog && !error ? <p className="shelf-status">Carregando a seleção…</p> : null}
      {error ? (
        <p className="shelf-status" role="alert">
          {error}
        </p>
      ) : null}
      {catalog && !catalog.enabled ? (
        <p className="shelf-status">Esta seleção ainda não está publicada. Volte aos pães da casa.</p>
      ) : null}
      {catalog?.enabled && catalog.context?.empty ? (
        <p className="shelf-status" role="status">
          Não há complementos disponíveis para essa sugestão.{" "}
          <a href="/acompanhar">Ver todos os acompanhamentos</a>
        </p>
      ) : null}
      {catalog?.enabled && total > 0 ? (
        <div id="acc-grid" className="acc-grid">
          {stories.map((story, index) => {
            const productNamed = story.items.some((item) => item.name === story.title);
            const hideHeading = Boolean(catalog?.context?.active) || productNamed;
            return (
              <Fragment key={`${story.occasion}-${story.items[0]?.id || story.title}`}>
                {hideHeading ? null : (
                  <header className={index === 0 ? "acc-story-copy acc-story-copy--first" : "acc-story-copy"}>
                    <p className="eyebrow">{story.occasion}</p>
                    <h2>{story.title}</h2>
                    {story.lead ? <p>{story.lead}</p> : null}
                  </header>
                )}
                {story.items.map((item) => (
                  <Card key={item.id} item={item} />
                ))}
              </Fragment>
            );
          })}
        </div>
      ) : null}
      {catalog?.enabled && total > 0 ? (
        <p className="acc-notice acc-offer-note">
          {[catalog.external_notice, catalog.commission_note].filter(Boolean).join(" ")}
        </p>
      ) : null}
      {catalog?.enabled && total > ACC_PAGE_SIZE ? (
        <nav className="acc-pager" aria-label="Páginas da seleção">
          <button type="button" disabled={safePage <= 1} onClick={() => goTo(safePage - 1)}>
            Anterior
          </button>
          <p>
            Página {safePage} de {pages} · {total} {total === 1 ? "item" : "itens"}
          </p>
          <button type="button" disabled={safePage >= pages} onClick={() => goTo(safePage + 1)}>
            Próxima
          </button>
        </nav>
      ) : null}
      {catalog?.enabled ? (
        <aside className="acc-plan">
          <h2>Sobre a fornada</h2>
          <p>{catalog.delivery_help.text}</p>
          {fornada ? <p>Fornada escolhida na Loja: {fornada}.</p> : null}
          <label>
            Data informada de entrega
            <input type="date" value={seenDate} onChange={(event) => setSeenDate(event.target.value)} />
          </label>
          {catalog.delivery_help.client_note ? <p>{catalog.delivery_help.client_note}</p> : null}
          {seenLabel ? (
            <p>
              Data informada por você: {seenLabel}
              {fornada ? ` / Fornada escolhida: ${fornada}` : ""}. A Loja não confirma automaticamente a entrega do
              site de compra.
            </p>
          ) : null}
          <p>
            <a href="/#paes">Escolher o pão e a fornada</a>
          </p>
        </aside>
      ) : null}
    </main>
  );
}
