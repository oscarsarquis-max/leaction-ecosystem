import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";
type Note = {
  id: string;
  topic_key: string;
  title: string;
  body: string;
  editorial_status: string;
  version: number;
};

export function GigioNotes() {
  const [items, setItems] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    adminRequest<{ items: Note[] }>("/api/v1/admin/gigio/notes")
      .then((payload) => setItems(payload.items))
      .catch((reason) => setError(reason instanceof AdminApiError ? reason.message : "Falha ao carregar."));
  }, []);

  async function save(note: Note) {
    setBusy(note.id);
    setError(null);
    try {
      const updated = await adminRequest<Note>(`/api/v1/admin/gigio/notes/${note.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: note.title,
          body: note.body,
          editorial_status: note.editorial_status,
        }),
      });
      setItems((current) => current.map((item) => (item.id === note.id ? updated : item)));
    } catch (reason) {
      setError(reason instanceof AdminApiError ? reason.message : "Não foi possível gravar.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="admin-page">
      <p className="admin-eyebrow">Gigio</p>
      <h1>Explicações aprovadas</h1>
      <p className="admin-lead">
        Rascunhos não entram na conversa. Não invente tempos de fermentação para preencher lacunas. As opções do
        Criador e os preços não mudam nesta tela. Referências de vinho, queijo e azeite ficam em{" "}
        <a href="/admin/produtos/gigio/harmonizacoes">Harmonizações</a>.
      </p>
      {error ? <p className="admin-error">{error}</p> : null}
      {items.map((note) => (
        <form
          key={note.id}
          className="admin-note-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save(note);
          }}
        >
          <p className="admin-muted">
            {note.topic_key} · versão {note.version}
          </p>
          <label>
            Título
            <input
              value={note.title}
              onChange={(event) =>
                setItems((current) =>
                  current.map((item) => (item.id === note.id ? { ...item, title: event.target.value } : item)),
                )
              }
            />
          </label>
          <label>
            Texto
            <textarea
              rows={5}
              value={note.body}
              onChange={(event) =>
                setItems((current) =>
                  current.map((item) => (item.id === note.id ? { ...item, body: event.target.value } : item)),
                )
              }
            />
          </label>
          <label>
            Estado
            <select
              value={note.editorial_status}
              onChange={(event) =>
                setItems((current) =>
                  current.map((item) =>
                    item.id === note.id ? { ...item, editorial_status: event.target.value } : item,
                  ),
                )
              }
            >
              <option value="draft">Rascunho</option>
              <option value="published">Publicada</option>
            </select>
          </label>
          <button type="submit" className="admin-primary" disabled={busy === note.id}>
            Salvar
          </button>
        </form>
      ))}
    </section>
  );
}
