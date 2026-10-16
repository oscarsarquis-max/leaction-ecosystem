import { useEffect, useState } from "react";
import { companyQuery, request, sendPending, freezeWrite } from "./api";
import { formatMinor } from "./money";

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
  const [narrow, setNarrow] = useState(window.matchMedia("(max-width: 1099px)").matches);

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
  }, []);

  useEffect(() => {
    if (!accountId) {
      return;
    }
    setQueue(null);
    void request<Queue>(`/api/v1/reconciliation?${companyQuery(`accountId=${accountId}&situation=${situation}&page=${page}&size=8`)}`)
      .then(setQueue)
      .catch(() => setError("Não foi possível consultar a conciliação."));
  }, [accountId, situation, page]);

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
      assignment: initiativeId ? "SINGLE" : "UNASSIGNED",
      initiativeId: initiativeId || null,
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
                    <button key={item.lineId} type="button" className="statement-card" onClick={() => open(item.lineId)}>
                      <strong>{item.description || "Sem descrição"}</strong>
                      <span>{money(item.netMinor)}</span>
                      <span>{SITUATION[item.situation]}</span>
                    </button>
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
          <label>Iniciativa<select value={initiativeId} onChange={(event) => setInitiativeId(event.target.value)}><option value="">Não atribuída</option>{initiatives.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => classify(true)}>Ver o efeito</button>
            <button type="button" disabled={busy} onClick={() => classify(false)}>Confirmar classificação</button>
          </div>
          {detail ? <Detail detail={detail} onChanged={() => accountId && open(String(detail.lineId))} /> : <p className="pv-muted">Selecione um movimento para ver bruto, tarifa, líquido e os candidatos.</p>}
        </aside>
      </div>
    </article>
  );
}

function Detail({ detail, onChanged }: { detail: Record<string, unknown>; onChanged: () => void }) {
  const [basis, setBasis] = useState("GROSS");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const suggestions = (detail.suggestions as { kind: string; reason: string; titleId?: string; strength: string }[] | undefined) ?? [];
  const shares = (detail.shares as { name: string; amountMinor: number }[] | undefined) ?? [];
  const confirmReference = (titleId: string) => {
    const minor = Number(amount.replace(/\D/g, ""));
    if (!minor) {
      setError("Informe o valor da referência em centavos, como 9000 para R$ 90,00.");
      return;
    }
    const pending = freezeWrite(`/api/v1/reconciliation/references?${companyQuery()}`, "POST", {
      lineId: detail.lineId,
      targetKind: "TITLE",
      titleId,
      comparedBasis: basis,
      allocatedMinor: minor,
    });
    void sendPending(pending).then(() => onChanged()).catch((caught: { message?: string }) => setError(caught.message || "Não foi possível relacionar."));
  };
  return (
    <div>
      <h2>Movimento</h2>
      <p>{String(detail.eventKind || "")} · {String(detail.direction || "")}. A natureza da origem permanece.</p>
      <p>Bruto {money(detail.grossMinor as number | null)} · Tarifa {money(detail.feeMinor as number | null)} · Líquido {money(detail.netMinor as number | null)}</p>
      <p>{String(detail.dateLabel || "Data de aprovação")}: {String(detail.effectiveOn || "sem data confiável")}</p>
      {shares.length > 0 ? (
        <ul>{shares.map((share) => <li key={share.name}>{share.name}: {money(share.amountMinor)}</li>)}</ul>
      ) : <p>Não atribuída até haver uma decisão.</p>}
      {error ? <p className="error" role="alert">{error}</p> : null}
      <h3>Candidatos</h3>
      {suggestions.length === 0 ? <p>Nenhuma sugestão. Data e valor iguais não confirmam sozinhos.</p> : suggestions.map((item, index) => (
        <p key={index}>
          {item.strength === "WEAK" ? "Sugestão fraca. " : ""}{item.reason}
          {item.titleId ? <button type="button" className="secondary" onClick={() => confirmReference(item.titleId!)}>Confirmar só a referência</button> : null}
        </p>
      ))}
      <label>Base comparada
        <select value={basis} onChange={(event) => setBasis(event.target.value)}>
          <option value="GROSS">Bruto</option>
          <option value="NET">Líquido</option>
          <option value="CONFIRMED_PAID">Pago confirmado</option>
        </select>
      </label>
      <label>Valor em centavos<input value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
      <p className="pv-muted">Confirmar a referência não baixa o título e não marca o livro como conciliado.</p>
    </div>
  );
}
