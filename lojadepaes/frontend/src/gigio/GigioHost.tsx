import { useEffect, useId, useRef, useState } from "react";
import gigioAvatar from "../../images/logos/avatar_gigio.png";
import { requestJson } from "../services/http";
import { readOrderToken } from "../shop/checkoutApi";
import { SafeMarkdown } from "./markdown";
import { BUILDER_PROPOSAL_EVENT } from "../features/bread-builder/proposal";
import { GIGIO_OPEN_EVENT } from "../features/bread-builder/proposal";
import { fetchLibraryAccess, type LibraryAccess } from "../features/baker-library/libraryApi";
import {
  type GigioBuilderContext,
  type GigioLink,
  type GigioMessage,
  type GigioSource,
  type GigioStatus,
  clearConversation,
  loadConversation,
  pageContext,
  readLibraryPageContext,
  safeBuilderLink,
  saveConversation,
  setBuilderPageContext,
} from "./session";
import "./gigio.css";

type Props = { path: string };

type ChatOut = {
  reply: string;
  links: GigioLink[];
  cta?: GigioLink | null;
  builder_cta?: GigioLink | null;
  sources?: GigioSource[];
  suggestions: string[];
  notice?: string;
  unavailable: boolean;
  access?: {
    authorized?: boolean;
    needs_confirm?: boolean;
    credits?: number | null;
    exhausted?: boolean;
    complementary_eligible?: boolean;
    charged?: boolean;
    reason?: string;
    balance_source?: string;
    deepen_offer?: boolean;
    cost_label?: string;
    action_label?: string;
  };
};

function openBuilderProposal(href: string | undefined, event: { preventDefault: () => void }): void {
  if (!href) return;
  event.preventDefault();
  const token = new URLSearchParams(href.split("#")[0].replace(/^\//, "")).get("proposta") || "";
  if (!token) return;
  const next = `/?proposta=${encodeURIComponent(token)}#criacao`;
  window.history.replaceState({}, "", next);
  window.dispatchEvent(new CustomEvent(BUILDER_PROPOSAL_EVENT, { detail: { token } }));
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

function safeVitrineCta(link: GigioLink | null | undefined): GigioLink | null {
  if (!link?.href || !link.label) {
    return null;
  }
  if (!link.href.startsWith("/acompanhar") || link.href.startsWith("//")) {
    return null;
  }
  return { href: link.href, label: link.label, kind: "vitrine" };
}

export function GigioHost({ path }: Props) {
  const [status, setStatus] = useState<GigioStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<GigioMessage[]>(() => loadConversation());
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryText, setRetryText] = useState<string | null>(null);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [libraryAccess, setLibraryAccess] = useState<LibraryAccess | null>(null);
  const [consultDeepen, setConsultDeepen] = useState(false);
  const [links, setLinks] = useState<GigioLink[]>([]);
  const launchRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const liveId = useId();
  const admin = path.startsWith("/admin");
  const checkout = path.startsWith("/pedido/");
  const liftFab = path === "/" || path.startsWith("/receitas") || path.startsWith("/paes/") || path.startsWith("/acompanhar") || path.startsWith("/biblioteca");
  const deepen = readLibraryPageContext()?.intent === "deepen";

  useEffect(() => {
    requestJson<GigioStatus>("/api/v1/gigio/status")
      .then(setStatus)
      .catch(() => setStatus({ enabled: false, ready: false, live: false, welcome: null, starters: [], culinary: [] }));
  }, []);

  useEffect(() => {
    saveConversation(messages);
  }, [messages]);

  useEffect(() => {
    const thread = threadRef.current;
    if (!open || !thread) {
      return;
    }
    thread.scrollTop = thread.scrollHeight;
  }, [messages, open]);

  useEffect(() => {
    if (!open || !deepen) {
      return;
    }
    fetchLibraryAccess()
      .then(setLibraryAccess)
      .catch(() => setLibraryAccess(null));
  }, [open, deepen, messages.length]);

  useEffect(() => {
    const onOpen = (event: Event) => {
      const detail = (event as CustomEvent<GigioBuilderContext>).detail;
      if (detail) {
        setBuilderPageContext(detail);
      }
      setOpen(true);
    };
    window.addEventListener(GIGIO_OPEN_EVENT, onOpen);
    return () => window.removeEventListener(GIGIO_OPEN_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        launchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!status?.enabled) {
    return null;
  }

  const starters = deepen ? [] : messages.length === 0 ? status.starters : path.startsWith("/paes/") ? status.culinary : [];
  const creditReady =
    !deepen ||
    Boolean(libraryAccess?.can_use_ai) ||
    (libraryAccess?.balance_source === "hub" &&
      !libraryAccess.exhausted &&
      (libraryAccess.credits ?? 0) > 0);

  async function send(text: string, credit = false) {
    const content = text.trim();
    if (!content || busy) {
      return;
    }
    const credited = credit || consultDeepen || readLibraryPageContext()?.intent === "deepen";
    const nextOp =
      credited && operationId && retryText === content ? operationId : credited ? crypto.randomUUID() : null;
    if (credited && nextOp) {
      setOperationId(nextOp);
    }
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setBusy(true);
    setError(null);
    setRetryText(null);
    const page = pageContext(path, credited && consultDeepen || credit ? "deepen" : "");
    const headers: HeadersInit = { "Content-Type": "application/json" };
    if (page.order_reference) {
      const token = readOrderToken(page.order_reference);
      if (token) {
        headers["X-Order-Token"] = token;
      }
    }
    try {
      const result = await requestJson<ChatOut>("/api/v1/gigio/chat", {
        method: "POST",
        headers,
        body: JSON.stringify({
          messages: next,
          page,
          ...(credited ? { spend_credit: true, operation_id: nextOp } : {}),
        }),
      });
      const cta = result.unavailable ? null : safeVitrineCta(result.cta) || safeVitrineCta((result.links || []).find((item) => item.kind === "vitrine" || item.href.startsWith("/acompanhar?")));
      const builderCta = result.unavailable
        ? null
        : safeBuilderLink(result.builder_cta) ||
          safeBuilderLink((result.links || []).find((item) => item.kind === "builder" || item.label === "Montar esse pão"));
      setMessages([
        ...next,
        {
          role: "assistant",
          content: result.reply,
          cta,
          builderCta,
          links: result.unavailable ? [] : result.links || [],
          sources: result.unavailable ? [] : result.sources || [],
          notice: result.unavailable ? undefined : result.notice || undefined,
          deepenOffer: Boolean(result.access?.deepen_offer),
        },
      ]);
      setLinks([]);
      setDraft("");
      if (result.access?.credits != null) {
        setLibraryAccess((prev) => (prev ? { ...prev, credits: result.access?.credits ?? prev.credits, exhausted: (result.access?.credits ?? 0) <= 0 } : prev));
      }
      if (result.unavailable) {
        setRetryText(content);
        setError(result.reply || "Não consegui concluir a resposta agora. Tente novamente.");
        if (result.access?.reason === "released" || result.access?.charged === false) {
          setOperationId(null);
        }
      }
    } catch {
      setRetryText(content);
      setError("Não consegui concluir a resposta agora. Tente novamente.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="gigio-host"
      data-admin={admin ? "true" : "false"}
      data-checkout={checkout ? "true" : "false"}
      data-lift={liftFab ? "true" : "false"}
      data-open={open ? "true" : "false"}
    >
      {open ? (
        <aside className="gigio-panel" role="dialog" aria-labelledby="gigio-title">
          <header className="gigio-head">
            <img src={gigioAvatar} alt="" width={48} height={48} />
            <div>
              <h2 id="gigio-title">Gigio</h2>
              <p>{deepen ? "Aprofundamento da Biblioteca com créditos." : "Ideias para sua mesa. Ajuda com seu pedido."}</p>
            </div>
            <button ref={closeRef} type="button" className="gigio-close" aria-label="Fechar conversa" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>
          <div className="gigio-thread" aria-live="polite" id={liveId} ref={threadRef}>
            {messages.length === 0 && status.welcome ? <p className="gigio-msg is-assistant">{status.welcome}</p> : null}
            {messages.map((item, index) => (
              <div key={`${item.role}-${index}`} className={`gigio-msg is-${item.role}`}>
                {item.role === "assistant" ? <SafeMarkdown text={item.content} /> : <p>{item.content}</p>}
                {item.role === "assistant" && item.sources?.length ? (
                  <details className="gigio-sources">
                    <summary>Sobre esta sugestão</summary>
                    {item.sources.map((source) => (
                      <div key={`${source.href}-${source.title || source.label}`} className="gigio-source">
                        {source.title ? <p className="gigio-source-title">{source.title}</p> : null}
                        {source.score_line ? <p className="gigio-source-score">{source.score_line}</p> : null}
                        {source.synthesis ? <p>{source.synthesis}</p> : null}
                        <a href={source.href} target="_blank" rel="noopener noreferrer">
                          Fonte: {source.label}
                        </a>
                        {source.kind_note ? <p className="gigio-source-note">{source.kind_note}</p> : null}
                      </div>
                    ))}
                  </details>
                ) : null}
                {item.role === "assistant" && item.links?.length
                  ? item.links
                      .filter((link) => link.href !== item.cta?.href && link.href !== item.builderCta?.href && link.kind !== "source" && link.kind !== "builder")
                      .map((link) => {
                        const external = link.href.startsWith("https://");
                        return (
                          <a
                            key={`${link.href}-${link.label}`}
                            className="gigio-msg-link"
                            href={link.href}
                            {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                          >
                            {link.label}
                          </a>
                        );
                      })
                  : null}
                {item.role === "assistant" && item.notice ? <p className="gigio-notice">{item.notice}</p> : null}
                {item.role === "assistant" && item.deepenOffer ? (
                  <button
                    type="button"
                    className="gigio-cta"
                    onClick={() => {
                      const previous = messages[index - 1]?.content || "";
                      setConsultDeepen(true);
                      void send(previous, true);
                    }}
                  >
                    Usar 1 crédito de IA
                  </button>
                ) : null}
                {item.role === "assistant" && item.builderCta ? (
                  <a
                    className="gigio-cta gigio-cta-builder"
                    href={item.builderCta.href}
                    onClick={(event) => openBuilderProposal(item.builderCta?.href, event)}
                  >
                    {item.builderCta.label}
                  </a>
                ) : null}
                {item.role === "assistant" && item.cta ? (
                  <a className="gigio-cta" href={item.cta.href}>
                    {item.cta.label}
                  </a>
                ) : null}
                {item.role === "assistant" && (item.cta || item.links?.some((link) => link.href.includes("mercadolivre") || link.href.includes("amazon"))) ? (
                  <p className="gigio-commission">
                    Links comissionados: A Loja pode receber uma comissão pelas compras. Compra e entrega são
                    separadas.
                  </p>
                ) : null}
              </div>
            ))}
            {busy ? <p className="gigio-status">Gigio está consultando…</p> : null}
            {error && !retryText ? <p className="gigio-status">{error}</p> : null}
            {retryText && !busy ? (
              <button type="button" className="text-button" onClick={() => void send(retryText)}>
                Tentar novamente
              </button>
            ) : null}
          </div>
          {links.length ? (
            <div className="gigio-links">
              {links.map((link) => {
                const external = link.href.startsWith("https://");
                return (
                  <a
                    key={link.href}
                    href={link.href}
                    {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  >
                    {link.label}
                  </a>
                );
              })}
            </div>
          ) : null}
          {starters.length ? (
            <div className="gigio-chips">
              {starters.map((item) => (
                <button key={item} type="button" disabled={busy} onClick={() => void send(item)}>
                  {item}
                </button>
              ))}
            </div>
          ) : null}
          <div className="gigio-tools">
            <button
              type="button"
              className="text-button"
              onClick={() => {
                clearConversation();
                setMessages([]);
                setLinks([]);
                setRetryText(null);
                setError(null);
                setConsultDeepen(false);
              }}
            >
              Limpar conversa
            </button>
            {!status.ready ? <span className="gigio-status">Atendimento indisponível no momento.</span> : null}
          </div>
          {consultDeepen && !deepen ? (
            <div className="gigio-credit-bar">
              <p>Aprofundamento com o Gigio. Cada envio usa 1 crédito de IA.</p>
              <button type="button" className="text-button" onClick={() => setConsultDeepen(false)}>
                Voltar à consulta livre
              </button>
            </div>
          ) : null}
          {deepen ? (
            <div className="gigio-credit-bar">
              {libraryAccess?.balance_source === "hub" && typeof libraryAccess.credits === "number" ? (
                <p>
                  Saldo: {libraryAccess.credits} · 1 consulta = 1 crédito
                  {libraryAccess.valid_until
                    ? ` · mensal até ${new Date(libraryAccess.valid_until).toLocaleDateString("pt-BR")}`
                    : ""}
                  {typeof libraryAccess.pack_credits === "number"
                    ? ` · avulso ${libraryAccess.pack_credits} sem vencimento`
                    : ""}
                </p>
              ) : libraryAccess?.reason === "hub_unavailable" || libraryAccess?.balance_source === "unavailable" ? (
                <p>O ActionHub não confirmou o saldo agora. Isso não é esgotamento.</p>
              ) : (
                <p>Consulta com créditos: o envio só ocorre depois de Usar 1 crédito.</p>
              )}
              {libraryAccess?.exhausted ? <p>Saldo deste ciclo esgotado. Leitura e atendimento continuam livres.</p> : null}
            </div>
          ) : null}
          <form
            className="gigio-form"
            onSubmit={(event) => {
              event.preventDefault();
              void send(draft);
            }}
          >
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={2000}
              rows={2}
              aria-label={deepen ? "Consulta de aprofundamento da Biblioteca" : "Mensagem para o Gigio"}
              disabled={!status.ready || busy || (deepen && !creditReady)}
            />
            <button type="submit" disabled={!status.ready || busy || !draft.trim() || (deepen && !creditReady)}>
              {consultDeepen && !deepen ? "Usar 1 crédito de IA" : deepen ? "Usar 1 crédito" : "Enviar"}
            </button>
          </form>
        </aside>
      ) : (
        <button
          ref={launchRef}
          type="button"
          className="gigio-launch"
          onClick={() => setOpen(true)}
          aria-label="Conversar com Gigio"
        >
          <img src={gigioAvatar} alt="" width={56} height={56} />
          <span>Conversar com Gigio</span>
        </button>
      )}
    </div>
  );
}
