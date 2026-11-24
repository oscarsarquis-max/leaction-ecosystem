import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminApiError, adminRequest } from "../api";
import { Button } from "../shell/Button";
import { PageHeader } from "../shell/PageHeader";
import { INVITE_PREFILL_KEY, MARKETPLACE_API, categoryLabel, stampLabel } from "./labels";
import "./marketplace.css";

export const LEADS_PATH = "/admin/interessados";
const B2B_URL = "https://lojadepaes.com.br/b2b";

export type Lead = {
  id: string;
  created_at: string;
  name: string;
  brand: string;
  category: string;
  city: string;
  whatsapp: string;
  email: string;
  link: string;
  message: string;
  status: string;
};

type Tone = { label: string; tone: string };

const STATUS: Record<string, Tone> = {
  new: { label: "Novo", tone: "c-acc" },
  contacting: { label: "Em conversa", tone: "c-open" },
  invited: { label: "Convidado", tone: "c-prod" },
  discarded: { label: "Descartado", tone: "c-none" },
};

const FILTERS: Array<[string, string]> = [
  ["new", "Novos"],
  ["contacting", "Em conversa"],
  ["invited", "Convidados"],
  ["discarded", "Descartados"],
  ["all", "Todos"],
];

const leadStatus = (key: string): Tone => STATUS[key] ?? { label: key, tone: "c-none" };

/** Só links http(s); um @perfil vira link do Instagram. Qualquer outra coisa fica como texto. */
export function safeLink(raw: string): string | null {
  const value = raw.trim();
  if (/^@[A-Za-z0-9._]{1,30}$/.test(value)) {
    return `https://instagram.com/${value.slice(1)}`;
  }
  if (/^https?:\/\/[^\s]+$/i.test(value)) {
    return value;
  }
  if (/^(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+(\/[^\s]*)?$/i.test(value)) {
    return `https://${value}`;
  }
  return null;
}

export function whatsappHref(raw: string): string | null {
  let digits = raw.replace(/\D/g, "");
  if (digits.length === 10 || digits.length === 11) {
    digits = `55${digits}`;
  }
  return digits.length >= 12 && digits.length <= 13 ? `https://wa.me/${digits}` : null;
}

type Props = {
  marketplaceOn: boolean;
  onNavigate: (to: string) => void;
};

export function LeadsPage({ marketplaceOn, onNavigate }: Props) {
  const [rows, setRows] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [off, setOff] = useState(false);
  const [filter, setFilter] = useState("new");
  const [openId, setOpenId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await adminRequest<Lead[]>(`${MARKETPLACE_API}/leads`);
      setRows(Array.isArray(data) ? data : []);
      setOff(false);
    } catch (reason) {
      if (reason instanceof AdminApiError && reason.status === 404) {
        setOff(true);
      } else {
        setError(reason instanceof AdminApiError ? reason.message : "Não foi possível carregar os interessados.");
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    const result: Record<string, number> = { all: rows?.length ?? 0 };
    for (const row of rows ?? []) {
      result[row.status] = (result[row.status] ?? 0) + 1;
    }
    return result;
  }, [rows]);

  const visible = (rows ?? []).filter((row) => filter === "all" || row.status === filter);

  async function setStatus(lead: Lead, status: string): Promise<boolean> {
    setBusyId(lead.id);
    setError(null);
    try {
      await adminRequest(`${MARKETPLACE_API}/leads/${encodeURIComponent(lead.id)}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setRows((current) => (current ?? []).map((row) => (row.id === lead.id ? { ...row, status } : row)));
      return true;
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível atualizar o interessado.");
      return false;
    } finally {
      setBusyId(null);
    }
  }

  async function invite(lead: Lead) {
    if (!(await setStatus(lead, "invited"))) return;
    try {
      sessionStorage.setItem(
        INVITE_PREFILL_KEY,
        JSON.stringify({ brand_name: lead.brand, city: lead.city, contact: lead.name, email: lead.email }),
      );
    } catch {
      /* sem armazenamento: o convite abre em branco */
    }
    onNavigate("/admin/marketplace/parceiros/novo");
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(B2B_URL);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  const header = (
    <PageHeader
      title="Interessados"
      description="Produtores que se apresentaram pela página de parceiros (lojadepaes.com.br/b2b). Converse, convide ou descarte."
      actions={<Button onClick={() => void copyLink()}>{copied ? "Link copiado" : "Copiar link da página"}</Button>}
    />
  );

  if (off) {
    return (
      <section className="mkt-page">
        {header}
        <p className="mkt-note" role="status">
          O formulário de parceiros está desligado neste ambiente.
        </p>
      </section>
    );
  }

  return (
    <section className="mkt-page">
      {header}
      <nav className="mkt-tabs" aria-label="Filtrar interessados">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={filter === key ? "mkt-tab is-on" : "mkt-tab"}
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
            {rows ? <span className="mkt-tab-count">{counts[key] ?? 0}</span> : null}
          </button>
        ))}
      </nav>

      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}

      {rows === null && !error ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : null}

      {rows && visible.length === 0 ? (
        <div className="admin-card mkt-empty">
          <p className="mkt-empty-title">
            {rows.length === 0 ? "Ninguém se apresentou ainda." : "Nenhum interessado neste filtro."}
          </p>
          {rows.length === 0 ? (
            <p className="mkt-muted">Compartilhe a página lojadepaes.com.br/b2b com produtores da região.</p>
          ) : null}
        </div>
      ) : null}

      {visible.length ? (
        <ul className="mkt-leads" aria-label="Interessados">
          {visible.map((lead) => {
            const status = leadStatus(lead.status);
            const open = openId === lead.id;
            const link = lead.link ? safeLink(lead.link) : null;
            const wa = whatsappHref(lead.whatsapp);
            const detailId = `lead-${lead.id}`;
            return (
              <li key={lead.id} className="admin-card mkt-lead">
                <div className="mkt-lead-top">
                  <div className="mkt-lead-who">
                    <strong>{lead.brand}</strong>
                    <span className="mkt-muted">
                      {lead.name} · {lead.city} · {categoryLabel(lead.category)}
                    </span>
                  </div>
                  <span className={`admin-chip ${status.tone}`}>
                    <span className="dot" aria-hidden="true" />
                    {status.label}
                  </span>
                  <span className="mkt-muted mkt-lead-when">{stampLabel(lead.created_at)}</span>
                  <Button aria-expanded={open} aria-controls={detailId} onClick={() => setOpenId(open ? null : lead.id)}>
                    {open ? "Fechar" : "Abrir"}
                  </Button>
                </div>
                {open ? (
                  <div className="mkt-lead-body" id={detailId}>
                    <p className="mkt-lead-msg">{lead.message}</p>
                    <dl className="mkt-lead-contacts">
                      <dt>WhatsApp</dt>
                      <dd>
                        {wa ? (
                          <a href={wa} target="_blank" rel="noopener noreferrer">
                            {lead.whatsapp}
                          </a>
                        ) : (
                          lead.whatsapp
                        )}
                      </dd>
                      <dt>E-mail</dt>
                      <dd>
                        <a href={`mailto:${lead.email}`}>{lead.email}</a>
                      </dd>
                      {lead.link ? (
                        <>
                          <dt>Instagram ou site</dt>
                          <dd>
                            {link ? (
                              <a href={link} target="_blank" rel="noopener noreferrer nofollow">
                                {lead.link}
                              </a>
                            ) : (
                              lead.link
                            )}
                          </dd>
                        </>
                      ) : null}
                    </dl>
                    <div className="mkt-row">
                      {lead.status !== "contacting" && lead.status !== "invited" ? (
                        <Button disabled={busyId === lead.id} onClick={() => void setStatus(lead, "contacting")}>
                          Marcar em conversa
                        </Button>
                      ) : null}
                      {lead.status !== "invited" ? (
                        marketplaceOn ? (
                          <Button variant="primary" disabled={busyId === lead.id} onClick={() => void invite(lead)}>
                            Convidar como parceiro
                          </Button>
                        ) : (
                          <span className="mkt-muted">O convite de parceiro abre quando o marketplace for ligado.</span>
                        )
                      ) : null}
                      {lead.status !== "discarded" && lead.status !== "invited" ? (
                        <Button disabled={busyId === lead.id} onClick={() => void setStatus(lead, "discarded")}>
                          Descartar
                        </Button>
                      ) : null}
                      {lead.status === "discarded" ? (
                        <Button disabled={busyId === lead.id} onClick={() => void setStatus(lead, "new")}>
                          Voltar para novos
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
