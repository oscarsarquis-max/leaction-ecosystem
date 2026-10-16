import { useEffect, useState } from "react";
import { companyQuery, freezeWrite, request, sendPending } from "./api";

type Initiative = { id: string; code: string; name: string; active: boolean; version: number };
type Share = { initiativeId: string; code: string; basisPoints: number };

export function InitiativesPage({ onDirty }: { onDirty: (value: boolean) => void }) {
  const [items, setItems] = useState<Initiative[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    void request<Initiative[]>(`/api/v1/catalogs/initiatives?${companyQuery()}`).then(setItems).catch(() => setError("Não foi possível consultar as iniciativas."));
  };
  useEffect(load, []);

  return (
    <article className="fluxo">
      <h1 id="page-title" tabIndex={-1}>Iniciativas</h1>
      <p className="pv-muted">A iniciativa é uma atividade da empresa. O nome da empresa não vira iniciativa sozinho. Inativar não apaga o que já foi atribuído.</p>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {items.length === 0 ? <p>Nenhuma iniciativa cadastrada. Crie a primeira para poder atribuir movimentos.</p> : (
        <ul>{items.map((item) => <li key={item.id}><strong>{item.name}</strong> · {item.code} · {item.active ? "Ativa" : "Inativa"}</li>)}</ul>
      )}
      <form className="form" onChange={() => onDirty(true)} onSubmit={(event) => {
        event.preventDefault();
        const pending = freezeWrite(`/api/v1/catalogs/initiatives?${companyQuery()}`, "POST", { code, name });
        void sendPending(pending).then(() => { setCode(""); setName(""); onDirty(false); load(); }).catch((caught: { message?: string }) => setError(caught.message || "Não foi possível cadastrar."));
      }}>
        <label>Código estável<input value={code} onChange={(event) => setCode(event.target.value)} required /></label>
        <label>Nome<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <button type="submit">Criar iniciativa</button>
      </form>
    </article>
  );
}

export function AllocationRulesPage({ onDirty }: { onDirty: (value: boolean) => void }) {
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [name, setName] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [shares, setShares] = useState<Share[]>([]);
  const [error, setError] = useState("");
  const [rules, setRules] = useState<{ id: string; name: string; versions: { versionNo: number; validFrom: string; shares?: { code: string; basisPoints: number }[] }[] }[]>([]);

  const load = () => {
    void request<Initiative[]>(`/api/v1/catalogs/initiatives?${companyQuery()}`).then(setInitiatives);
    void request<typeof rules>(`/api/v1/catalogs/allocation-rules?${companyQuery()}`).then(setRules).catch(() => setError("Não foi possível consultar as regras."));
  };
  useEffect(load, []);

  const points = shares.reduce((sum, share) => sum + share.basisPoints, 0);

  return (
    <article className="fluxo">
      <h1 id="page-title" tabIndex={-1}>Regras de rateio</h1>
      <p className="pv-muted">Uma regra completa soma 100%. Ela não recalcula decisões já gravadas. O resíduo não atribuído fica na classificação, não numa regra pela metade.</p>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {rules.length === 0 ? <p>Nenhuma regra ainda.</p> : rules.map((rule) => (
        <p key={rule.id}>
          <strong>{rule.name}</strong> · versão {rule.versions[0]?.versionNo} desde {rule.versions[0]?.validFrom}
          {(rule.versions[0]?.shares ?? []).length > 0 ? (
            <span> · {(rule.versions[0]?.shares ?? []).map((share) => `${share.code} ${(share.basisPoints / 100).toLocaleString("pt-BR")}%`).join(" e ")}</span>
          ) : null}
        </p>
      ))}
      <form className="form" onChange={() => onDirty(true)} onSubmit={(event) => {
        event.preventDefault();
        if (points !== 10000) {
          setError("A soma precisa ser 100%. Agora está em " + (points / 100).toLocaleString("pt-BR") + "%.");
          return;
        }
        const pending = freezeWrite(`/api/v1/catalogs/allocation-rules?${companyQuery()}`, "POST", { name, validFrom, shares });
        void sendPending(pending).then(() => { onDirty(false); load(); }).catch((caught: { message?: string }) => setError(caught.message || "Não foi possível gravar a regra."));
      }}>
        <label>Nome<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <label>Vigência a partir de<input type="date" value={validFrom} onChange={(event) => setValidFrom(event.target.value)} required /></label>
        {initiatives.map((item) => (
          <label key={item.id}>{item.name}
            <input inputMode="decimal" placeholder="Percentual, como 50" onChange={(event) => {
              const basisPoints = Math.round(Number(event.target.value.replace(",", ".")) * 100);
              setShares((current) => [...current.filter((share) => share.initiativeId !== item.id), { initiativeId: item.id, code: item.code, basisPoints }].filter((share) => share.basisPoints > 0));
            }} />
          </label>
        ))}
        <p>Soma atual: {(points / 100).toLocaleString("pt-BR")}%</p>
        <button type="submit">Criar regra</button>
      </form>
    </article>
  );
}
