import { useEffect, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatMinor } from "./money";
import { getSession } from "./session";

type MoneyPart = { state: string; minor: number | null };
type Share = { label: string; minor: number };
type Week = { start: string; label: string; minor: number; lowest: boolean };
type Attention = { tag: string; text: string; href: string; action: string };

export type Overview = {
  title: string;
  rangeLabel: string;
  sales: MoneyPart;
  fees: MoneyPart;
  production: MoneyPart;
  expenses: MoneyPart;
  leftover: { complete: boolean; state: string; minor: number | null; missing: string[] };
  methods: Share[];
  categories: Share[];
  cash: { state: string; positionMinor: number | null; accountName: string | null; weeks: Week[]; lowest: Week | null };
  attention: Attention[];
  statementLines: number;
  reconciliationPending: number;
  lastPaySyncAt: string | null;
  lastStatementAt: string | null;
  accountName: string | null;
};

function gap(state: string): string {
  return state === "NAO_CONECTADO" ? "Não conectado" : "Não apurado";
}

function shownMoney(minor: number, cost = false): string {
  if (cost && minor > 0) {
    return `− ${formatMinor(String(minor))}`;
  }
  return formatMinor(String(minor));
}

function valueOf(part: MoneyPart, cost = false): string {
  if (part.state === "APURADO" && part.minor != null) {
    return shownMoney(part.minor, cost);
  }
  return gap(part.state);
}

function percent(part: number, total: number): string | null {
  if (total <= 0) {
    return null;
  }
  return `${Math.round((part / total) * 100)}%`;
}

function ago(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const elapsed = Date.now() - new Date(value).getTime();
  if (Number.isNaN(elapsed)) {
    return null;
  }
  if (elapsed < 60_000) {
    return "há instantes";
  }
  const minutes = Math.round(elapsed / 60_000);
  if (minutes < 60) {
    return `há ${minutes} min`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 48) {
    return `há ${hours} h`;
  }
  return `há ${Math.round(hours / 24)} dias`;
}

function freshness(data: Overview): string {
  const pay = ago(data.lastPaySyncAt);
  const statement = ago(data.lastStatementAt);
  if (pay && statement) {
    return `atualizado sozinho ${pay} com o ActionHub Pay e ${statement} com o extrato`;
  }
  if (pay) {
    return `atualizado sozinho ${pay} com o ActionHub Pay`;
  }
  if (statement) {
    return `extrato atualizado ${statement}`;
  }
  return "ainda sem sincronização do ActionHub Pay nem extrato importado";
}

function readings(data: Overview): [string, string] {
  let first: string;
  if (data.sales.state === "APURADO" && data.sales.minor != null) {
    first = `Entraram ${shownMoney(data.sales.minor)} em vendas.`;
    if (data.leftover.complete && data.leftover.minor != null && data.sales.minor > 0) {
      const share = Math.round((data.leftover.minor / data.sales.minor) * 100);
      first += ` Depois de taxas, custos de produção e despesas, sobraram ${shownMoney(data.leftover.minor)} — ${share}% de cada real vendido.`;
    } else if (data.leftover.minor != null) {
      first += ` O que já está apurado soma ${shownMoney(data.leftover.minor)}. Ainda falta: ${data.leftover.missing.join(", ")}.`;
    } else {
      first += ` Ainda não dá para dizer o que sobrou. Falta: ${data.leftover.missing.join(", ")}.`;
    }
  } else if (data.sales.state === "NAO_CONECTADO") {
    first = "As vendas ainda não estão conectadas.";
  } else {
    first = "As vendas deste período ainda não foram apuradas.";
  }
  if (data.cash.state === "APURADO" && data.cash.lowest) {
    const ending = data.cash.lowest.minor >= 0 ? "Ainda fica positivo." : "Fica negativo.";
    return [first, `O caixa fica mais apertado na semana de ${data.cash.lowest.label}, com cerca de ${shownMoney(data.cash.lowest.minor)}. ${ending}`];
  }
  if (data.cash.state === "NAO_CONECTADO") {
    return [first, "O caixa ainda não está conectado."];
  }
  return [first, "O caixa deste período ainda não foi apurado."];
}

function shortWeek(minor: number): string {
  const reais = Math.abs(minor) / 100;
  const sign = minor < 0 ? "−" : "";
  if (reais >= 1000) {
    return `${sign}${reais / 1000 >= 10 ? Math.round(reais / 1000) : (reais / 1000).toFixed(1).replace(".", ",")} mil`;
  }
  return shownMoney(minor);
}

export function HomePage({ onNavigate }: { onNavigate: (to: string) => void }) {
  const companyId = getSession()?.companyId ?? "";
  const [period, setPeriod] = useState("month");
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void request<Overview>(`/api/v1/overview?${companyQuery(`period=${period}`)}`)
      .then((body) => {
        if (active) {
          setData(body);
        }
      })
      .catch((caught) => {
        if (active) {
          setData(null);
          setError((caught as ApiError).message || "Não foi possível ler o mês.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [companyId, period]);

  const go = (to: string) => onNavigate(to);

  return (
    <div className="owner-home">
      <div className="owner-head">
        <div>
          <h1 id="page-title" tabIndex={-1}>{data?.title ?? "Início"}</h1>
          <p className="owner-range">{data ? `${data.rangeLabel} · ${freshness(data)}` : "A leitura da empresa desta sessão."}</p>
        </div>
        <div role="group" aria-label="Período" className="owner-periods">
          {[
            ["week", "Semana"],
            ["month", "Mês"],
            ["year", "Ano"],
          ].map(([value, label]) => (
            <button key={value} type="button" aria-pressed={period === value} onClick={() => setPeriod(value)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {loading ? <p className="hint">Carregando a leitura…</p> : null}
      {error ? <p className="error error-box" role="alert">{error}</p> : null}
      {data ? <OwnerReading data={data} onNavigate={go} /> : null}
    </div>
  );
}

function OwnerReading({ data, onNavigate }: { data: Overview; onNavigate: (to: string) => void }) {
  const [lead, cashLine] = readings(data);
  const salesMinor = data.sales.state === "APURADO" ? data.sales.minor : null;
  const cards = [
    { label: "Vendas", value: valueOf(data.sales), note: data.sales.state === "APURADO" ? "ActionHub Pay" : gap(data.sales.state), tone: "" },
    { label: "Taxas", value: valueOf(data.fees, true), note: noteOf(data.fees, salesMinor, "Sem extrato neste período"), tone: "" },
    { label: "Custos de produção", value: valueOf(data.production, true), note: "Ainda não ligado", tone: "" },
    { label: "Despesas", value: valueOf(data.expenses, true), note: data.expenses.state === "APURADO" ? categoryNote(data.categories) : "Sem baixas neste período", tone: "" },
    {
      label: "Sobrou",
      value: data.leftover.minor == null ? "Não apurado" : shownMoney(data.leftover.minor),
      note: data.leftover.complete && salesMinor ? `${percent(data.leftover.minor ?? 0, salesMinor)} das vendas` : `Falta: ${data.leftover.missing.join(", ")}`,
      tone: data.leftover.complete ? "complete" : "",
    },
  ];
  const outflows = outflowRows(data);
  const bank = bankCopy(data);
  const weeks = data.cash.weeks ?? [];
  const peak = Math.max(...weeks.map((week) => Math.abs(week.minor)), 1);

  return (
    <>
      <section className="owner-reading" aria-labelledby="leitura">
        <h2 id="leitura">Leitura do mês</h2>
        <p className="owner-lead">{lead}</p>
        <p>{cashLine}</p>
      </section>
      <section className="owner-kpis" aria-label="Resumo do resultado">
        {cards.map((card) => (
          <div key={card.label} className={card.tone ? `owner-kpi ${card.tone}` : "owner-kpi"}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <small>{card.note}</small>
          </div>
        ))}
      </section>
      <div className="owner-split">
        <section className="owner-panel" aria-labelledby="caixa">
          <div className="owner-panel-head">
            <h2 id="caixa">Caixa nas próximas 8 semanas</h2>
            <button type="button" className="btn-link" onClick={() => onNavigate("/financial-accounts/agenda")}>Ver o fluxo completo</button>
          </div>
          <p className="owner-muted">
            {data.cash.state === "APURADO" && data.cash.positionMinor != null
              ? <>Hoje na conta {data.accountName ?? data.cash.accountName ?? "apurada"}: <strong>{shownMoney(data.cash.positionMinor)}</strong>.</>
              : gap(data.cash.state)}
          </p>
          {weeks.length === 8 ? (
            <>
              <div className="owner-bars" role="img" aria-label={cashLine}>
                {weeks.map((week) => (
                  <div key={week.start} className="owner-bar-col">
                    <span className={week.lowest ? "is-low" : ""}>{shortWeek(week.minor)}</span>
                    <div className="owner-bar-track">
                      <div className={week.lowest ? "owner-bar is-low" : "owner-bar"} style={{ height: `${Math.max(8, Math.round((Math.abs(week.minor) / peak) * 100))}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="owner-bar-dates">
                {weeks.map((week) => <span key={week.start} className={week.lowest ? "is-low" : ""}>{week.label}</span>)}
              </div>
              <div className="owner-legend">
                <span><i className="swatch" />Saldo previsto</span>
                <span><i className="swatch is-low" />Menor ponto</span>
              </div>
            </>
          ) : null}
        </section>
        <section className="owner-panel" aria-labelledby="atencao">
          <h2 id="atencao">Pede sua atenção</h2>
          {data.attention.length === 0 ? <p className="owner-muted">Nada urgente nesta leitura.</p> : null}
          {data.attention.map((item) => (
            <div key={`${item.tag}-${item.href}`} className="owner-alert">
              <span className={item.tag.startsWith("Vence") || item.tag === "Vencido" ? "owner-tag warn" : "owner-tag"}>{item.tag}</span>
              <p>{item.text}</p>
              <button type="button" onClick={() => onNavigate(item.href)}>{item.action}</button>
            </div>
          ))}
        </section>
      </div>
      <div className="owner-flows">
        <section className="owner-panel" aria-labelledby="entradas">
          <h2 id="entradas">De onde veio o dinheiro</h2>
          {data.sales.state === "APURADO" && data.methods.length > 0 ? data.methods.map((row) => (
            <ShareRow key={row.label} label={row.label} value={shownMoney(row.minor)} share={salesMinor ? percent(row.minor, salesMinor) : null} tone="in" total={salesMinor ?? 0} minor={row.minor} />
          )) : <p className="owner-muted">{gap(data.sales.state)}</p>}
        </section>
        <section className="owner-panel" aria-labelledby="saidas">
          <h2 id="saidas">Para onde foi</h2>
          {outflows.length > 0 ? outflows.map((row) => (
            <ShareRow key={row.label} label={row.label} value={shownMoney(row.minor, true)} share={percent(row.minor, outflowTotal(outflows))} tone="out" total={outflowTotal(outflows)} minor={row.minor} />
          )) : <p className="owner-muted">{data.expenses.state === "APURADO" || data.fees.state === "APURADO" ? "Não apurado" : gap(data.expenses.state === "NAO_CONECTADO" ? "NAO_CONECTADO" : "NAO_APURADO")}</p>}
        </section>
      </div>
      <section className="owner-bank" aria-labelledby="banco">
        <div>
          <h2 id="banco">{bank.title}</h2>
          <p>{bank.text}</p>
        </div>
        {bank.action ? <button type="button" onClick={() => onNavigate("/financial-accounts/reconciliation")}>{bank.action}</button> : null}
      </section>
    </>
  );
}

function noteOf(part: MoneyPart, sales: number | null, emptyNote: string): string {
  if (part.state === "APURADO" && part.minor != null && sales) {
    return `${percent(part.minor, sales)} das vendas`;
  }
  if (part.state === "NAO_CONECTADO") {
    return "Não conectado";
  }
  return emptyNote;
}

function categoryNote(rows: Share[]): string {
  const names = rows.slice(0, 3).map((row) => row.label);
  if (names.length === 0) {
    return "Baixas do período";
  }
  if (names.length === 1) {
    return names[0];
  }
  return `${names.slice(0, -1).join(", ")} e ${names[names.length - 1]}`;
}

function outflowRows(data: Overview): Share[] {
  const rows = data.expenses.state === "APURADO" ? [...data.categories] : [];
  if (data.fees.state === "APURADO" && data.fees.minor != null && data.fees.minor > 0) {
    rows.push({ label: "Taxas do Mercado Pago", minor: data.fees.minor });
  }
  return rows;
}

function outflowTotal(rows: Share[]): number {
  return rows.reduce((sum, row) => sum + row.minor, 0);
}

function bankCopy(data: Overview): { title: string; text: string; action: string | null } {
  const name = data.accountName || data.cash.accountName;
  if (!data.statementLines) {
    return {
      title: name || "Conta",
      text: data.cash.state === "NAO_CONECTADO" ? "A conta ainda não está conectada." : "O extrato ainda não foi apurado.",
      action: null,
    };
  }
  const pending = data.reconciliationPending;
  const done = Math.max(0, data.statementLines - pending);
  const title = name ? `${name} conferida` : "Conta conferida";
  const text = pending > 0
    ? `${done} de ${data.statementLines} lançamentos conferidos sozinhos com as vendas e os pagamentos. Faltam ${pending} para você decidir.`
    : `${done} de ${data.statementLines} lançamentos conferidos sozinhos com as vendas e os pagamentos.`;
  return { title, text, action: pending > 0 ? `Revisar ${pending} lançamentos` : "Ver a conciliação" };
}

function ShareRow({ label, value, share, tone, total, minor }: { label: string; value: string; share: string | null; tone: "in" | "out"; total: number; minor: number }) {
  const width = total > 0 ? Math.max(4, Math.round((minor / total) * 100)) : 0;
  return (
    <div className="owner-share">
      <div><span>{share ? `${label}` : label}</span><span>{value}{share ? <em> · {share}</em> : null}</span></div>
      <div className={`owner-share-track ${tone}`}><div style={{ width: `${width}%` }} /></div>
    </div>
  );
}
