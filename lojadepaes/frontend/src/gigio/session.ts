export type GigioLink = {
  href: string;
  label: string;
  kind?: string;
};

export type GigioSource = {
  href: string;
  label: string;
  kind?: string;
  title?: string;
  synthesis?: string;
  source_kind?: string;
  kind_note?: string;
  author?: string;
  consulted_at?: string;
  scope?: string;
  evidence_type?: string;
  retrieval_role?: string;
  score_line?: string;
  loja_choice?: boolean;
};

export type GigioMessage = {
  role: "user" | "assistant";
  content: string;
  cta?: GigioLink | null;
  builderCta?: GigioLink | null;
  links?: GigioLink[];
  sources?: GigioSource[];
  notice?: string;
  deepenOffer?: boolean;
};

export type GigioBuilderContext = {
  flour: string;
  preparation: string;
  inclusions: string[];
  shape: string;
  note: string;
};

export type GigioLibraryContext = {
  article_id: string;
  article_version: number;
  intent: string;
  calculator_mode: string;
};

let builderPage: GigioBuilderContext | null = null;
let libraryPage: GigioLibraryContext | null = null;

export function setBuilderPageContext(context: GigioBuilderContext | null): void {
  builderPage = context;
}

export function readBuilderPageContext(): GigioBuilderContext | null {
  return builderPage;
}

export function setLibraryPageContext(context: GigioLibraryContext | null): void {
  libraryPage = context;
}

export function readLibraryPageContext(): GigioLibraryContext | null {
  return libraryPage;
}

export type GigioStatus = {
  enabled: boolean;
  ready: boolean;
  live: boolean;
  welcome: string | null;
  starters: string[];
  culinary: string[];
};

const KEY = "lojadepaes_gigio_messages";

export function loadConversation(): GigioMessage[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as GigioMessage[];
    return parsed
      .filter((item) => item.role === "user" || item.role === "assistant")
      .map((item) => ({
        role: item.role,
        content: item.content,
        cta: safeAcompanharLink(item.cta),
        builderCta: safeBuilderLink(item.builderCta),
        links: Array.isArray(item.links) ? item.links.map(safeShopLink).filter((link): link is GigioLink => Boolean(link)) : undefined,
        sources: Array.isArray(item.sources)
          ? item.sources.map(safeSourceLink).filter((link): link is GigioSource => Boolean(link))
          : undefined,
        notice: typeof item.notice === "string" ? item.notice : undefined,
      }));
  } catch {
    return [];
  }
}

export function saveConversation(messages: GigioMessage[]): void {
  sessionStorage.setItem(KEY, JSON.stringify(messages.slice(-20)));
}

export function clearConversation(): void {
  sessionStorage.removeItem(KEY);
}

export function safeBuilderLink(link: GigioLink | null | undefined): GigioLink | null {
  if (!link?.href || !link.label) {
    return null;
  }
  if (link.label !== "Montar esse pão") {
    return null;
  }
  if (!link.href.startsWith("/?proposta=") || !link.href.includes("#criacao") || link.href.startsWith("//")) {
    return null;
  }
  const token = new URLSearchParams(link.href.split("#")[0].slice(1)).get("proposta") || "";
  if (!token || token.length > 800 || /[^A-Za-z0-9._-]/.test(token)) {
    return null;
  }
  return { href: `/?proposta=${token}#criacao`, label: "Montar esse pão", kind: "builder" };
}

function safeAcompanharLink(link: GigioLink | null | undefined): GigioLink | null {
  if (!link?.href || !link.label) {
    return null;
  }
  if (!link.href.startsWith("/acompanhar") || link.href.startsWith("//")) {
    return null;
  }
  return { href: link.href, label: link.label, kind: "vitrine" };
}

const SOURCE_HOSTS = [
  ".evino.com.br",
  ".gov.br",
  ".embrapa.br",
  ".winefolly.com",
  ".decanter.com",
  ".lojadepaes.com.br",
  ".adegaonline.com.br",
  ".guiadescorchados.cl",
];
const SOURCE_EXACT = new Set([
  "evino.com.br",
  "www.evino.com.br",
  "ajuda.evino.com.br",
  "gov.br",
  "www.gov.br",
  "embrapa.br",
  "www.embrapa.br",
  "alice.cnptia.embrapa.br",
  "winefolly.com",
  "www.winefolly.com",
  "decanter.com",
  "www.decanter.com",
  "lojadepaes.com.br",
  "www.lojadepaes.com.br",
  "adegaonline.com.br",
  "www.adegaonline.com.br",
  "guiadescorchados.cl",
  "www.guiadescorchados.cl",
]);

function safeSourceLink(link: GigioSource | null | undefined): GigioSource | null {
  if (!link?.href || !link.label) {
    return null;
  }
  try {
    const parsed = new URL(link.href);
    if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
      return null;
    }
    const host = parsed.hostname.toLowerCase();
    if (!SOURCE_EXACT.has(host) && !SOURCE_HOSTS.some((suffix) => host.endsWith(suffix))) {
      return null;
    }
  } catch {
    return null;
  }
  return {
    href: link.href,
    label: link.label,
    kind: "source",
    title: link.title,
    synthesis: link.synthesis,
    source_kind: link.source_kind,
    kind_note: link.kind_note,
    author: link.author,
    consulted_at: link.consulted_at,
    scope: link.scope,
    evidence_type: link.evidence_type,
    retrieval_role: link.retrieval_role,
    score_line: link.score_line,
    loja_choice: Boolean(link.loja_choice),
  };
}

function safeShopLink(link: GigioLink | null | undefined): GigioLink | null {
  if (!link?.href || !link.label) {
    return null;
  }
  if (link.href.startsWith("/") && !link.href.startsWith("//")) {
    return { href: link.href, label: link.label, kind: link.kind };
  }
  return null;
}

export function pageContext(path: string, consult = ""): {
  path: string;
  product_slug: string;
  recipe_slug: string;
  order_reference: string;
  consult?: string;
  builder?: GigioBuilderContext;
  library?: GigioLibraryContext;
} {
  const product = path.match(/^\/paes\/([^/]+)\/?$/);
  const recipe = path.match(/^\/receitas\/([^/]+)\/?$/);
  const order = path.match(/^\/pedido\/([^/]+)\/?$/);
  return {
    path,
    product_slug: product ? decodeURIComponent(product[1]) : "",
    recipe_slug: recipe ? decodeURIComponent(recipe[1]) : "",
    order_reference: order && order[1] !== "novo" ? decodeURIComponent(order[1]) : "",
    ...(consult === "deepen" ? { consult: "deepen" } : {}),
    ...(builderPage ? { builder: builderPage } : {}),
    ...(libraryPage ? { library: libraryPage } : {}),
  };
}
