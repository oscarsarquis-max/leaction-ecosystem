import { useCallback, useEffect, useRef, useState } from "react";
import {
  companyQuery,
  freezeWrite,
  isUnknownWriteOutcome,
  loadAccessMode,
  loadHomologIntegration,
  request,
  restoreOidcSession,
  sendPending,
  signIn,
  signOut,
  startOidcLogin,
  type AccessMode,
  type ApiError,
  type CatalogItem,
  type ExternalLookup,
  type FinancialAccount,
  type HistoryItem,
  type MovementPage,
  type PendingWrite,
  type Settlement,
  type Title,
  type TitleList,
} from "./api";
import {
  formatAccountType,
  formatDateBr,
  formatHistoryValue,
  formatMethodLabel,
  formatMinor,
  formatMovementKind,
  parseBrlInput,
  parseSignedBrlInput,
} from "./money";
import { consumeReviewBeforeRelogin, getUnknownWrite } from "./pendingWrites";
import {
  canReverseSettlements,
  canWrite,
  canWriteAccounts,
  canWriteCatalogs,
  canWriteSettlements,
  getSession,
  getSessionNotice,
  hideProtectedFinancialData,
  isProtectedDataHidden,
  setSession,
  setSessionNotice,
  subscribeSession,
  withCompanyPermissions,
  type Session,
} from "./session";
import { PayReceiptsPage } from "./PayReceiptsPage";
import { AppShell } from "./ui/AppShell";
import { BrandLogo } from "./ui/BrandLogo";
import { CompactRef } from "./ui/CompactRef";
import { FinancialSummary } from "./ui/FinancialSummary";
import { Modal } from "./ui/Modal";
import { PageHeader } from "./ui/PageHeader";
import { StatusBadge } from "./ui/StatusBadge";

type Direction = "RECEIVABLE" | "PAYABLE";

const FILTER_KEY = "af.listFilters";

type Filters = {
  q: string;
  status: string;
  dueFrom: string;
  dueTo: string;
  categoryId: string;
  overdueOnly: boolean;
  settlement: string;
  page: number;
  size: number;
};

const defaultFilters = (): Filters => ({
  q: "",
  status: "OPEN",
  dueFrom: "",
  dueTo: "",
  categoryId: "",
  overdueOnly: false,
  settlement: "PENDING",
  page: 0,
  size: 20,
});

function pathOf(): string {
  return window.location.pathname;
}

function navigate(to: string, replace = false) {
  if (replace) {
    window.history.replaceState(null, "", to);
  } else {
    window.history.pushState(null, "", to);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function directionFromPath(path: string): Direction {
  return path.startsWith("/payables") ? "PAYABLE" : "RECEIVABLE";
}

function loadFilters(direction: Direction): Filters {
  try {
    const raw = sessionStorage.getItem(`${FILTER_KEY}.${direction}`);
    return raw ? { ...defaultFilters(), ...JSON.parse(raw) } : defaultFilters();
  } catch {
    return defaultFilters();
  }
}

function saveFilters(direction: Direction, filters: Filters) {
  sessionStorage.setItem(`${FILTER_KEY}.${direction}`, JSON.stringify(filters));
}

export function App() {
  const [path, setPath] = useState(pathOf);
  const [session, setSessionState] = useState<Session | null>(getSession());
  const [token, setToken] = useState("");
  const [authError, setAuthError] = useState("");
  const [accessMode, setAccessMode] = useState<AccessMode | "UNKNOWN">("UNKNOWN");
  const [restoring, setRestoring] = useState(true);
  const dirtyRef = useRef(false);
  const [pendingCompany, setPendingCompany] = useState<string | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [sessionNotice, setSessionNoticeState] = useState(getSessionNotice());
  const [protectedHidden, setProtectedHidden] = useState(isProtectedDataHidden());
  const [logoutUnconfirmed, setLogoutUnconfirmed] = useState(false);

  useEffect(
    () =>
      subscribeSession(() => {
        setSessionState(getSession());
        setSessionNoticeState(getSessionNotice());
        setProtectedHidden(isProtectedDataHidden());
      }),
    [],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("login") === "failed") {
      setAuthError("Não foi possível entrar com o provedor. Tente novamente.");
    }
    if (params.get("logout") === "1") {
      setAuthError("");
    }
    if (consumeReviewBeforeRelogin()) {
      setAuthError("O resultado anterior não foi confirmado. Confira os registros antes de lançar de novo.");
    }
    void loadAccessMode()
      .then(async (mode) => {
        setAccessMode(mode);
        if (mode === "OIDC" && !getSession()) {
          const restored = await restoreOidcSession();
          if (restored?.accessState === "READY" && (pathOf() === "/" || pathOf() === "")) {
            navigate("/receivables", true);
          }
        }
      })
      .catch(() => {
        setAccessMode(import.meta.env.DEV ? "DEMO" : "OIDC");
      })
      .finally(() => setRestoring(false));
  }, []);

  useEffect(() => {
    const onPop = () => {
      if (dirtyRef.current && !window.confirm("Há alterações não salvas. Descartar e sair?")) {
        window.history.pushState(null, "", path);
        return;
      }
      dirtyRef.current = false;
      setPath(pathOf());
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [path]);

  useEffect(() => {
    if (path === "/") {
      navigate("/receivables", true);
    }
  }, [path]);

  if (restoring && !session) {
    return (
      <main className="sign-in">
        <div className="sign-in-brand">
          <BrandLogo variant="yellow" width={212} />
          <p className="hint">Carregando acesso…</p>
        </div>
      </main>
    );
  }

  if (!session) {
    const oidc = accessMode === "OIDC";
    return (
      <main className="sign-in">
        <div className="sign-in-brand">
          <BrandLogo variant="yellow" width={212} />
          {oidc ? (
            <p className="hint">Acesso restrito a contas autorizadas.</p>
          ) : (
            <p className="hint">Demonstração local. Cole o token de teste de <code>.local/demo-tokens.env</code>. O valor não é gravado neste navegador.</p>
          )}
        </div>
        {oidc ? (
          <div className="sign-in-panel">
            {sessionNotice?.kind === "expired" ? (
              <p className="error error-box" role="alert">{sessionNotice.message}</p>
            ) : null}
            {authError ? <p className="error error-box" role="alert">{authError}</p> : null}
            <button
              type="button"
              onClick={() => {
                if (dirtyRef.current && !window.confirm("Há alterações não salvas. Elas serão descartadas ao sair desta página.")) {
                  return;
                }
                if (getUnknownWrite() && !window.confirm("O resultado anterior não foi confirmado. Confira os registros antes de lançar de novo.")) {
                  return;
                }
                startOidcLogin();
              }}
            >
              Entrar
            </button>
            <p className="hint">Sair do ActionFinance não encerra a sessão no provedor de identidade.</p>
          </div>
        ) : (
          <form
            className="sign-in-panel"
            onSubmit={(event) => {
              event.preventDefault();
              void signIn(token.trim())
                .then((next) => {
                  setSessionState(next);
                  setAuthError("");
                  if (pathOf() === "/" || pathOf() === "") {
                    navigate("/receivables", true);
                  }
                })
                .catch((error: ApiError) => setAuthError(error.message));
            }}
          >
            <label>
              Token local
              <input value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" />
            </label>
            {sessionNotice?.kind === "expired" ? (
              <p className="error error-box" role="alert">{sessionNotice.message}</p>
            ) : null}
            {authError ? <p className="error error-box" role="alert">{authError}</p> : null}
            <button type="submit">Entrar na demonstração</button>
          </form>
        )}
      </main>
    );
  }

  if (session.mode === "oidc" && session.accessState && session.accessState !== "READY") {
    return (
      <main className="sign-in">
        <div className="sign-in-brand">
          <BrandLogo variant="yellow" width={212} />
          <h1 className="sign-in-title">Seu acesso ainda não foi liberado</h1>
          <p className="hint">Esta conta autenticou, mas ainda não tem empresa autorizada no ActionFinance.</p>
        </div>
        <div className="sign-in-panel">
          <button
            type="button"
            onClick={() => {
              void signOut().then(() => {
                sessionStorage.removeItem(`${FILTER_KEY}.RECEIVABLE`);
                sessionStorage.removeItem(`${FILTER_KEY}.PAYABLE`);
                startOidcLogin();
              });
            }}
          >
            Tentar outra conta
          </button>
          <button
            type="button"
            className="btn-link"
            onClick={() => {
              void signOut().then(() => {
                sessionStorage.removeItem(`${FILTER_KEY}.RECEIVABLE`);
                sessionStorage.removeItem(`${FILTER_KEY}.PAYABLE`);
                setSessionState(null);
                navigate("/", true);
              });
            }}
          >
            Sair
          </button>
        </div>
      </main>
    );
  }

  const leave = (next?: () => void) => {
    if (dirtyRef.current && !window.confirm("Há alterações não salvas. Descartar e sair?")) {
      return false;
    }
    dirtyRef.current = false;
    next?.();
    return true;
  };

  const switchCompany = (companyId: string) => {
    if (dirtyRef.current) {
      setPendingCompany(companyId);
      return;
    }
    applyCompany(companyId);
  };

  const applyCompany = (companyId: string) => {
    const current = getSession();
    if (!current) {
      return;
    }
    const next = withCompanyPermissions(current, companyId);
    setSession(next);
    setSessionState(next);
    sessionStorage.removeItem(`${FILTER_KEY}.RECEIVABLE`);
    sessionStorage.removeItem(`${FILTER_KEY}.PAYABLE`);
    dirtyRef.current = false;
    setPendingCompany(null);
    navigate("/receivables");
  };

  const requestSignOut = async () => {
    hideProtectedFinancialData();
    setProtectedHidden(true);
    if (session.mode !== "oidc") {
      setSession(null);
      setSessionState(null);
      navigate("/", true);
      return;
    }
    const result = await signOut();
    if (result.confirmed) {
      setLogoutUnconfirmed(false);
      setSessionNotice(null);
      setSessionState(null);
      navigate("/", true);
      return;
    }
    setLogoutUnconfirmed(true);
    setSessionNotice({
      kind: "logout-unconfirmed",
      message: result.message,
    });
  };

  return (
    <AppShell
      session={session}
      path={path}
      navOpen={navOpen}
      setNavOpen={setNavOpen}
      onNavigate={(to) =>
        leave(() => {
          navigate(to);
          window.setTimeout(() => document.getElementById("page-title")?.focus(), 0);
        })
      }
      onSignOut={() =>
        leave(() => {
          sessionStorage.removeItem(`${FILTER_KEY}.RECEIVABLE`);
          sessionStorage.removeItem(`${FILTER_KEY}.PAYABLE`);
          void requestSignOut();
        })
      }
      onSwitchCompany={switchCompany}
    >
      {sessionNotice ? (
        <p className="error error-box" role="alert">
          {sessionNotice.message}
          {logoutUnconfirmed ? (
            <>
              {" "}
              <button type="button" className="btn-link" onClick={() => void requestSignOut()}>
                Tentar sair novamente
              </button>
            </>
          ) : null}
        </p>
      ) : null}
      {protectedHidden || logoutUnconfirmed ? (
        <section className="panel">
          <p>A informação financeira desta sessão foi ocultada.</p>
          {logoutUnconfirmed ? (
            <p>Não foi possível confirmar a saída. Tente novamente.</p>
          ) : null}
        </section>
      ) : path.startsWith("/pay-receipts") ? (
            <PayReceiptsPage
              path={path}
              onNavigate={(to) =>
                leave(() => {
                  navigate(to);
                  window.setTimeout(() => document.getElementById("page-title")?.focus(), 0);
                })
              }
            />
          ) : path.startsWith("/catalogs") ? (
            <CatalogsPage path={path} onDirty={(value) => (dirtyRef.current = value)} />
          ) : path.startsWith("/financial-accounts") ? (
            <AccountsRouter path={path} onDirty={(value) => (dirtyRef.current = value)} />
          ) : path.startsWith("/settlements/") ? (
            <SettlementDetailPage path={path} />
          ) : /\/(receivables|payables)\/[^/]+\/settlements\/new$/.test(path) ? (
            <SettlementFormPage path={path} onDirty={(value) => (dirtyRef.current = value)} />
          ) : path.includes("/new") || path.includes("/edit") ? (
            <TitleFormPage path={path} onDirty={(value) => (dirtyRef.current = value)} />
          ) : /\/(receivables|payables)\/[^/]+$/.test(path) ? (
            <TitleDetailPage path={path} />
          ) : (
            <TitleListPage path={path} />
          )}
      {pendingCompany ? (
        <Modal title="Trocar empresa" onClose={() => setPendingCompany(null)}>
          <p>Há alterações não salvas. Ficar nesta empresa ou descartar e trocar?</p>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => setPendingCompany(null)}>
              Ficar nesta empresa
            </button>
            <button type="button" onClick={() => applyCompany(pendingCompany)}>
              Descartar alterações e trocar
            </button>
          </div>
        </Modal>
      ) : null}
    </AppShell>
  );
}

function TitleListPage({ path }: { path: string }) {
  const direction = directionFromPath(path);
  const [filters, setFilters] = useState<Filters>(() => loadFilters(direction));
  const [data, setData] = useState<TitleList | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<CatalogItem[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const requestId = useRef(0);

  const load = useCallback(
    async (next: Filters) => {
      const id = ++requestId.current;
      setLoading(true);
      setError("");
      const params = new URLSearchParams({
        status: next.status,
        page: String(next.page),
        size: String(next.size),
        overdueOnly: String(next.overdueOnly),
      });
      if (next.status === "DRAFT" || next.status === "CANCELLED") {
        params.set("settlement", "ALL");
      } else {
        params.set("settlement", next.settlement);
      }
      if (next.q) params.set("q", next.q);
      if (next.dueFrom) params.set("dueFrom", next.dueFrom);
      if (next.dueTo) params.set("dueTo", next.dueTo);
      if (next.categoryId) params.set("categoryId", next.categoryId);
      try {
        const result = await request<TitleList>(`/api/v1/${direction === "RECEIVABLE" ? "receivables" : "payables"}?${companyQuery(params.toString())}`);
        if (id !== requestId.current) return;
        setData(result);
      } catch (caught) {
        if (id !== requestId.current) return;
        setData(null);
        setError((caught as ApiError).message);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [direction],
  );

  const companyId = getSession()?.companyId;
  useEffect(() => {
    const next = loadFilters(direction);
    setFilters(next);
    void load(next);
    void request<CatalogItem[]>(`/api/v1/catalogs/categories?${companyQuery(`compatibleWith=${direction}`)}`)
      .then(setCategories)
      .catch(() => setCategories([]));
  }, [direction, load, companyId]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      saveFilters(direction, filters);
      void load(filters);
    }, 300);
    return () => window.clearTimeout(handle);
  }, [direction, filters, load]);

  const apply = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch, page: patch.page ?? 0 };
    setFilters(next);
    saveFilters(direction, next);
    void load(next);
  };

  const title = direction === "RECEIVABLE" ? "Contas a receber" : "Contas a pagar";
  const createLabel = direction === "RECEIVABLE" ? "Novo recebível" : "Nova conta a pagar";
  const partyLabel = direction === "RECEIVABLE" ? "Cliente" : "Fornecedor";
  const emptyCompany = direction === "RECEIVABLE" ? "Nenhum recebível cadastrado nesta empresa" : "Nenhuma conta a pagar cadastrada nesta empresa";
  const base = direction === "RECEIVABLE" ? "/receivables" : "/payables";

  const extrasActive =
    filters.status !== "OPEN" ||
    filters.settlement !== "PENDING" ||
    Boolean(filters.dueFrom || filters.dueTo || filters.categoryId || filters.overdueOnly);
  return (
    <section>
      <PageHeader
        title={title}
        hint="Resumo de todos os resultados do filtro. Não é saldo bancário."
        action={
          canWrite() ? (
            <button type="button" onClick={() => navigate(`${base}/new`)}>
              {createLabel}
            </button>
          ) : null
        }
      />
      <FinancialSummary
        items={[
          {
            label: direction === "RECEIVABLE" ? "A receber" : "A pagar",
            value: data ? formatMinor(data.summary.openAmountMinor) : loading ? "…" : "—",
            hint: data ? `${data.summary.openCount} itens` : undefined,
          },
          {
            label: "Vencidos",
            value: data ? formatMinor(data.summary.overdueAmountMinor) : loading ? "…" : "—",
            hint: data ? `${data.summary.overdueCount} itens` : undefined,
          },
          {
            label: "Rascunhos",
            value: data ? String(data.summary.draftCount) : loading ? "…" : "—",
            hint: "itens",
          },
        ]}
      />
      <div className="filters">
        <label>
          Buscar
          <input
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value, page: 0 })}
            placeholder="Buscar referência, descrição ou contraparte"
          />
        </label>
        <button type="button" className="secondary" onClick={() => setFiltersOpen((open) => !open)}>
          {filtersOpen ? "Ocultar filtros" : extrasActive ? "Filtros (ativos)" : "Filtros"}
        </button>
      </div>
      {filtersOpen || typeof window === "undefined" || window.innerWidth > 1023 ? (
      <div className="filters">
        <label>
          Situação
          <select value={filters.status} onChange={(event) => apply({ status: event.target.value })}>
            <option value="OPEN">Em aberto</option>
            <option value="DRAFT">Rascunho</option>
            <option value="CANCELLED">Cancelado</option>
            <option value="ALL">Todas</option>
          </select>
        </label>
        <label>
          Situação financeira
          <select
            value={filters.settlement}
            onChange={(event) => apply({ settlement: event.target.value })}
            disabled={filters.status === "DRAFT" || filters.status === "CANCELLED"}
          >
            <option value="PENDING">Com pendência</option>
            <option value="PARTIAL">Parcial</option>
            <option value="SETTLED">Quitado</option>
            <option value="ALL">Todos</option>
          </select>
        </label>
        {filters.status === "DRAFT" || filters.status === "CANCELLED" ? (
          <p className="hint">Filtro financeiro desconsiderado para rascunho ou cancelado.</p>
        ) : null}
        <label>
          De
          <input type="date" value={filters.dueFrom} onChange={(event) => apply({ dueFrom: event.target.value })} />
        </label>
        <label>
          Até
          <input type="date" value={filters.dueTo} onChange={(event) => apply({ dueTo: event.target.value })} />
        </label>
        <SearchableSelect
          label="Categoria"
          value={filters.categoryId}
          onChange={(value) => apply({ categoryId: value })}
          options={categories}
          emptyLabel="Todas"
        />
        <label className="check">
          <input type="checkbox" checked={filters.overdueOnly} onChange={(event) => apply({ overdueOnly: event.target.checked })} />
          Só vencidos
        </label>
        <button type="button" className="secondary" onClick={() => apply(defaultFilters())}>
          Limpar
        </button>
      </div>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}{" "}
          <button type="button" onClick={() => void load(filters)}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {!error && !loading && data && data.totalItems === 0 && filters.status === "OPEN" && !filters.q && !filters.dueFrom && !filters.overdueOnly ? (
        <p>
          {emptyCompany}
          {canWrite() ? (
            <>
              {" "}
              <button type="button" className="link" onClick={() => navigate(`${base}/new`)}>
                {createLabel}
              </button>
            </>
          ) : null}
        </p>
      ) : null}
      {!error && !loading && data && data.totalItems === 0 && (filters.q || filters.dueFrom || filters.overdueOnly || filters.status !== "OPEN") ? (
        <p>
          Nenhum resultado para estes filtros.{" "}
          <button type="button" className="link" onClick={() => apply(defaultFilters())}>
            Limpar filtros
          </button>
        </p>
      ) : null}
      {data && data.items.length > 0 ? (
        <>
          <table className="desktop-table">
            <thead>
              <tr>
                <th>Referência</th>
                <th>{partyLabel}</th>
                <th>Descrição</th>
                <th>Vencimento</th>
                <th className="num">Valor original</th>
                <th className="num">Restante</th>
                <th>Situação</th>
                <th>Categoria</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <a href={`${base}/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`${base}/${item.id}`); }}>
                      <CompactRef value={item.reference} />
                    </a>
                  </td>
                  <td>{item.counterpartyName ?? "Não informado"}</td>
                  <td>{item.description}</td>
                  <td>{formatDateBr(item.dueDate)}</td>
                  <td className="num">{formatMinor(item.amountMinor)}</td>
                  <td className="num">{formatMinor(item.outstandingAmountMinor)}</td>
                  <td><StatusBadge title={item} /></td>
                  <td>{item.categoryName ?? "Não informado"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards">
            {data.items.map((item) => (
              <li key={item.id}>
                <a href={`${base}/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`${base}/${item.id}`); }}>
                  <div className="card-top">
                    <strong><CompactRef value={item.reference} /></strong>
                    <StatusBadge title={item} />
                  </div>
                  <p>{item.counterpartyName ?? "Não informado"}</p>
                  <p>{item.description}</p>
                  <p className="highlight">
                    Restante {formatMinor(item.outstandingAmountMinor)}
                  </p>
                  <p>
                    {formatDateBr(item.dueDate)} · original {formatMinor(item.amountMinor)}
                  </p>
                  <p className="muted">{item.categoryName ?? "Não informado"}</p>
                </a>
              </li>
            ))}
          </ul>
          <p className="pager">
            {data.page * data.size + 1}–{Math.min((data.page + 1) * data.size, data.totalItems)} de {data.totalItems}
            <button type="button" className="secondary" disabled={data.page === 0} onClick={() => apply({ page: data.page - 1 })}>
              Anterior
            </button>
            <button type="button" className="secondary" disabled={(data.page + 1) * data.size >= data.totalItems} onClick={() => apply({ page: data.page + 1 })}>
              Próximo
            </button>
            <select value={filters.size} onChange={(event) => apply({ size: Number(event.target.value) })} aria-label="Itens por página">
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </p>
        </>
      ) : null}
    </section>
  );
}

function TitleFormPage({ path, onDirty }: { path: string; onDirty: (value: boolean) => void }) {
  const direction = directionFromPath(path);
  const id = path.match(/\/(receivables|payables)\/([^/]+)\/edit$/)?.[2];
  const [description, setDescription] = useState("");
  const [counterpartyId, setCounterpartyId] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [amount, setAmount] = useState("");
  const [competenceDate, setCompetenceDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [reason, setReason] = useState("");
  const [version, setVersion] = useState<number | null>(null);
  const [status, setStatus] = useState<"DRAFT" | "OPEN" | "CANCELLED">("DRAFT");
  const [counterparties, setCounterparties] = useState<CatalogItem[]>([]);
  const [categories, setCategories] = useState<CatalogItem[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState("");
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState<"cp" | "cat" | null>(null);
  const pending = useRef<PendingWrite | null>(null);
  const [unknownResult, setUnknownResult] = useState(false);
  const [conflictTitle, setConflictTitle] = useState<Title | null>(null);
  const [principalLocked, setPrincipalLocked] = useState(false);
  const base = direction === "RECEIVABLE" ? "/receivables" : "/payables";

  useEffect(() => {
    void request<CatalogItem[]>(`/api/v1/catalogs/counterparties?${companyQuery(`compatibleWith=${direction}`)}`).then(setCounterparties);
    void request<CatalogItem[]>(`/api/v1/catalogs/categories?${companyQuery(`compatibleWith=${direction}`)}`).then(setCategories);
    if (id) {
      void request<Title>(`/api/v1${base}/${id}?${companyQuery()}`).then((title) => {
        setDescription(title.description);
        setCounterpartyId(title.counterpartyId ?? "");
        setSourceReference(title.sourceReference ?? "");
        setAmount(title.amountMinor ? formatMinor(title.amountMinor).replace("R$ ", "") : "");
        setCompetenceDate(title.competenceDate ?? "");
        setDueDate(title.dueDate ?? "");
        setCategoryId(title.categoryId ?? "");
        setVersion(title.version);
        setStatus(title.status);
      });
      void request<Settlement[]>(`/api/v1${base}/${id}/settlements?${companyQuery()}`)
        .then((rows) => setPrincipalLocked(Array.isArray(rows) && rows.length > 0))
        .catch(() => setPrincipalLocked(false));
    }
  }, [id, direction, base]);

  const dirty = () => onDirty(true);
  const payload = () => {
    const parsed = parseBrlInput(amount);
    return {
      description,
      counterpartyId: counterpartyId || null,
      sourceReference: sourceReference || null,
      amountMinor: parsed.minor ?? null,
      currency: "BRL",
      competenceDate: competenceDate || null,
      dueDate: dueDate || null,
      categoryId: categoryId || null,
      version,
      reason: reason || null,
    };
  };

  const submit = async (register: boolean) => {
    if (status === "CANCELLED") {
      return;
    }
    const parsed = parseBrlInput(amount);
    const nextErrors: Record<string, string> = {};
    if (!description.trim()) nextErrors.description = "Descrição é obrigatória.";
    if (parsed.error) nextErrors.amount = parsed.error;
    if (status === "OPEN" && !reason.trim()) nextErrors.reason = "Informe o motivo da correção.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      setBanner("Revise os campos destacados.");
      return;
    }
    setBusy(true);
    setBanner("");
    setUnknownResult(false);
    try {
      if (!pending.current) {
        const query = register ? companyQuery("register=true") : companyQuery();
        pending.current = freezeWrite(
          id ? `/api/v1${base}/${id}?${query}` : `/api/v1${base}?${query}`,
          id ? "PATCH" : "POST",
          payload(),
        );
      }
      const title = await sendPending<Title>(pending.current);
      pending.current = null;
      onDirty(false);
      navigate(`${base}/${title.id}`, true);
    } catch (caught) {
      const error = caught as ApiError;
      if (error.code === "STALE") {
        pending.current = null;
        setUnknownResult(false);
        setBanner(error.message);
      } else if (error.code === "VERSION_CONFLICT") {
        pending.current = null;
        setUnknownResult(false);
        setBanner("Este título foi alterado por outra pessoa. Seus valores foram mantidos.");
        if (id) {
          void request<Title>(`/api/v1${base}/${id}?${companyQuery()}`)
            .then(setConflictTitle)
            .catch(() => setConflictTitle(null));
        }
      } else if (isUnknownWriteOutcome(error)) {
        setUnknownResult(true);
        setBanner("Não foi possível confirmar o resultado. A repetição reenvia a mesma operação, sem criar outro pedido.");
      } else {
        pending.current = null;
        setUnknownResult(false);
        setBanner(error.message);
        setErrors(error.fields ?? {});
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
    <form className="form" onChange={dirty}>
      <h1 id="page-title" tabIndex={-1}>{id ? "Editar título" : direction === "RECEIVABLE" ? "Novo recebível" : "Nova conta a pagar"}</h1>
      {banner ? (
        <p className="error" tabIndex={-1} role="alert">
          {banner}
        </p>
      ) : null}
      {conflictTitle ? (
        <p className="hint" role="status">
          Versão atual no servidor: {conflictTitle.description} · {formatMinor(conflictTitle.amountMinor)}.{" "}
          <button
            type="button"
            className="link"
            onClick={() => {
              setVersion(conflictTitle.version);
              setStatus(conflictTitle.status);
              setConflictTitle(null);
              setBanner("Versão atualizada. Revise e envie novamente.");
            }}
          >
            Usar a versão atual e manter meus campos
          </button>
        </p>
      ) : null}
      <p className="muted">
        Empresa fixa. Direção: {direction === "RECEIVABLE" ? "A receber" : "A pagar"}.
      </p>
      <fieldset>
        <legend>Identificação</legend>
        <label>
          Descrição *
          <input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={200} disabled={status === "CANCELLED" || unknownResult} />
          {errors.description ? <span className="error">{errors.description}</span> : null}
        </label>
        <SearchableSelect
          label={direction === "RECEIVABLE" ? "Cliente / pagador" : "Fornecedor / favorecido"}
          value={counterpartyId}
          onChange={setCounterpartyId}
          options={counterparties}
          emptyLabel="Não informado"
          disabled={status === "CANCELLED" || unknownResult || principalLocked}
        />
        {principalLocked ? <p className="hint">Valor, contraparte e competência não podem ser alterados após existir baixa.</p> : null}
        {canWriteCatalogs() && status !== "CANCELLED" ? (
          <button type="button" className="link" onClick={() => setDialog("cp")}>
            Cadastrar contraparte
          </button>
        ) : null}
        <label>
          Referência informativa
          <input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} maxLength={100} disabled={status === "CANCELLED" || unknownResult} />
        </label>
      </fieldset>
      <fieldset className="money-row">
        <legend>Valor e datas</legend>
        <label>
          Valor (BRL)
          <input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" placeholder="1.234,56" disabled={status === "CANCELLED" || unknownResult || principalLocked} />
          {errors.amount || errors.amountMinor ? <span className="error">{errors.amount || errors.amountMinor}</span> : null}
        </label>
        <label>
          Competência
          <input type="date" value={competenceDate} onChange={(event) => setCompetenceDate(event.target.value)} disabled={status === "CANCELLED" || unknownResult || principalLocked} />
        </label>
        <label>
          Vencimento
          <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} disabled={status === "CANCELLED" || unknownResult} />
        </label>
      </fieldset>
      <fieldset>
        <legend>Classificação</legend>
        <SearchableSelect
          label="Categoria"
          value={categoryId}
          onChange={setCategoryId}
          options={categories}
          emptyLabel="Não informado"
          disabled={status === "CANCELLED" || unknownResult}
        />
        {canWriteCatalogs() && status !== "CANCELLED" ? (
          <button type="button" className="link" onClick={() => setDialog("cat")}>
            Cadastrar categoria
          </button>
        ) : null}
        {status === "OPEN" ? (
          <label>
            Motivo da correção *
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} maxLength={500} />
            {errors.reason ? <span className="error">{errors.reason}</span> : null}
          </label>
        ) : null}
      </fieldset>
      <div className="actions">
        <button type="button" className="secondary" onClick={() => navigate(id ? `${base}/${id}` : base)}>
          Cancelar edição
        </button>
        {status === "CANCELLED" ? (
          <p className="hint">Título cancelado. A alteração não é permitida.</p>
        ) : status === "OPEN" ? (
          <button type="button" disabled={busy || unknownResult} onClick={() => void submit(false)}>
            Salvar correção
          </button>
        ) : (
          <>
            <button type="button" className="secondary" disabled={busy || unknownResult} onClick={() => void submit(false)}>
              Salvar rascunho
            </button>
            <button type="button" disabled={busy || unknownResult} onClick={() => void submit(true)}>
              Registrar
            </button>
          </>
        )}
        {unknownResult ? (
          <button type="button" disabled={busy} onClick={() => void submit(false)}>
            Tentar novamente a operação pendente
          </button>
        ) : null}
      </div>
    </form>
      {dialog ? (
        <QuickCatalog
          kind={dialog}
          direction={direction}
          onClose={() => setDialog(null)}
          onCreated={(item) => {
            if (dialog === "cp") {
              setCounterparties((current) => [...current, item]);
              setCounterpartyId(item.id);
            } else {
              setCategories((current) => [...current, item]);
              setCategoryId(item.id);
            }
            setDialog(null);
          }}
        />
      ) : null}
    </>
  );
}

function QuickCatalog({
  kind,
  direction,
  onClose,
  onCreated,
}: {
  kind: "cp" | "cat";
  direction: Direction;
  onClose: () => void;
  onCreated: (item: CatalogItem) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal title={kind === "cp" ? "Cadastrar contraparte" : "Cadastrar categoria"} onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          void request<CatalogItem>(`/api/v1/catalogs/${kind === "cp" ? "counterparties" : "categories"}?${companyQuery()}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(
              kind === "cp"
                ? { name, role: direction === "RECEIVABLE" ? "CUSTOMER" : "SUPPLIER" }
                : { name, direction },
            ),
          })
            .then(onCreated)
            .catch((caught: ApiError) => setError(caught.message))
            .finally(() => setBusy(false));
        }}
      >
        <label>
          Nome
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="actions">
          <button type="button" className="secondary" onClick={onClose}>
            Voltar
          </button>
          <button type="submit" disabled={busy}>Salvar</button>
        </div>
      </form>
    </Modal>
  );
}

function TitleDetailPage({ path }: { path: string }) {
  const direction = directionFromPath(path);
  const id = path.split("/").pop() ?? "";
  const base = direction === "RECEIVABLE" ? "/receivables" : "/payables";
  const [title, setTitle] = useState<Title | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [flash, setFlash] = useState("");
  const [busy, setBusy] = useState(false);
  const [homolog, setHomolog] = useState(false);
  const [lookup, setLookup] = useState<ExternalLookup | null>(null);
  const [lookupRef, setLookupRef] = useState("");
  const [lookupBusy, setLookupBusy] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const confirmPending = useRef<PendingWrite | null>(null);
  const cancelPending = useRef<PendingWrite | null>(null);

  const loadHistory = useCallback(() => {
    setHistoryError("");
    void request<{ items: HistoryItem[] }>(`/api/v1${base}/${id}/history?${companyQuery()}`)
      .then((body) => setHistory(body.items ?? []))
      .catch((caught: ApiError) => {
        setHistory([]);
        setHistoryError(caught.message);
      });
  }, [base, id]);

  const load = useCallback(() => {
    void request<Title>(`/api/v1${base}/${id}?${companyQuery()}`)
      .then((item) => {
        if (item.direction !== direction) {
          setError("Este título não pertence a esta lista.");
          setTitle(null);
          return;
        }
        setTitle(item);
        setError("");
      })
      .catch((caught: ApiError) => setError(caught.message));
    void request<Settlement[]>(`/api/v1${base}/${id}/settlements?${companyQuery()}`)
      .then((rows) => setSettlements(Array.isArray(rows) ? rows : []))
      .catch(() => setSettlements([]));
    loadHistory();
    void loadHomologIntegration().then((enabled) => {
      setHomolog(enabled);
      if (!enabled) {
        return;
      }
      void request<ExternalLookup>(`/api/v1${base}/${id}/pay-lookup?${companyQuery()}`)
        .then((item) => {
          setLookup(item);
          setLookupRef(item.externalReference);
        })
        .catch((caught: ApiError) => {
          if (caught.status !== 404) {
            setError(caught.message);
          }
        });
    });
  }, [base, id, direction, loadHistory]);

  useEffect(() => {
    load();
  }, [load]);

  if (error && !title) {
    return <p className="error">{error}</p>;
  }
  if (!title) {
    return <p>Carregando…</p>;
  }

  const remainingPositive = Number(title.outstandingAmountMinor ?? "0") > 0;
  return (
    <article>
      <h1 id="page-title" ref={headingRef} tabIndex={-1}>
        <CompactRef value={title.reference} />
      </h1>
      {flash ? <p className="success" role="status">{flash}</p> : null}
      <p className="hint">{title.counterpartyName ?? "Não informado"} · {title.description}</p>
      <StatusBadge title={title} />
      <dl className="value-band">
        <div><dt>Original</dt><dd>{formatMinor(title.amountMinor)}</dd></div>
        <div><dt>{direction === "RECEIVABLE" ? "Recebido" : "Pago"}</dt><dd>{formatMinor(title.settledAmountMinor)}</dd></div>
        <div className={remainingPositive ? "value-band__restante" : undefined}><dt>Restante</dt><dd>{formatMinor(title.outstandingAmountMinor)}</dd></div>
      </dl>
      <dl className="facts">
        <div><dt>{direction === "RECEIVABLE" ? "Cliente / pagador" : "Fornecedor / favorecido"}</dt><dd>{title.counterpartyName ?? "Não informado"}{title.counterpartyId && !title.counterpartyActive ? " (inativo)" : ""}</dd></div>
        <div><dt>Descrição</dt><dd>{title.description}</dd></div>
        <div><dt>Competência</dt><dd>{formatDateBr(title.competenceDate)}</dd></div>
        <div><dt>Vencimento</dt><dd>{formatDateBr(title.dueDate)}</dd></div>
        <div><dt>Categoria</dt><dd>{title.categoryName ?? "Não informado"}{title.categoryId && !title.categoryActive ? " (inativa)" : ""}</dd></div>
        <div><dt>Origem</dt><dd>Manual</dd></div>
        <div><dt>Referência informativa</dt><dd>{title.sourceReference ?? "Não informado"}</dd></div>
        {title.demoCompany ? <div><dt>Ambiente</dt><dd>Dado de demonstração local</dd></div> : null}
      </dl>
      {homolog ? (
        <section className="homolog-lookup">
          <h2>Acompanhamento no ActionHub Pay</h2>
          <p className="hint" role="status">Homologação — sem movimentação real. A consulta não baixa este título.</p>
          <dl className="facts">
            <div><dt>Registro no controle</dt><dd>{title.reference} · {formatMinor(title.amountMinor)}</dd></div>
            <div><dt>Observação financeira</dt><dd data-lookup-observation>{lookup ? labelExternalStatus(lookup.externalStatus) : "Ainda não consultada"}</dd></div>
            <div><dt>Última tentativa</dt><dd data-lookup-attempt>{lookup ? labelAttempt(lookup.lastAttemptOutcome) : "—"}</dd></div>
            <div><dt>Referência no Pay</dt><dd>{lookup?.externalReference ?? "Não informada"}</dd></div>
            <div><dt>Observada em</dt><dd>{lookup?.observedAt ? new Date(lookup.observedAt).toLocaleString("pt-BR") : "Sem carimbo do provedor"}</dd></div>
            <div><dt>Tentativa em</dt><dd>{lookup?.lastAttemptAt ? new Date(lookup.lastAttemptAt).toLocaleString("pt-BR") : "—"}</dd></div>
            <div><dt>Valor observado</dt><dd>{lookup?.amountMinor ? formatMinor(lookup.amountMinor) : "—"}</dd></div>
            <div><dt>Origem da resposta</dt><dd>{labelOrigin(lookup?.providerOrigin)}</dd></div>
          </dl>
          {lookup?.lastError ? <p className="error" role="alert">{lookup.lastError}</p> : null}
          <label>
            Referência do pagamento de teste
            <input
              value={lookupRef}
              onChange={(event) => setLookupRef(event.target.value)}
              maxLength={80}
              autoComplete="off"
            />
          </label>
          <div className="actions">
            <button
              type="button"
              disabled={lookupBusy || !lookupRef.trim()}
              onClick={() => {
                setLookupBusy(true);
                void request<ExternalLookup>(`/api/v1${base}/${title.id}/pay-lookup?${companyQuery()}`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ externalReference: lookupRef.trim() }),
                })
                  .then((item) => {
                    setLookup(item);
                    setLookupRef(item.externalReference);
                    setFlash(flashForLookup(item));
                    setError("");
                  })
                  .catch((caught: ApiError) => setError(caught.message))
                  .finally(() => setLookupBusy(false));
              }}
            >
              {lookup ? "Consultar resultado" : "Consultar no ActionHub Pay"}
            </button>
          </div>
          {lookup ? (
            <details>
              <summary>Detalhes de rastreio</summary>
              <dl className="facts">
                <div><dt>Correlação da operação</dt><dd>{lookup.correlationId}</dd></div>
                <div><dt>Tentativa</dt><dd>{lookup.lastAttemptId ?? "—"}</dd></div>
                <div><dt>Decisão</dt><dd>{lookup.spiderDecisionId ?? "—"}</dd></div>
                <div><dt>Entrega</dt><dd>{labelDelivery(lookup.deliveryStatus)}</dd></div>
              </dl>
            </details>
          ) : null}
        </section>
      ) : null}
      {(canWrite() || canWriteSettlements()) && title.status !== "CANCELLED" ? (
        <div className="actions">
          {canWriteSettlements() && title.status === "OPEN" && title.settlementStatus !== "SETTLED" ? (
            <button type="button" onClick={() => navigate(`${base}/${title.id}/settlements/new`)}>
              {direction === "RECEIVABLE" ? "Registrar recebimento" : "Registrar pagamento"}
            </button>
          ) : null}
          {canWrite() ? (
          <button type="button" className="secondary" onClick={() => navigate(`${base}/${title.id}/edit`)}>
            {title.status === "OPEN" ? "Corrigir" : "Editar rascunho"}
          </button>
          ) : null}
          {title.status === "DRAFT" ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setBusy(true);
                confirmPending.current = freezeWrite(
                  `/api/v1${base}/${title.id}/confirm?${companyQuery()}`,
                  "POST",
                  { version: title.version },
                  confirmPending.current,
                );
                void sendPending<Title>(confirmPending.current)
                  .then((item) => {
                    confirmPending.current = null;
                    setTitle(item);
                    setFlash(direction === "RECEIVABLE" ? "Recebível registrado. Não houve movimentação financeira." : "Conta a pagar registrada. Não houve movimentação financeira.");
                    load();
                  })
                  .catch((caught: ApiError) => {
                    if (caught.code === "STALE" || !isUnknownWriteOutcome(caught)) {
                      confirmPending.current = null;
                    }
                    setError(
                      isUnknownWriteOutcome(caught)
                        ? "Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação."
                        : caught.message,
                    );
                  })
                  .finally(() => setBusy(false));
              }}
            >
              Confirmar
            </button>
          ) : null}
          {canWrite() && Number(title.settledAmountMinor ?? "0") > 0 ? (
            <p className="hint">Estorne os registros de baixa antes de cancelar este título.</p>
          ) : canWrite() ? (
          <button type="button" className="danger" onClick={() => setCancelOpen(true)}>
            Cancelar título
          </button>
          ) : null}
        </div>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      <h2>Baixas</h2>
      {settlements.length === 0 ? <p className="muted">Nenhum registro de baixa neste título.</p> : (
        <>
          <table className="desktop-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Conta</th>
                <th>Meio</th>
                <th className="num">Valor</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {settlements.map((item) => (
                <tr key={item.id}>
                  <td>
                    <a href={`/settlements/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`/settlements/${item.id}`); }}>
                      {formatDateBr(item.effectiveDate)}
                    </a>
                  </td>
                  <td>{item.accountName}</td>
                  <td>{formatMethodLabel(item.method)}</td>
                  <td className="num">{formatMinor(item.amountMinor)}</td>
                  <td>{item.reversed ? "Estornado" : "Ativo"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards">
            {settlements.map((item) => (
              <li key={item.id}>
                <a href={`/settlements/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`/settlements/${item.id}`); }}>
                  {formatDateBr(item.effectiveDate)} · {item.accountName} · {formatMethodLabel(item.method)} · {formatMinor(item.amountMinor)} · {item.reversed ? "Estornado" : "Ativo"}
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
      <h2>Histórico</h2>
      {historyError ? (
        <p className="error" role="alert">
          {historyError}{" "}
          <button type="button" onClick={loadHistory}>
            Tentar novamente
          </button>
        </p>
      ) : (
        <ol className="history">
          {history.map((item) => (
            <li key={item.id}>
              <strong>{labelAction(item.action)}</strong> · {item.actorDisplayName} · {new Date(item.occurredAt).toLocaleString("pt-BR")}
              {item.reason ? <p>Motivo: {item.reason}</p> : null}
              <ul>{humanChanges(item.changesJson).map((line) => <li key={line}>{line}</li>)}</ul>
            </li>
          ))}
        </ol>
      )}
      {cancelOpen ? (
        <Modal title="Cancelar este título?" onClose={() => !busy && setCancelOpen(false)}>
          <p>
            <CompactRef value={title.reference} /> · {formatMinor(title.amountMinor)}. Isso retira o compromisso das previsões e não desfaz movimentação bancária.
          </p>
          <label>
            Motivo
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} minLength={3} maxLength={500} required disabled={busy} />
          </label>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => setCancelOpen(false)}>
              Voltar
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setBusy(true);
                setError("");
                cancelPending.current = freezeWrite(
                  `/api/v1${base}/${title.id}/cancel?${companyQuery()}`,
                  "POST",
                  { version: title.version, reason },
                  cancelPending.current,
                );
                void sendPending<Title>(cancelPending.current)
                  .then((item) => {
                    cancelPending.current = null;
                    setTitle(item);
                    setCancelOpen(false);
                    headingRef.current?.focus();
                    load();
                  })
                  .catch((caught: ApiError) => {
                    if (caught.code === "STALE" || !isUnknownWriteOutcome(caught)) {
                      cancelPending.current = null;
                    }
                    setError(
                      isUnknownWriteOutcome(caught)
                        ? "Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação."
                        : caught.message,
                    );
                  })
                  .finally(() => setBusy(false));
              }}
              className="danger"
            >
              Cancelar título
            </button>
          </div>
        </Modal>
      ) : null}
    </article>
  );
}

function CatalogsPage({ path, onDirty }: { path: string; onDirty: (value: boolean) => void }) {
  const tab = path.includes("categories") ? "categories" : "counterparties";
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [name, setName] = useState("");
  const [kind, setKind] = useState(tab === "categories" ? "BOTH" : "BOTH");
  const [editing, setEditing] = useState<CatalogItem | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editName, setEditName] = useState("");

  const companyId = getSession()?.companyId;
  const load = useCallback(() => {
    setError("");
    void request<CatalogItem[]>(`/api/v1/catalogs/${tab}?companyId=${encodeURIComponent(companyId ?? "")}`)
      .then(setItems)
      .catch((caught: ApiError) => setError(caught.message));
  }, [tab, companyId]);
  useEffect(() => {
    load();
  }, [load]);

  return (
    <section>
      <PageHeader title="Cadastros" hint="Contrapartes e categorias da empresa ativa." />
      <div className="tabs">
        <button type="button" className={tab === "counterparties" ? "active" : ""} onClick={() => navigate("/catalogs/counterparties")}>
          Contrapartes
        </button>
        <button type="button" className={tab === "categories" ? "active" : ""} onClick={() => navigate("/catalogs/categories")}>
          Categorias
        </button>
      </div>
      {canWriteCatalogs() ? (
        <form
          className="inline"
          onSubmit={(event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            void request<CatalogItem>(`/api/v1/catalogs/${tab}?${companyQuery()}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(tab === "counterparties" ? { name, role: kind } : { name, direction: kind }),
            })
              .then(() => {
                setName("");
                onDirty(false);
                load();
              })
              .catch((caught: ApiError) => setError(caught.message))
              .finally(() => setBusy(false));
          }}
          onChange={() => onDirty(true)}
        >
          <label>
            Nome
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label>
            {tab === "counterparties" ? "Papel" : "Natureza"}
            <select value={kind} onChange={(event) => setKind(event.target.value)}>
              {tab === "counterparties" ? (
                <>
                  <option value="CUSTOMER">Cliente</option>
                  <option value="SUPPLIER">Fornecedor</option>
                  <option value="BOTH">Ambos</option>
                </>
              ) : (
                <>
                  <option value="RECEIVABLE">A receber</option>
                  <option value="PAYABLE">A pagar</option>
                  <option value="BOTH">Ambas</option>
                </>
              )}
            </select>
          </label>
          <button type="submit" disabled={busy}>Criar</button>
        </form>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}{" "}
          <button type="button" onClick={load}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      <table className="desktop-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>{tab === "counterparties" ? "Papel" : "Natureza"}</th>
            <th>Situação</th>
            {canWriteCatalogs() ? <th>Ações</th> : null}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>{item.role ?? item.direction}</td>
              <td>{item.active ? "Ativo" : "Inativo"}</td>
              {canWriteCatalogs() ? (
                <td>
                  <button type="button" className="link" onClick={() => { setEditing(item); setEditName(item.name); }}>
                    Editar
                  </button>
                  {item.active ? (
                    <button
                      type="button"
                      className="link"
                      onClick={() => {
                        if (window.confirm("Inativar? Títulos anteriores permanecem vinculados.")) {
                          setBusy(true);
                          setError("");
                          void request(`/api/v1/catalogs/${tab}/${item.id}?${companyQuery()}`, {
                            method: "PATCH",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ version: item.version, active: false }),
                          })
                            .then(load)
                            .catch((caught: ApiError) => setError(caught.message))
                            .finally(() => setBusy(false));
                        }
                      }}
                    >
                      Inativar
                    </button>
                  ) : null}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cards catalog-cards">
        {items.map((item) => (
          <li key={`card-${item.id}`}>
            <strong>{item.name}</strong>
            <p>{item.role ?? item.direction} · {item.active ? "Ativo" : "Inativo"}</p>
            {canWriteCatalogs() ? (
              <button type="button" className="link" onClick={() => { setEditing(item); setEditName(item.name); }}>
                Editar
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {editing ? (
        <Modal title="Editar cadastro" onClose={() => !busy && setEditing(null)}>
          <label>
            Nome
            <input value={editName} onChange={(event) => setEditName(event.target.value)} />
          </label>
          {error ? <p className="error" role="alert">{error}</p> : null}
          <div className="actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => setEditing(null)}>
              Voltar
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setBusy(true);
                setError("");
                void request(`/api/v1/catalogs/${tab}/${editing.id}?${companyQuery()}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ version: editing.version, name: editName }),
                })
                  .then(() => {
                    setEditing(null);
                    load();
                  })
                  .catch((caught: ApiError) => setError(caught.message))
                  .finally(() => setBusy(false));
              }}
            >
              Salvar
            </button>
          </div>
        </Modal>
      ) : null}
    </section>
  );
}

function labelExternalStatus(status: string): string {
  return {
    AWAITING_SEND: "Aguardando envio",
    ACCEPTED: "Solicitação aceita",
    IN_PROGRESS: "Em processamento",
    CONFIRMED: "Confirmado pelo Pay",
    REFUSED: "Recusado",
    REFUNDED: "Estornado pelo Pay — sem baixa automática",
    UNKNOWN: "Resultado desconhecido",
    REVIEW_REQUIRED: "Requer revisão",
  }[status] ?? status;
}

function labelAttempt(outcome: string | null | undefined): string {
  return {
    STARTED: "Consulta iniciada, ainda sem resultado",
    DELIVERED: "Resposta válida recebida",
    UNAVAILABLE: "Falha de transporte — observação anterior preservada",
    REJECTED: "Spider recusou a consulta",
    INVALID: "Resposta rejeitada por identidade",
    CONFLICT: "Divergência em revisão",
    RECOVERED: "Consulta interrompida — tente novamente",
  }[outcome ?? ""] ?? (outcome || "—");
}

function flashForLookup(item: ExternalLookup): string {
  if (item.lastAttemptOutcome === "UNAVAILABLE" || item.lastAttemptOutcome === "RECOVERED") {
    return "Não foi possível atualizar. A observação anterior foi preservada. O título não foi baixado.";
  }
  if (item.externalStatus === "REVIEW_REQUIRED") {
    return "A observação exige revisão. O título não foi baixado.";
  }
  return "Consulta atualizada. O título não foi baixado.";
}

function labelOrigin(origin: string | null | undefined): string {
  if (origin === "SIMULATOR") {
    return "Simulador da borda Pay";
  }
  if (origin === "ACTIONHUB_PAY") {
    return "ActionHub Pay (resposta validada)";
  }
  return origin ?? "—";
}

function labelDelivery(status: string): string {
  return {
    PENDING: "Aguardando resposta",
    DELIVERED: "Resposta recebida",
    LOST_RESPONSE: "Resposta perdida",
    CONFLICT: "Conflito",
    UNAVAILABLE: "Spider indisponível",
  }[status] ?? status;
}

function labelAction(action: string): string {
  return {
    CREATED: "Criado",
    UPDATED: "Atualizado",
    CONFIRMED: "Confirmado",
    CANCELLED: "Cancelado",
    SETTLEMENT_RECORDED: "Baixa registrada",
    SETTLEMENT_REVERSED: "Registro estornado",
  }[action] ?? action;
}

function humanChanges(json: string): string[] {
  try {
    const parsed = JSON.parse(json) as { fields?: { field: string; before: unknown; after: unknown }[] };
    const labels: Record<string, string> = {
      description: "Descrição",
      status: "Situação",
      amountMinor: "Valor",
      competenceDate: "Competência",
      dueDate: "Vencimento",
      sourceReference: "Referência informativa",
      counterparty: "Contraparte",
      category: "Categoria",
    };
    return (parsed.fields ?? []).map((field) => {
      const before = formatHistoryValue(field.field, field.before);
      const after = formatHistoryValue(field.field, field.after);
      return `${labels[field.field] ?? field.field}: ${before} → ${after}`;
    });
  } catch {
    return [];
  }
}

function SettlementFormPage({ path, onDirty }: { path: string; onDirty: (value: boolean) => void }) {
  const direction = directionFromPath(path);
  const titleId = path.match(/\/(receivables|payables)\/([^/]+)\/settlements\/new$/)?.[2] ?? "";
  const base = direction === "RECEIVABLE" ? "/receivables" : "/payables";
  const [title, setTitle] = useState<Title | null>(null);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [method, setMethod] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState("");
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const [createAccount, setCreateAccount] = useState(false);
  const pending = useRef<PendingWrite | null>(null);
  const titleRef = useRef<Title | null>(null);

  useEffect(() => {
    void request<Title>(`/api/v1${base}/${titleId}?${companyQuery()}`).then((item) => {
      setTitle(item);
      titleRef.current = item;
      setAmount(item.outstandingAmountMinor ? formatMinor(item.outstandingAmountMinor).replace("R$ ", "").replace("R$ -", "-") : "");
      setEffectiveDate(item.businessDate);
    });
    void request<FinancialAccount[]>(`/api/v1/financial-accounts?${companyQuery()}`)
      .then((items) => setAccounts(items.filter((item) => item.active)))
      .catch(() => setAccounts([]));
  }, [base, titleId]);

  const applyWriteError = (caught: ApiError) => {
    if (caught.code === "STALE") {
      pending.current = null;
      setUnknownResult(false);
      setBanner(caught.message);
      return;
    }
    if (caught.code === "VERSION_CONFLICT") {
      pending.current = null;
      setUnknownResult(false);
      void request<Title>(`/api/v1${base}/${titleId}?${companyQuery()}`)
        .then((fresh) => {
          setTitle(fresh);
          titleRef.current = fresh;
          setBanner(
            `Este título foi alterado por outra pessoa. O restante atual é ${formatMinor(fresh.outstandingAmountMinor)}. Revise o valor e envie novamente.`,
          );
        })
        .catch(() => {
          setBanner("Este título foi alterado por outra pessoa. Revise o restante atual e envie novamente.");
        });
      return;
    }
    if (isUnknownWriteOutcome(caught)) {
      setUnknownResult(true);
      setBanner("Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação.");
      return;
    }
    pending.current = null;
    setUnknownResult(false);
    setErrors(caught.fields ?? {});
    if (caught.fields?.outstandingAmountMinor) {
      setBanner(`O restante atual é ${formatMinor(caught.fields.outstandingAmountMinor)}. Revise o valor.`);
    } else {
      setBanner(caught.message);
    }
  };

  const sendSettlement = (existing?: PendingWrite | null) => {
    const currentTitle = titleRef.current;
    if (!currentTitle) {
      return;
    }
    const parsed = parseBrlInput(amount);
    setBusy(true);
    setBanner("");
    pending.current = freezeWrite(
      `/api/v1${base}/${currentTitle.id}/settlements?${companyQuery()}`,
      "POST",
      {
        accountId,
        amountMinor: parsed.minor,
        effectiveDate,
        method,
        note: note || null,
        version: currentTitle.version,
      },
      existing,
    );
    onDirty(true);
    void sendPending<Settlement>(pending.current)
      .then((item) => {
        pending.current = null;
        setUnknownResult(false);
        onDirty(false);
        navigate(`${base}/${currentTitle.id}?destaque=${item.id}`);
      })
      .catch((caught: ApiError) => applyWriteError(caught))
      .finally(() => setBusy(false));
  };

  if (!title) {
    return <p>Carregando…</p>;
  }

  return (
    <section>
      <h1 id="page-title" tabIndex={-1}>
        {direction === "RECEIVABLE" ? "Registrar recebimento realizado" : "Registrar pagamento realizado"}
      </h1>
      <p>{title.counterpartyName ?? "Não informado"} · <CompactRef value={title.reference} /> · restante {formatMinor(title.outstandingAmountMinor)}</p>
      <p className="hint">Este registro atualiza seu controle financeiro. Não envia nem movimenta dinheiro.</p>
      {accounts.length === 0 ? (
        <p>
          Nenhuma conta ativa nesta empresa.{" "}
          {canWriteAccounts() ? (
            <button type="button" className="link" onClick={() => setCreateAccount(true)}>
              Criar conta
            </button>
          ) : null}
        </p>
      ) : null}
      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault();
          if (unknownResult) {
            return;
          }
          const parsed = parseBrlInput(amount);
          const nextErrors: Record<string, string> = {};
          if (!accountId) nextErrors.accountId = "Selecione a conta financeira.";
          if (parsed.error || !parsed.minor) nextErrors.amount = parsed.error ?? "Informe o valor.";
          if (!effectiveDate) nextErrors.effectiveDate = "Informe a data efetiva.";
          if (!method) nextErrors.method = "Informe o meio.";
          setErrors(nextErrors);
          if (Object.keys(nextErrors).length) {
            setBanner("Revise os campos destacados.");
            return;
          }
          sendSettlement(null);
        }}
        onChange={() => onDirty(true)}
      >
        <SearchableSelect
          label="Conta financeira"
          value={accountId}
          onChange={setAccountId}
          options={accounts.map((item) => ({ id: item.id, code: item.code, name: item.name, active: item.active, version: item.version }))}
          emptyLabel="Selecione"
          disabled={unknownResult}
        />
        {errors.accountId ? <span className="error">{errors.accountId}</span> : null}
        {canWriteAccounts() ? (
          <button type="button" className="link" onClick={() => setCreateAccount(true)} disabled={unknownResult}>
            Criar conta
          </button>
        ) : null}
        <label>
          Valor
          <input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" disabled={unknownResult} />
        </label>
        {errors.amount || errors.amountMinor ? <span className="error">{errors.amount || errors.amountMinor}</span> : null}
        <label>
          Data efetiva
          <input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} disabled={unknownResult} />
        </label>
        {errors.effectiveDate ? <span className="error">{errors.effectiveDate}</span> : null}
        <label>
          Meio
          <select value={method} onChange={(event) => setMethod(event.target.value)} disabled={unknownResult}>
            <option value="">Selecione</option>
            <option value="PIX">Pix</option>
            <option value="BANK_TRANSFER">Transferência</option>
            <option value="CASH">Dinheiro</option>
            <option value="CARD">Cartão</option>
            <option value="OTHER">Outro</option>
          </select>
        </label>
        {errors.method ? <span className="error">{errors.method}</span> : null}
        <label>
          Observação
          <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} disabled={unknownResult} />
        </label>
        {banner ? <p className="error" role="alert">{banner}</p> : null}
        <div className="actions">
          <button type="button" className="secondary" onClick={() => navigate(`${base}/${title.id}`)}>
            Voltar
          </button>
          <button type="submit" disabled={busy || unknownResult}>
            {direction === "RECEIVABLE" ? "Registrar recebimento" : "Registrar pagamento"}
          </button>
          {unknownResult ? (
            <button
              type="button"
              disabled={busy || !pending.current}
              onClick={() => {
                if (!pending.current) return;
                sendSettlement(pending.current);
              }}
            >
              Tentar novamente
            </button>
          ) : null}
        </div>
      </form>
      {createAccount ? (
        <AccountCreateDialog
          onClose={() => setCreateAccount(false)}
          onCreated={(account) => {
            setAccounts((current) => [...current, account]);
            setAccountId(account.id);
            setCreateAccount(false);
          }}
        />
      ) : null}
    </section>
  );
}

function SettlementDetailPage({ path }: { path: string }) {
  const id = path.split("/").pop() ?? "";
  const [item, setItem] = useState<Settlement | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const pending = useRef<PendingWrite | null>(null);
  const itemRef = useRef<Settlement | null>(null);

  const load = useCallback(() => {
    void request<Settlement>(`/api/v1/settlements/${id}?${companyQuery()}`)
      .then((row) => {
        setItem(row);
        itemRef.current = row;
        setEffectiveDate((current) => current || row.effectiveDate);
        setError("");
      })
      .catch((caught: ApiError) => setError(caught.message));
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);

  const applyReversalError = (caught: ApiError) => {
    if (caught.code === "STALE") {
      pending.current = null;
      setUnknownResult(false);
      setError(caught.message);
      return;
    }
    if (caught.code === "VERSION_CONFLICT") {
      pending.current = null;
      setUnknownResult(false);
      void request<Settlement>(`/api/v1/settlements/${id}?${companyQuery()}`)
        .then((fresh) => {
          setItem(fresh);
          itemRef.current = fresh;
          setError(
            `Este título foi alterado por outra pessoa. O restante atual é ${formatMinor(fresh.titleOutstandingAmountMinor)}. Revise e confirme o estorno novamente.`,
          );
        })
        .catch(() => {
          setError("Este título foi alterado por outra pessoa. Revise o restante atual e confirme o estorno novamente.");
        });
      return;
    }
    if (isUnknownWriteOutcome(caught)) {
      setUnknownResult(true);
      setError("Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação.");
      return;
    }
    pending.current = null;
    setUnknownResult(false);
    setError(caught.message);
  };

  if (error && !item) {
    return <p className="error">{error}</p>;
  }
  if (!item) {
    return <p>Carregando…</p>;
  }
  const titleBase = item.direction === "RECEIVABLE" ? "/receivables" : "/payables";
  return (
    <article>
      <h1 id="page-title" tabIndex={-1}>
        Registro de baixa
      </h1>
      <p>
        <a href={`${titleBase}/${item.titleId}`} onClick={(event) => { event.preventDefault(); navigate(`${titleBase}/${item.titleId}`); }}>
          <CompactRef value={item.titleReference} />
        </a>
        {" · "}
        {item.counterpartyName ?? "Não informado"}
      </p>
      <dl className="facts">
        <div><dt>Conta</dt><dd>{item.accountName}{item.accountActive ? "" : " (inativa)"}</dd></div>
        <div><dt>Data efetiva</dt><dd>{formatDateBr(item.effectiveDate)}</dd></div>
        <div><dt>Valor</dt><dd>{formatMinor(item.amountMinor)}</dd></div>
        <div><dt>Meio</dt><dd>{formatMethodLabel(item.method)}</dd></div>
        <div><dt>Origem</dt><dd>Registro manual</dd></div>
        <div><dt>Autor</dt><dd>{item.actorDisplayName} · {new Date(item.recordedAt).toLocaleString("pt-BR")}</dd></div>
        {item.note ? <div><dt>Observação</dt><dd>{item.note}</dd></div> : null}
        {item.reversed ? (
          <>
            <div><dt>Situação</dt><dd>Estornado</dd></div>
            <div><dt>Motivo do estorno</dt><dd>{item.reversalReason}</dd></div>
            <div><dt>Data do estorno</dt><dd>{formatDateBr(item.reversalEffectiveDate)}</dd></div>
            <div><dt>Autor do estorno</dt><dd>{item.reversalActorDisplayName} · {item.reversalRecordedAt ? new Date(item.reversalRecordedAt).toLocaleString("pt-BR") : ""}</dd></div>
          </>
        ) : (
          <div><dt>Situação</dt><dd>Ativo</dd></div>
        )}
      </dl>
      {canReverseSettlements() && !item.reversed ? (
        <button type="button" onClick={() => setOpen(true)}>
          Estornar registro
        </button>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {open ? (
        <Modal title="Estornar este registro?" onClose={() => !busy && setOpen(false)}>
          <p>
            {formatMinor(item.amountMinor)} em {item.accountName}. O restante do título volta a incluir este valor.
          </p>
          <p className="hint">O estorno corrige o controle financeiro. Nenhuma devolução ou operação bancária será enviada.</p>
          <label>
            Data do estorno
            <input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} disabled={busy || unknownResult} />
          </label>
          <label>
            Motivo
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} minLength={3} maxLength={500} required disabled={busy || unknownResult} />
          </label>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => setOpen(false)}>
              Voltar
            </button>
            <button
              type="button"
              disabled={busy || unknownResult}
              onClick={() => {
                const current = itemRef.current ?? item;
                setBusy(true);
                setError("");
                pending.current = freezeWrite(
                  `/api/v1/settlements/${current.id}/reversal?${companyQuery()}`,
                  "POST",
                  { effectiveDate, reason, version: current.titleVersion },
                  null,
                );
                void sendPending<Settlement>(pending.current)
                  .then(() => {
                    pending.current = null;
                    setUnknownResult(false);
                    setOpen(false);
                    load();
                  })
                  .catch((caught: ApiError) => applyReversalError(caught))
                  .finally(() => setBusy(false));
              }}
              className="danger"
            >
              Confirmar estorno do registro
            </button>
            {unknownResult ? (
              <button
                type="button"
                disabled={busy || !pending.current}
                onClick={() => {
                  if (!pending.current) return;
                  setBusy(true);
                  setError("");
                  void sendPending<Settlement>(pending.current)
                    .then(() => {
                      pending.current = null;
                      setUnknownResult(false);
                      setOpen(false);
                      load();
                    })
                    .catch((caught: ApiError) => applyReversalError(caught))
                    .finally(() => setBusy(false));
                }}
              >
                Tentar novamente
              </button>
            ) : null}
          </div>
        </Modal>
      ) : null}
    </article>
  );
}

function AccountsRouter({ path, onDirty }: { path: string; onDirty: (value: boolean) => void }) {
  if (path === "/financial-accounts/new") {
    return <AccountFormPage onDirty={onDirty} />;
  }
  if (/\/financial-accounts\/[^/]+$/.test(path) && path !== "/financial-accounts/new") {
    return <AccountDetailPage path={path} onDirty={onDirty} />;
  }
  return <AccountListPage />;
}

function AccountListPage() {
  const [items, setItems] = useState<FinancialAccount[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    void request<FinancialAccount[]>(`/api/v1/financial-accounts?${companyQuery()}`)
      .then(setItems)
      .catch((caught: ApiError) => setError(caught.message));
  }, []);
  const companyId = getSession()?.companyId;
  useEffect(() => {
    load();
  }, [load, companyId]);
  return (
    <section>
      <PageHeader
        title="Contas financeiras"
        hint="Saldos gerenciais desta empresa. Não são saldos bancários confirmados."
        action={
          canWriteAccounts() ? (
            <button type="button" onClick={() => navigate("/financial-accounts/new")}>
              Nova conta
            </button>
          ) : null
        }
      />
      {error ? <p className="error">{error}</p> : null}
      <table className="desktop-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Tipo</th>
            <th>Situação</th>
            <th className="num">Saldo gerencial</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <a href={`/financial-accounts/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`/financial-accounts/${item.id}`); }}>
                  {item.name}
                </a>
              </td>
              <td>{formatAccountType(item.type)}</td>
              <td>{item.active ? "Ativa" : "Inativa"}</td>
              <td className="num">{formatMinor(item.currentBalanceMinor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cards">
        {items.map((item) => (
          <li key={item.id}>
            <a href={`/financial-accounts/${item.id}`} onClick={(event) => { event.preventDefault(); navigate(`/financial-accounts/${item.id}`); }}>
              <strong>{item.name}</strong>
              <p>{formatAccountType(item.type)} · {item.active ? "Ativa" : "Inativa"}</p>
              <p className="highlight">{formatMinor(item.currentBalanceMinor)}</p>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

function applyAccountWriteError(
  caught: ApiError,
  pending: { current: PendingWrite | null },
  setUnknownResult: (value: boolean) => void,
  setError: (value: string) => void,
) {
  if (caught.code === "STALE") {
    pending.current = null;
    setUnknownResult(false);
    setError(caught.message);
    return;
  }
  if (isUnknownWriteOutcome(caught)) {
    setUnknownResult(true);
    setError("Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação.");
    return;
  }
  pending.current = null;
  setUnknownResult(false);
  setError(caught.message);
}

function AccountFormPage({ onDirty }: { onDirty: (value: boolean) => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [openedOn, setOpenedOn] = useState("");
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const pending = useRef<PendingWrite | null>(null);

  const sendCreate = (existing?: PendingWrite | null) => {
    const parsed = parseSignedBrlInput(opening);
    if (!existing && (!name.trim() || !type || !openedOn || parsed.error || parsed.minor == null)) {
      setError(parsed.error ?? "Preencha nome, tipo, data e saldo inicial.");
      return;
    }
    setBusy(true);
    setError("");
    pending.current = freezeWrite(
      `/api/v1/financial-accounts?${companyQuery()}`,
      "POST",
      { name: name.trim(), type, openedOn, openingBalanceMinor: parsed.minor },
      existing,
    );
    void sendPending<FinancialAccount>(pending.current)
      .then((account) => {
        pending.current = null;
        setUnknownResult(false);
        onDirty(false);
        navigate(`/financial-accounts/${account.id}`);
      })
      .catch((caught: ApiError) => applyAccountWriteError(caught, pending, setUnknownResult, setError))
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <h1 id="page-title" tabIndex={-1}>
        Nova conta financeira
      </h1>
      <p className="hint">Informe o saldo no início desse dia. As movimentações registradas a partir dele atualizarão o saldo gerencial.</p>
      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault();
          if (unknownResult) {
            return;
          }
          sendCreate(null);
        }}
        onChange={() => onDirty(true)}
      >
        <label>
          Nome
          <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} disabled={unknownResult} />
        </label>
        <label>
          Tipo
          <select value={type} onChange={(event) => setType(event.target.value)} required disabled={unknownResult}>
            <option value="">Selecione</option>
            <option value="BANK">Banco</option>
            <option value="CASH">Caixa físico</option>
            <option value="OTHER">Outra</option>
          </select>
        </label>
        <label>
          Início do controle
          <input type="date" value={openedOn} onChange={(event) => setOpenedOn(event.target.value)} required disabled={unknownResult} />
        </label>
        <label>
          Saldo inicial
          <input value={opening} onChange={(event) => setOpening(event.target.value)} required disabled={unknownResult} />
        </label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="actions">
          <button type="button" className="secondary" onClick={() => navigate("/financial-accounts")}>
            Voltar
          </button>
          <button type="submit" disabled={busy || unknownResult}>
            Criar conta
          </button>
          {unknownResult ? (
            <button type="button" disabled={busy || !pending.current} onClick={() => sendCreate(pending.current)}>
              Tentar novamente
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

function AccountDetailPage({ path, onDirty }: { path: string; onDirty: (value: boolean) => void }) {
  const id = path.split("/").pop() ?? "";
  const [account, setAccount] = useState<FinancialAccount | null>(null);
  const [movements, setMovements] = useState<MovementPage | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(0);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [statementError, setStatementError] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [renameUnknown, setRenameUnknown] = useState(false);
  const [statusUnknown, setStatusUnknown] = useState(false);
  const renamePending = useRef<PendingWrite | null>(null);
  const statusPending = useRef<PendingWrite | null>(null);
  const accountRef = useRef<FinancialAccount | null>(null);
  const loadGen = useRef(0);

  useEffect(() => {
    void request<FinancialAccount>(`/api/v1/financial-accounts/${id}?${companyQuery()}`)
      .then((item) => {
        setAccount(item);
        accountRef.current = item;
        setName(item.name);
        setFrom((current) => current || item.openedOn);
        setTo((current) => current || new Date().toISOString().slice(0, 10));
      })
      .catch((caught: ApiError) => setError(caught.message));
  }, [id]);

  useEffect(() => {
    if (!from || !to) {
      return;
    }
    const gen = ++loadGen.current;
    setMovements(null);
    setStatementError("");
    void request<MovementPage>(`/api/v1/financial-accounts/${id}/movements?${companyQuery(`from=${from}&to=${to}&page=${page}&size=20`)}`)
      .then((result) => {
        if (gen !== loadGen.current) {
          return;
        }
        setMovements(result);
      })
      .catch((caught: ApiError) => {
        if (gen !== loadGen.current) {
          return;
        }
        setStatementError(caught.message);
      });
  }, [id, from, to, page]);

  const sendRename = (existing?: PendingWrite | null) => {
    const current = accountRef.current;
    if (!current) {
      return;
    }
    setBusy(true);
    setError("");
    renamePending.current = freezeWrite(
      `/api/v1/financial-accounts/${current.id}?${companyQuery()}`,
      "PATCH",
      { name, version: current.version },
      existing,
    );
    void sendPending<FinancialAccount>(renamePending.current)
      .then((item) => {
        renamePending.current = null;
        setRenameUnknown(false);
        setAccount(item);
        accountRef.current = item;
        setName(item.name);
        onDirty(false);
      })
      .catch((caught: ApiError) => applyAccountWriteError(caught, renamePending, setRenameUnknown, setError))
      .finally(() => setBusy(false));
  };

  const sendStatus = (existing?: PendingWrite | null) => {
    const current = accountRef.current;
    if (!current) {
      return;
    }
    setBusy(true);
    setError("");
    statusPending.current = freezeWrite(
      `/api/v1/financial-accounts/${current.id}?${companyQuery()}`,
      "PATCH",
      { version: current.version, active: !current.active },
      existing,
    );
    void sendPending<FinancialAccount>(statusPending.current)
      .then((item) => {
        statusPending.current = null;
        setStatusUnknown(false);
        setAccount(item);
        accountRef.current = item;
      })
      .catch((caught: ApiError) => applyAccountWriteError(caught, statusPending, setStatusUnknown, setError))
      .finally(() => setBusy(false));
  };

  if (!account) {
    return error ? <p className="error">{error}</p> : <p>Carregando…</p>;
  }
  const currentBalanceLabel = movements
    ? formatMinor(movements.currentBalanceMinor)
    : statementError
      ? "Indisponível"
      : "Carregando…";
  return (
    <article>
      <h1 id="page-title" tabIndex={-1}>
        {account.name}
      </h1>
      <p className="hint">Calculado a partir do saldo inicial e dos registros locais; não conciliado com o banco.</p>
      <dl className="facts">
        <div><dt>Empresa</dt><dd>{account.companyName}</dd></div>
        <div><dt>Moeda</dt><dd>Real</dd></div>
        <div><dt>Saldo gerencial atual</dt><dd>{currentBalanceLabel}</dd></div>
        <div><dt>Situação</dt><dd>{account.active ? "Ativa" : "Inativa"}</dd></div>
      </dl>
      {movements && Number(movements.currentBalanceMinor) < 0 ? <p className="hint">Saldo gerencial negativo. Isso não autoriza operação bancária.</p> : null}
      {canWriteAccounts() ? (
        <form
          className="account-manage inline"
          onSubmit={(event) => {
            event.preventDefault();
            if (renameUnknown) {
              return;
            }
            sendRename(null);
          }}
          onChange={() => onDirty(true)}
        >
          <label>
            Nome
            <input value={name} onChange={(event) => setName(event.target.value)} disabled={renameUnknown} />
          </label>
          <button type="submit" className="secondary" disabled={busy || renameUnknown}>Renomear</button>
          {renameUnknown ? (
            <button type="button" disabled={busy || !renamePending.current} onClick={() => sendRename(renamePending.current)}>
              Tentar novamente
            </button>
          ) : null}
          <button
            type="button"
            className="secondary"
            disabled={busy || statusUnknown}
            onClick={() => sendStatus(null)}
          >
            {account.active ? "Inativar" : "Reativar"}
          </button>
          {statusUnknown ? (
            <button type="button" disabled={busy || !statusPending.current} onClick={() => sendStatus(statusPending.current)}>
              Tentar novamente a situação
            </button>
          ) : null}
        </form>
      ) : null}
      <h2>Extrato gerencial</h2>
      <p className="period-line">
        Período: {from ? formatDateBr(from) : "…"} a {to ? formatDateBr(to) : "…"}
      </p>
      <button type="button" className="secondary" onClick={() => setFiltersOpen((open) => !open)}>
        {filtersOpen ? "Ocultar período" : from || to ? "Período (definido)" : "Período"}
      </button>
      {filtersOpen || typeof window === "undefined" || window.innerWidth > 1023 ? (
        <div className="filters">
          <label>
            De
            <input type="date" value={from} onChange={(event) => { setFrom(event.target.value); setPage(0); }} />
          </label>
          <label>
            Até
            <input type="date" value={to} onChange={(event) => { setTo(event.target.value); setPage(0); }} />
          </label>
        </div>
      ) : null}
      {movements ? (
        <>
          <div className="statement-summary">
            <div>
              <span>Saldo anterior</span>
              <strong>{formatMinor(movements.previousBalanceMinor)}</strong>
            </div>
            <div>
              <span>Saldo final do período</span>
              <strong>{formatMinor(movements.periodEndBalanceMinor)}</strong>
            </div>
            <div>
              <span>Saldo atual</span>
              <strong>{formatMinor(movements.currentBalanceMinor)}</strong>
            </div>
          </div>
          <table className="desktop-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Tipo</th>
                <th className="num">Entrada</th>
                <th className="num">Saída</th>
                <th className="num">Saldo após</th>
              </tr>
            </thead>
            <tbody>
              {(movements.items ?? []).map((row) => (
                <tr key={row.id}>
                  <td>{formatDateBr(row.effectiveDate)}</td>
                  <td>
                    {row.description}
                    {row.settlementId ? (
                      <>
                        {" "}
                        <a
                          href={`/settlements/${row.settlementId}`}
                          onClick={(event) => {
                            event.preventDefault();
                            navigate(`/settlements/${row.settlementId}`);
                          }}
                        >
                          Ver registro
                        </a>
                      </>
                    ) : null}
                  </td>
                  <td>{formatMovementKind(row.kind)}</td>
                  <td className="num">{Number(row.inflowMinor) ? formatMinor(row.inflowMinor) : "—"}</td>
                  <td className="num">{Number(row.outflowMinor) ? formatMinor(row.outflowMinor) : "—"}</td>
                  <td className="num">{formatMinor(row.balanceAfterMinor)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards">
            {(movements.items ?? []).map((row) => (
              <li key={row.id} className="movement-card">
                <p>{formatDateBr(row.effectiveDate)} · {formatMovementKind(row.kind)}</p>
                <p>{row.description}</p>
                <MovementFlowLines row={row} />
                <p>Saldo após: {formatMinor(row.balanceAfterMinor)}</p>
                {row.settlementId ? (
                  <a
                    href={`/settlements/${row.settlementId}`}
                    onClick={(event) => {
                      event.preventDefault();
                      navigate(`/settlements/${row.settlementId}`);
                    }}
                  >
                    Ver registro
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
          <p className="pager">
            <button type="button" className="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Anterior</button>
            <button type="button" className="secondary" disabled={(page + 1) * movements.size >= movements.totalItems} onClick={() => setPage(page + 1)}>Próximo</button>
          </p>
        </>
      ) : statementError ? (
        <p className="error" role="alert">{statementError}</p>
      ) : (
        <p>Carregando extrato…</p>
      )}
      {error ? <p className="error" role="alert">{error}</p> : null}
    </article>
  );
}

function MovementFlowLines({ row }: { row: MovementPage["items"][number] }) {
  const openingMinor = Number(row.outflowMinor) > 0 ? `-${row.outflowMinor}` : row.inflowMinor || "0";
  if (row.kind === "OPENING") {
    return <p>Abertura: {formatMinor(openingMinor)}</p>;
  }
  return (
    <>
      {row.kind === "REVERSAL" ? <p>Estorno do registro</p> : null}
      {Number(row.inflowMinor) > 0 ? <p>Entrada: {formatMinor(row.inflowMinor)}</p> : <p>Saída: {formatMinor(row.outflowMinor || "0")}</p>}
    </>
  );
}

function AccountCreateDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (account: FinancialAccount) => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("BANK");
  const [openedOn, setOpenedOn] = useState("");
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const pending = useRef<PendingWrite | null>(null);

  const sendCreate = (existing?: PendingWrite | null) => {
    const parsed = parseSignedBrlInput(opening);
    if (!existing && (parsed.error || parsed.minor == null || !name.trim() || !openedOn)) {
      setError(parsed.error ?? "Informe o saldo inicial.");
      return;
    }
    setBusy(true);
    setError("");
    pending.current = freezeWrite(
      `/api/v1/financial-accounts?${companyQuery()}`,
      "POST",
      { name, type, openedOn, openingBalanceMinor: parsed.minor },
      existing,
    );
    void sendPending<FinancialAccount>(pending.current)
      .then((account) => {
        pending.current = null;
        setUnknownResult(false);
        onCreated(account);
      })
      .catch((caught: ApiError) => applyAccountWriteError(caught, pending, setUnknownResult, setError))
      .finally(() => setBusy(false));
  };

  return (
    <Modal title="Criar conta financeira" onClose={onClose}>
      <p className="hint">Informe o saldo no início desse dia. As movimentações registradas a partir dele atualizarão o saldo gerencial.</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (unknownResult) {
            return;
          }
          sendCreate(null);
        }}
      >
        <label>Nome<input value={name} onChange={(event) => setName(event.target.value)} required disabled={unknownResult} /></label>
        <label>
          Tipo
          <select value={type} onChange={(event) => setType(event.target.value)} disabled={unknownResult}>
            <option value="BANK">Banco</option>
            <option value="CASH">Caixa físico</option>
            <option value="OTHER">Outra</option>
          </select>
        </label>
        <label>Início do controle<input type="date" value={openedOn} onChange={(event) => setOpenedOn(event.target.value)} required disabled={unknownResult} /></label>
        <label>Saldo inicial<input value={opening} onChange={(event) => setOpening(event.target.value)} required disabled={unknownResult} /></label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="actions">
          <button type="button" className="secondary" onClick={onClose}>Voltar</button>
          <button type="submit" disabled={busy || unknownResult}>Criar conta</button>
          {unknownResult ? (
            <button type="button" disabled={busy || !pending.current} onClick={() => sendCreate(pending.current)}>
              Tentar novamente
            </button>
          ) : null}
        </div>
      </form>
    </Modal>
  );
}

function SearchableSelect({
  label,
  value,
  onChange,
  options,
  emptyLabel,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: CatalogItem[];
  emptyLabel: string;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const filtered = options.filter((item) => {
    const hay = `${item.name} ${item.code}`.toLowerCase();
    return hay.includes(query.trim().toLowerCase());
  });
  return (
    <label className="searchable">
      {label}
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Buscar na lista"
        disabled={disabled}
        aria-label={`Buscar ${label}`}
      />
      <select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
        <option value="">{emptyLabel}</option>
        {filtered.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
            {item.active === false ? " (inativa)" : ""}
          </option>
        ))}
        {value && !filtered.some((item) => item.id === value)
          ? options
              .filter((item) => item.id === value)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))
          : null}
      </select>
    </label>
  );
}

