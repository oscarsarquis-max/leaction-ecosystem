import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";
import type { AdminProductList } from "./productTypes";

export type ShowcaseProduct = {
  id: string;
  name: string;
  slug: string;
  editorial_status: string;
  is_available: boolean;
  thumbnail_url: string | null;
};

export type ShowcaseSlot = {
  position: number;
  product_id: string | null;
  product: ShowcaseProduct | null;
};

type ShowcaseResponse = {
  slots: ShowcaseSlot[];
};

const STATUS: Record<string, string> = {
  draft: "rascunho",
  published: "publicado",
  archived: "arquivado",
};

function errorMessage(error: unknown): string {
  if (error instanceof AdminApiError) {
    return error.message;
  }
  return "Não foi possível atualizar a vitrine.";
}

export function ShowcasePanel() {
  const [slots, setSlots] = useState<ShowcaseSlot[] | null>(null);
  const [candidates, setCandidates] = useState<AdminProductList["items"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [showcase, products] = await Promise.all([
        adminRequest<ShowcaseResponse>("/api/v1/admin/showcase"),
        adminRequest<AdminProductList>("/api/v1/admin/products?page=1&page_size=50"),
      ]);
      setSlots(showcase.slots);
      setCandidates(products.items.filter((item) => item.editorial_status !== "archived"));
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function assign(position: number, productId: string | null) {
    setBusy(`assign-${position}`);
    setError(null);
    try {
      const data = await adminRequest<ShowcaseResponse>(`/api/v1/admin/showcase/slots/${position}`, {
        method: "PUT",
        body: JSON.stringify({ product_id: productId }),
      });
      setSlots(data.slots);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  async function move(position: number, direction: "up" | "down") {
    setBusy(`move-${position}-${direction}`);
    setError(null);
    try {
      const data = await adminRequest<ShowcaseResponse>(
        `/api/v1/admin/showcase/slots/${position}/move`,
        {
          method: "POST",
          body: JSON.stringify({ direction }),
        },
      );
      setSlots(data.slots);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  const taken = new Set((slots ?? []).map((slot) => slot.product_id).filter(Boolean));

  return (
    <section className="admin-showcase" aria-labelledby="showcase-title">
      <h2 id="showcase-title">Vitrine (10 posições)</h2>
      <p className="admin-lead">
        A ordem da loja pública segue estas posições. Tirar um pão da vitrine não apaga o cadastro.
        O limite de dez é só da vitrine, não do catálogo nem da agenda.
      </p>
      {error ? <p className="admin-error">{error}</p> : null}
      {loading || !slots ? <p className="admin-muted">Carregando a vitrine…</p> : null}
      {slots ? (
        <ol className="admin-showcase-list">
          {slots.map((slot) => (
            <li key={slot.position} className="admin-showcase-slot">
              <span className="admin-showcase-index">Posição {slot.position}</span>
              <label>
                Produto
                <select
                  value={slot.product_id ?? ""}
                  disabled={busy !== null}
                  onChange={(event) => {
                    const value = event.target.value;
                    void assign(slot.position, value ? value : null);
                  }}
                >
                  <option value="">Escolher produto</option>
                  {slot.product && !candidates.some((item) => item.id === slot.product?.id) ? (
                    <option value={slot.product.id}>
                      {slot.product.name} ({STATUS[slot.product.editorial_status] ?? slot.product.editorial_status})
                    </option>
                  ) : null}
                  {candidates
                    .filter((item) => item.id === slot.product_id || !taken.has(item.id))
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                        {item.editorial_status === "published" ? "" : ` (${STATUS[item.editorial_status]})`}
                      </option>
                    ))}
                </select>
              </label>
              <div className="admin-showcase-actions">
                <button
                  type="button"
                  className="admin-secondary"
                  disabled={slot.position === 1 || busy !== null}
                  onClick={() => void move(slot.position, "up")}
                >
                  Subir
                </button>
                <button
                  type="button"
                  className="admin-secondary"
                  disabled={slot.position === 10 || busy !== null}
                  onClick={() => void move(slot.position, "down")}
                >
                  Descer
                </button>
                <button
                  type="button"
                  className="admin-text"
                  disabled={!slot.product_id || busy !== null}
                  onClick={() => void assign(slot.position, null)}
                >
                  Remover da vitrine
                </button>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
