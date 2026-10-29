import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";
type Pairing = {
  id: string;
  profile_key: string;
  category: string;
  scope: string;
  title: string;
  synthesis: string;
  editorial_note: string;
  source_url: string;
  source_title: string;
  source_author: string;
  source_date: string;
  consulted_at: string;
  source_kind: string;
  commercial_relation: string;
  evidence_type: string;
  retrieval_role: string;
  verification_status: string;
  support_locator: string;
  editorial_status: string;
  reviewed_by: string;
  reviewed_at: string;
  loja_choice: boolean;
  version: number;
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  reviewed: "Revisada",
  published: "Publicada",
  archived: "Arquivada",
};

export function PairingRefs() {
  const [items, setItems] = useState<Pairing[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    adminRequest<{ items: Pairing[] }>("/api/v1/admin/gigio/pairings")
      .then((payload) => setItems(payload.items))
      .catch((reason) => setError(reason instanceof AdminApiError ? reason.message : "Falha ao carregar."));
  }, []);

  async function save(item: Pairing) {
    setBusy(item.id);
    setError(null);
    try {
      const updated = await adminRequest<Pairing>(`/api/v1/admin/gigio/pairings/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: item.title,
          synthesis: item.synthesis,
          editorial_note: item.editorial_note,
          editorial_status: item.editorial_status,
          category: item.category,
          scope: item.scope,
          source_url: item.source_url,
          source_title: item.source_title,
          source_author: item.source_author,
          source_date: item.source_date,
          consulted_at: item.consulted_at,
          source_kind: item.source_kind,
          commercial_relation: item.commercial_relation,
          evidence_type: item.evidence_type,
          retrieval_role: item.retrieval_role,
          verification_status: item.verification_status,
          support_locator: item.support_locator,
          reviewed_by: item.reviewed_by,
          reviewed_at: item.reviewed_at,
          loja_choice: item.loja_choice,
        }),
      });
      setItems((current) => current.map((row) => (row.id === item.id ? updated : row)));
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível gravar.");
    } finally {
      setBusy(null);
    }
  }

  function patch(id: string, change: Partial<Pairing>) {
    setItems((current) => current.map((row) => (row.id === id ? { ...row, ...change } : row)));
  }

  return (
    <section className="admin-page">
      <p className="admin-eyebrow">Gigio</p>
      <h1>Referências de harmonização</h1>
      <p className="admin-lead">
        Precisão antes de volume. Só entra na conversa o que estiver publicado, com papel de harmonização e
        verificação confirmada. Fonte comercial é orientação de varejista; registro oficial não é
        harmonização; projeto de pesquisa não é resultado. O responsável não é preenchido automaticamente.
        «Escolha de A Loja» é decisão distinta da conferência da fonte.
      </p>
      {error ? <p className="admin-error">{error}</p> : null}
      {items.map((item) => (
        <form
          key={item.id}
          className="admin-note-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save(item);
          }}
        >
          <p className="admin-muted">
            {item.profile_key} · {item.category} · {item.scope} · {item.evidence_type} ·{" "}
            {item.retrieval_role} · {item.verification_status} · versão {item.version} ·{" "}
            {STATUS_LABEL[item.editorial_status] || item.editorial_status}
          </p>
          <label>
            Título
            <input value={item.title} onChange={(event) => patch(item.id, { title: event.target.value })} />
          </label>
          <label>
            Síntese (o que a fonte sustenta)
            <textarea
              rows={4}
              value={item.synthesis}
              onChange={(event) => patch(item.id, { synthesis: event.target.value })}
            />
          </label>
          <label>
            Nota editorial interna
            <textarea
              rows={2}
              value={item.editorial_note}
              onChange={(event) => patch(item.id, { editorial_note: event.target.value })}
            />
          </label>
          <p className="admin-muted">
            Fonte:{" "}
            <a href={item.source_url} target="_blank" rel="noopener noreferrer">
              {item.source_title || item.source_url}
            </a>
            {item.source_author ? ` · ${item.source_author}` : ""}
            {item.source_date ? ` · ${item.source_date}` : " · data não informada"}
            {` · consulta ${item.consulted_at}`}
            {` · ${item.source_kind}`}
          </p>
          {item.support_locator ? <p className="admin-muted">Suporte: {item.support_locator}</p> : null}
          <label>
            Estado
            <select
              value={item.editorial_status}
              onChange={(event) => patch(item.id, { editorial_status: event.target.value })}
            >
              <option value="draft">Rascunho</option>
              <option value="reviewed">Revisada</option>
              <option value="published">Publicada</option>
              <option value="archived">Arquivada</option>
            </select>
          </label>
          <label>
            Responsável pela revisão
            <input
              value={item.reviewed_by}
              onChange={(event) => patch(item.id, { reviewed_by: event.target.value })}
            />
          </label>
          <label>
            Data da revisão
            <input
              value={item.reviewed_at}
              onChange={(event) => patch(item.id, { reviewed_at: event.target.value })}
            />
          </label>
          <label className="admin-check">
            <input
              type="checkbox"
              checked={item.loja_choice}
              onChange={(event) => patch(item.id, { loja_choice: event.target.checked })}
            />
            Escolha de A Loja (só após publicação e revisão)
          </label>
          <button type="submit" className="admin-primary" disabled={busy === item.id}>
            Salvar
          </button>
        </form>
      ))}
    </section>
  );
}
