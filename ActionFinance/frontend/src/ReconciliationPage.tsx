import { useEffect, useState } from "react";
import { companyQuery, request, sendPending, freezeWrite } from "./api";
import { formatMinor, parseBrlInput } from "./money";

type Coverage = {
  eligibleCount: number;
  documentaryCount: number;
  classifiedCount: number;
  inBaseMinor: number;
  outBaseMinor: number;
  inBookMinor: number;
  outBookMinor: number;
  inPendingMinor: number;
  outPendingMinor: number;
  note: string;
};

type Item = {
  lineId: string;
  description: string | null;
  externalReference: string | null;
  effectiveOn: string | null;
  dateLabel: string;
  direction: string;
  eventKind: string;
  grossMinor: number | null;
  feeMinor: number | null;
  netMinor: number | null;
  category: string;
  initiative: string;
  situation: string;
  version: number;
  eligible: boolean;
  reviewRequired: boolean;
};

type Queue = { page: number; size: number; total: number; items: Item[]; coverage: Coverage };

const TABS = [
  ["", "Todas"],
  ["SEM_CORRESPONDENCIA", "Sem correspondência"],
  ["PARCIAL", "Parcial"],
  ["CONCILIADO", "Conciliado com o livro"],
  ["DIVERGENCIA", "Diferença"],
  ["REFERENCIA", "Só referência"],
] as const;

const SITUATION: Record<string, string> = {
  SEM_CORRESPONDENCIA: "Sem correspondência",
  PARCIAL: "Conciliação parcial",
  CONCILIADO: "Conciliado com o livro",
  DIVERGENCIA: "Diferença em aberto",
  REFERENCIA: "Referência confirmada",
  FORA: "Fora da soma elegível",
};

function money(value: number | null | undefined) {
  if (value == null) {
    return "—";
  }
  return formatMinor(String(value));
}

export function ReconciliationPage() {
  const [accounts, setAccounts] = useState<{ id: string; name: string }[]>([]);
  const [accountId, setAccountId] = useState("");
  const [situation, setSituation] = useState(() => {
    const value = new URLSearchParams(window.location.search).get("situacao") ?? "";
    return ["SEM_CORRESPONDENCIA", "PARCIAL", "CONCILIADO", "DIVERGENCIA", "REFERENCIA"].includes(value) ? value : "";
  });
  const [page, setPage] = useState(0);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [initiatives, setInitiatives] = useState<{ id: string; name: string; code: string }[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [initiativeId, setInitiativeId] = useState("");
  const [assignment, setAssignment] = useState("UNASSIGNED");
  const [ruleVersionId, setRuleVersionId] = useState("");
  const [rules, setRules] = useState<{ id: string; name: string; versions: { id: string; validFrom: string; shares?: { code: string; basisPoints: number }[] }[] }[]>([]);
  const [narrow, setNarrow] = useState(window.matchMedia("(max-width: 1099px)").matches);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 1099px)");
    const onChange = () => setNarrow(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    void request<{ id: string; name: string }[]>(`/api/v1/financial-accounts?${companyQuery()}`).then((rows) => {
      setAccounts(rows);
      setAccountId((current) => current || rows[0]?.id || "");
    });
    void request<{ id: string; name: string }[]>(`/api/v1/catalogs/categories?${companyQuery()}`).then(setCategories).catch(() => setCategories([]));
    void request<{ id: string; name: string; code: string }[]>(`/api/v1/catalogs/initiatives?${companyQuery()}`).then(setInitiatives).catch(() => setInitiatives([]));
    void request<typeof rules>(`/api/v1/catalogs/allocation-rules?${companyQuery()}`).then(setRules).catch(() => setRules([]));
  }, []);

  useEffect(() => {
    if (!accountId) {
      return;
    }
    setQueue(null);
    void request<Queue>(`/api/v1/reconciliation?${companyQuery(`accountId=${accountId}&situation=${situation}&page=${page}&size=8`)}`)
      .then(setQueue)
      .catch(() => setError("Não foi possível consultar a conciliação."));
  }, [accountId, situation, page, generation]);

  const open = (lineId: string) => {
    setDetail(null);
    void request<Record<string, unknown>>(`/api/v1/reconciliation/lines/${lineId}?${companyQuery()}`)
      .then(setDetail)
      .catch(() => setError("Não foi possível abrir o movimento."));
  };

  const versions = () => {
    const map: Record<string, number> = {};
    for (const item of queue?.items ?? []) {
      if (selected.includes(item.lineId)) {
        map[item.lineId] = item.version;
      }
    }
    return map;
  };

  const classify = (preview: boolean) => {
    if (selected.length === 0) {
      setError("Selecione os movimentos antes de classificar.");
      return;
    }
    setBusy(true);
    setError("");
    const pending = freezeWrite(`/api/v1/reconciliation/classifications?${companyQuery()}`, "POST", {
      preview,
      lineIds: selected,
      versions: versions(),
      categoryId: categoryId || null,
      clearCategory: false,
      assignment,
      initiativeId: assignment === "SINGLE" ? initiativeId || null : null,
      ruleVersionId: assignment === "ALLOCATED" ? ruleVersionId || null : null,
      reason: preview ? "Prévia" : "Classificação confirmada pelo operador.",
    });
    void sendPending<Record<string, unknown>>(pending)
      .then((result) => {
        if (preview) {
          setNotice(`${result.applicable ?? 0} de ${result.selected ?? 0} podem receber esta classificação.`);
          return;
        }
        setNotice("Classificação gravada. O extrato e o saldo não foram alterados.");
        setPage(0);
        setSelected([]);
      })
      .catch((caught: { message?: string }) => setError(caught.message || "Não foi possível classificar."))
      .finally(() => setBusy(false));
  };

  const coverage = queue?.coverage;
  const showList = !narrow || !detail;

  return (
    <article className="fluxo">
      <h1 id="page-title" tabIndex={-1}>Conciliação</h1>
      <p className="pv-muted">Classificar e relacionar não cria título, baixa nem movimento. Uma sugestão só vale depois da sua confirmação.</p>
      <div className="pv-context">
        <label>
          Conta
          <select value={accountId} onChange={(event) => { setAccountId(event.target.value); setPage(0); setDetail(null); }}>
            {accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
          </select>
        </label>
      </div>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p>{notice}</p> : null}
      <div className="pv-layout">
        {showList ? (
          <section className="pv-card">
            <div className="fx-tabs" role="tablist" aria-label="Situação da conferência">
              {TABS.map(([value, label]) => (
                <button key={value} type="button" role="tab" className="fx-tab" aria-selected={situation === value} onClick={() => { setSituation(value); setPage(0); }}>
                  {label}
                </button>
              ))}
            </div>
            <p className="fx-caption">Conciliado é só o que confere com o livro. Referência confirmada explica a cobrança e não entra nessa soma.</p>
            {!queue ? <p>Carregando…</p> : queue.total === 0 ? (
              <p><strong>Ainda não há movimentos neste recorte.</strong> Importe e confira um relatório em Extratos para classificar.</p>
            ) : (
              <>
                <table className="desktop-table">
                  <thead>
                    <tr>
                      <th>Seleção</th>
                      <th>Data</th>
                      <th>Descrição</th>
                      <th>Situação</th>
                      <th className="num">Líquido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue.items.map((item) => (
                      <tr key={item.lineId}>
                        <td>
                          <input type="checkbox" aria-label={`Selecionar ${item.description || "movimento"}`} checked={selected.includes(item.lineId)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.lineId] : current.filter((id) => id !== item.lineId))} />
                        </td>
                        <td>{item.effectiveOn ? item.effectiveOn.split("-").reverse().join("/") : "Sem data"}<span className="hint">{item.dateLabel}</span></td>
                        <td>
                          <button type="button" className="link" onClick={() => open(item.lineId)}>{item.description || item.externalReference || "Sem descrição"}</button>
                          <span className="hint">{item.category} · {item.initiative}{item.reviewRequired ? " · revisar" : ""}</span>
                        </td>
                        <td>{SITUATION[item.situation] || item.situation}</td>
                        <td className="num">{money(item.netMinor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="statement-cards">
                  {queue.items.map((item) => (
                    <div key={item.lineId} className="statement-card">
                      <label>
                        <input type="checkbox" aria-label={`Selecionar ${item.description || "movimento"}`} checked={selected.includes(item.lineId)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.lineId] : current.filter((id) => id !== item.lineId))} />
                        Selecionar
                      </label>
                      <button type="button" className="link" onClick={() => open(item.lineId)}>
                        <strong>{item.description || "Sem descrição"}</strong>
                      </button>
                      <span>{money(item.netMinor)}</span>
                      <span>{SITUATION[item.situation]}</span>
                    </div>
                  ))}
                </div>
                <div className="pager">
                  <button type="button" className="secondary" disabled={page === 0} onClick={() => setPage((value) => value - 1)}>Anterior</button>
                  <span>Página {page + 1} · {queue.total} movimentos</span>
                  <button type="button" className="secondary" disabled={(page + 1) * 8 >= queue.total} onClick={() => setPage((value) => value + 1)}>Próximo</button>
                </div>
              </>
            )}
          </section>
        ) : null}
        <aside className={`pv-card ${detail ? "pv-detail" : ""}`}>
          {detail && narrow ? <button type="button" className="secondary" onClick={() => setDetail(null)}>Voltar à fila</button> : null}
          {coverage ? (
            <>
              <h2>Cobertura</h2>
              <p>{coverage.note}</p>
              <p>Entradas elegíveis {money(coverage.inBaseMinor)}. No livro {money(coverage.inBookMinor)}. Pendente {money(coverage.inPendingMinor)}.</p>
              <p>Saídas elegíveis {money(coverage.outBaseMinor)}. No livro {money(coverage.outBookMinor)}. Pendente {money(coverage.outPendingMinor)}.</p>
              <p>{coverage.classifiedCount} de {coverage.eligibleCount} elegíveis têm categoria. {coverage.documentaryCount} ficam fora da soma, só como documento.</p>
              <button type="button" className="secondary" onClick={() => setSituation("SEM_CORRESPONDENCIA")}>Ver sem correspondência</button>
            </>
          ) : null}
          <h2>Classificar a seleção</h2>
          <p>{selected.length} nesta página. A gravação usa a versão de cada um; se outro operador mudou, nada é gravado pela metade.</p>
          <label>Categoria<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">Sem categoria</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Atribuição
            <select value={assignment} onChange={(event) => setAssignment(event.target.value)}>
              <option value="UNASSIGNED">Não atribuída</option>
              <option value="SINGLE">Uma iniciativa</option>
              <option value="ALLOCATED">Regra de rateio</option>
            </select>
          </label>
          {assignment === "SINGLE" ? (
            <label>Iniciativa<select value={initiativeId} onChange={(event) => setInitiativeId(event.target.value)}><option value="">Escolha</option>{initiatives.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          ) : null}
          {assignment === "ALLOCATED" ? (
            <label>Regra
              <select value={ruleVersionId} onChange={(event) => setRuleVersionId(event.target.value)}>
                <option value="">Escolha</option>
                {rules.map((rule) => {
                  const version = rule.versions[0];
                  const parts = (version?.shares ?? []).map((share) => `${share.code} ${(share.basisPoints / 100).toLocaleString("pt-BR")}%`).join(" e ");
                  return <option key={rule.id} value={version?.id || ""}>{rule.name}{parts ? ` · ${parts}` : ""}</option>;
                })}
              </select>
            </label>
          ) : null}
          <div className="actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => classify(true)}>Ver o efeito</button>
            <button type="button" disabled={busy} onClick={() => classify(false)}>Confirmar classificação</button>
          </div>
          {detail ? <Detail detail={detail} accountId={accountId} onChanged={() => { setGeneration((value) => value + 1); if (accountId) open(String(detail.lineId)); }} /> : <p className="pv-muted">Selecione um movimento para ver bruto, tarifa, líquido e os candidatos.</p>}
        </aside>
      </div>
    </article>
  );
}

const BOOK_STATUS: Record<string, string> = {
  ACTIVE: "Vigente",
  UNDONE: "Desfeita",
  INVALID: "Invalidada pela baixa estornada",
};

const HISTORY_ACTION: Record<string, string> = {
  CONFIRMED: "Confirmada",
  UNDONE: "Desfeita",
  INVALIDATED: "Invalidada",
};

function reais(raw: string): number | null {
  const parsed = parseBrlInput(raw);
  if (!parsed.minor) {
    return null;
  }
  return Number(parsed.minor);
}

function Detail({ detail, accountId, onChanged }: { detail: Record<string, unknown>; accountId: string; onChanged: () => void }) {
  const [basis, setBasis] = useState("GROSS");
  const [amount, setAmount] = useState("");
  const [query, setQuery] = useState("");
  const [foundTitles, setFoundTitles] = useState<{ id: string; description: string; status: string; amountMinor: number }[]>([]);
  const [foundMovements, setFoundMovements] = useState<{ id: string; description: string; signedMinor: number; effectiveDate: string }[]>([]);
  const [picked, setPicked] = useState<{ id: string; description: string; amount: string }[]>([]);
  const [undoReason, setUndoReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const suggestions = (detail.suggestions as { kind: string; reason: string; titleId?: string; strength: string }[] | undefined) ?? [];
  const shares = (detail.shares as { name: string; amountMinor: number; criterion?: string }[] | undefined) ?? [];
  const book = (detail.book as { id: string; allocatedMinor: number; sign: number; status: string; version: number }[] | undefined) ?? [];
  const decisions = (detail.decisions as { version: number; reason: string }[] | undefined) ?? [];
  const history = (detail.history as { action: string; reason: string; amountMinor: number | string }[] | undefined) ?? [];
  const net = Number(detail.netMinor ?? 0);
  const target = detail.direction === "OUT" ? -net : net;
  const signed = book.filter((row) => row.status === "ACTIVE").reduce((sum, row) => sum + row.sign * row.allocatedMinor, 0);
  const difference = target - signed;

  const search = () => {
    setError("");
    void request<{ titles: typeof foundTitles; movements: typeof foundMovements }>(`/api/v1/reconciliation/search?${companyQuery(`accountId=${accountId}&q=${encodeURIComponent(query)}`)}`)
      .then((result) => {
        setFoundTitles(result.titles ?? []);
        setFoundMovements(result.movements ?? []);
      })
      .catch(() => setError("Não foi possível buscar."));
  };

  const confirmReference = (titleId: string) => {
    const minor = reais(amount);
    if (!minor) {
      setError("Informe o valor comparado, como 90,00.");
      return;
    }
    const pending = freezeWrite(`/api/v1/reconciliation/references?${companyQuery()}`, "POST", {
      lineId: detail.lineId,
      targetKind: "TITLE",
      titleId,
      comparedBasis: basis,
      allocatedMinor: minor,
    });
    void sendPending(pending)
      .then(() => { setNotice("Referência confirmada. O título continua em aberto e o livro não foi conciliado."); onChanged(); })
      .catch((caught: { message?: string }) => setError(caught.message || "Não foi possível relacionar."));
  };

  const confirmBook = (allowPartial: boolean) => {
    if (picked.length === 0) {
      setError("Escolha ao menos um movimento do livro.");
      return;
    }
    const components = [];
    for (const item of picked) {
      const minor = reais(item.amount);
      if (!minor) {
        setError("Informe o valor de cada movimento, como 90,00 ou 5,00.");
        return;
      }
      components.push({ movementId: item.id, allocatedMinor: minor });
    }
    const pending = freezeWrite(`/api/v1/reconciliation/book?${companyQuery()}`, "POST", {
      lineId: detail.lineId,
      allowPartial,
      components,
    });
    void sendPending<{ equation?: string; fullyReconciled?: boolean }>(pending)
      .then((result) => {
        setNotice(result.fullyReconciled ? "Grupo conciliado com o livro. Nenhum movimento novo foi criado." : "Conciliação parcial gravada. A diferença continua visível.");
        setPicked([]);
        onChanged();
      })
      .catch((caught: { message?: string }) => setError(caught.message || "Não foi possível conciliar."));
  };

  const undo = (id: string, version: number) => {
    if (undoReason.trim().length < 3) {
      setError("Informe o motivo para desfazer.");
      return;
    }
    const pending = freezeWrite(`/api/v1/reconciliation/undo?${companyQuery()}`, "POST", {
      kind: "BOOK",
      id,
      version,
      reason: undoReason.trim(),
    });
    void sendPending(pending)
      .then(() => { setNotice("Conciliação desfeita. O movimento do livro foi liberado."); setUndoReason(""); onChanged(); })
      .catch((caught: { message?: string }) => setError(caught.message || "Não foi possível desfazer."));
  };

  return (
    <div>
      <h2>Movimento</h2>
      <p>{String(detail.description || "Sem descrição")}. A natureza da origem permanece.</p>
      <p>Bruto {money(detail.grossMinor as number | null)} · Tarifa {money(detail.feeMinor as number | null)} · Líquido {money(detail.netMinor as number | null)}</p>
      <p>{String(detail.dateLabel || "Data de aprovação")}: {String(detail.effectiveOn || "sem data confiável")}</p>
      {shares.length > 0 ? (
        <>
          <ul>{shares.map((share) => <li key={share.name}>{share.name}: {money(share.amountMinor)}</li>)}</ul>
          {shares[0]?.criterion ? <p className="pv-muted">{shares[0].criterion}</p> : null}
        </>
      ) : <p>Não atribuída até haver uma decisão.</p>}
      {decisions.length > 0 ? (
        <>
          <h3>Histórico da classificação</h3>
          <ul>{decisions.map((item) => <li key={`${item.version}-${item.reason}`}>Versão {item.version}. {item.reason}</li>)}</ul>
        </>
      ) : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p>{notice}</p> : null}
      <h3>Referência comercial</h3>
      <p className="pv-muted">Confirmar a referência não baixa o título e não marca o livro como conciliado.</p>
      {suggestions.map((item, index) => (
        <p key={index}>{item.strength === "WEAK" ? "Sugestão fraca. " : ""}{item.reason}</p>
      ))}
      <label>Buscar título ou movimento
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <button type="button" className="secondary" onClick={search}>Buscar</button>
      {foundTitles.map((title) => (
        <p key={title.id}>
          {title.description} · {title.status === "OPEN" ? "Em aberto" : title.status} · {money(title.amountMinor)}
          <button type="button" className="secondary" onClick={() => confirmReference(title.id)}>Confirmar só a referência</button>
        </p>
      ))}
      <label>Base comparada
        <select value={basis} onChange={(event) => setBasis(event.target.value)}>
          <option value="GROSS">Bruto</option>
          <option value="NET">Líquido</option>
          <option value="CONFIRMED_PAID">Pago confirmado</option>
        </select>
      </label>
      <label>Valor comparado<input value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="90,00" /></label>
      <h3>Livro</h3>
      <p>Líquido do extrato {money(net)}. Conferido {money(signed)}. Diferença {money(difference)}.</p>
      {difference !== 0 ? <p>A diferença permanece visível. Nenhum movimento foi criado para cobri-la.</p> : <p>A equação fecha o líquido. Isso não é saldo bancário.</p>}
      {book.length === 0 ? <p>Nenhuma conciliação com o livro.</p> : (
        <ul>
          {book.map((row) => (
            <li key={row.id}>
              {row.sign < 0 ? "Saída" : "Entrada"} {money(row.allocatedMinor)} · {BOOK_STATUS[row.status] || row.status}
              {row.status === "ACTIVE" ? <button type="button" className="secondary" onClick={() => undo(row.id, row.version)}>Desfazer</button> : null}
            </li>
          ))}
        </ul>
      )}
      {foundMovements.map((movement) => (
        <p key={movement.id}>
          {movement.description} · {money(movement.signedMinor)}
          <button type="button" className="secondary" onClick={() => setPicked((current) => current.some((item) => item.id === movement.id) ? current : [...current, { id: movement.id, description: movement.description, amount: formatMinor(String(Math.abs(movement.signedMinor))).replace("R$ ", "") }])}>Incluir no grupo</button>
        </p>
      ))}
      {picked.map((item) => (
        <label key={item.id}>{item.description}
          <input aria-label={`Valor de ${item.description}`} value={item.amount} onChange={(event) => setPicked((current) => current.map((row) => row.id === item.id ? { ...row, amount: event.target.value } : row))} />
        </label>
      ))}
      <div className="actions">
        <button type="button" className="secondary" onClick={() => confirmBook(true)}>Conciliar parte</button>
        <button type="button" onClick={() => confirmBook(false)}>Conciliar o grupo</button>
      </div>
      <label>Motivo para desfazer
        <input value={undoReason} onChange={(event) => setUndoReason(event.target.value)} />
      </label>
      {history.length > 0 ? (
        <>
          <h3>Histórico dos vínculos</h3>
          <ul>{history.map((item, index) => <li key={index}>{HISTORY_ACTION[item.action] || item.action}. {item.reason}{item.amountMinor === "" ? "" : ` · ${money(Number(item.amountMinor))}`}</li>)}</ul>
        </>
      ) : null}
    </div>
  );
}
